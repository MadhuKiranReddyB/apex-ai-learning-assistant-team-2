"""TypedDict state for the roadmap-generation LangGraph agent.
"""

from typing import TypedDict, Optional, List, Dict
from uuid import UUID

from app.workflows.agents.shared.base_state import BaseState


class RoadmapState(TypedDict, total=False):
    """State carried through the roadmap graph nodes.

    Fields:
        * employee_id: target employee UUID (required input).
        * current_role: employee's current role.
        * target_role: desired role.
        * skills: existing skill -> level map.
        * skill_gaps: list of {skill, required_level} dicts.
        * available_weeks: optional cap on the roadmap length (weeks the
          employee is available for). Defaults to the workflow maximum.
        * candidate_courses: courses retrieved by vector search.
        * llm_plan: structured output from the LLM before enrichment.
        * final_plan: dict ready to be stored in ``roadmaps.plan`` JSONB.
        * error: optional error message from a failed node.
    """

    employee_id: UUID
    current_role: Optional[str]
    target_role: Optional[str]
    skills: Dict[str, int]
    skill_gaps: List[dict]
    available_weeks: Optional[int]
    candidate_courses: List[dict]
    llm_plan: Optional[dict]
    final_plan: Optional[dict]
    error: Optional[str]
