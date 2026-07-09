"""Roadmap generation workflow.

Implements a LangGraph StateGraph that turns a skill-gap analysis into a stored,
week-by-week learning roadmap. The graph has three nodes executed in sequence:

Step 1 - ``retrieve_courses``
    Takes the employee's ``skill_gaps`` and converts them into a query string.
    Calls the Gemini embedding model (``gemini-embedding-001``) to create a
    768-dimension vector for that query. Runs a pgvector similarity search via
    the Supabase ``match_courses`` RPC and stores the top matching courses in
    ``state["candidate_courses"]``.

Step 2 - ``generate_plan``
    Reads the retrieved candidate catalogue from the state. Builds a prompt
    that includes the employee's current role, target role, existing skills,
    skill gaps, and the available courses. Calls the Gemini generative model
    (``gemini-2.5-flash``) through LangChain with structured output to produce a
    week-by-week plan. The plan references courses only by their ``course_id``
    strings and is stored in ``state["llm_plan"]``.

Step 3 - ``enrich_plan``
    Takes the LLM plan and maps each referenced ``course_id`` back to the full
    course row found in Step 1. Discards any invented course IDs. Builds the
    final ``state["final_plan"]`` dict that matches the API ``RoadmapPlan`` schema,
    with full course objects including ``course_id``, ``course_name``,
    ``provider`` and ``url``.

The final ``final_plan`` dict is returned to the caller (the recommendation
service) which stores it as JSONB in the ``roadmaps`` table.
"""

from uuid import UUID

from langgraph.graph import StateGraph, END

from app.workflows.base_workflow import BaseWorkflow
from app.workflows.agents.roadmap.state import RoadmapState
from app.workflows.agents.roadmap.nodes import (
    node_retrieve_courses,
    node_generate_plan,
    node_enrich_plan,
    node_validate_plan,
)
from app.core.exceptions import WorkflowInputException
from app.core.logging import get_logger

logger = get_logger(__name__)

NODE_RETRIEVE = "retrieve_courses"
NODE_GENERATE = "generate_plan"
NODE_ENRICH = "enrich_plan"
NODE_VALIDATE = "validate_plan"


class RoadmapWorkflow(BaseWorkflow):
    name = "roadmap"
    description = "Generates a week-by-week learning roadmap for a role transition"

    def __init__(self, workflow_id: str = "roadmap"):
        self.id = workflow_id
        self._graph = self._build_graph()

    def validate_input(self, input_data: dict) -> None:
        """Ensures the required fields are present and non-empty."""
        employee_id = input_data.get("employee_id")
        if not employee_id:
            raise WorkflowInputException("'employee_id' is required.")
        try:
            UUID(str(employee_id))
        except Exception as exc:
            raise WorkflowInputException(f"'employee_id' must be a valid UUID: {exc}") from exc

        if not input_data.get("skill_gaps"):
            raise WorkflowInputException("'skill_gaps' must be a non-empty list.")

    def _build_graph(self):
        graph = StateGraph(RoadmapState)
        graph.add_node(NODE_RETRIEVE, node_retrieve_courses)
        graph.add_node(NODE_GENERATE, node_generate_plan)
        graph.add_node(NODE_ENRICH, node_enrich_plan)
        graph.add_node(NODE_VALIDATE, node_validate_plan)
        graph.set_entry_point(NODE_RETRIEVE)
        graph.add_edge(NODE_RETRIEVE, NODE_GENERATE)
        graph.add_edge(NODE_GENERATE, NODE_ENRICH)
        graph.add_edge(NODE_ENRICH, NODE_VALIDATE)
        graph.add_edge(NODE_VALIDATE, END)
        return graph.compile()

    async def run(self, input_data: dict) -> dict:
        """Runs the roadmap graph and returns ``final_plan`` or raises on error."""
        self.validate_input(input_data)

        initial_state: RoadmapState = {
            "employee_id": input_data["employee_id"],
            "current_role": input_data.get("current_role"),
            "target_role": input_data.get("target_role"),
            "skills": input_data.get("skills") or {},
            "skill_gaps": input_data.get("skill_gaps", []),
            "candidate_courses": [],
            "llm_plan": None,
            "final_plan": None,
            "error": None,
        }

        result = await self._graph.ainvoke(initial_state)

        if result.get("error"):
            raise RuntimeError(result["error"])

        final_plan = result.get("final_plan")
        if not final_plan:
            raise RuntimeError("Workflow completed but no final plan was produced.")

        return {"final_plan": final_plan}
