"""LangGraph nodes for the roadmap agent.

Flow: retrieve_courses → generate_plan → enrich_plan
- retrieve_courses: embeds skill gaps and runs vector search.
- generate_plan: calls Gemini with the candidate catalogue and returns a
  structured JSON plan (course_ids only).
- enrich_plan: maps course_ids back to the full course rows and builds the final
  plan dict that matches the API ``RoadmapPlan`` schema.
"""

from typing import List
from uuid import UUID

from langchain_core.messages import SystemMessage, HumanMessage

from app.core.config import get_settings
from app.core.exceptions import ConfigurationException, LLMException
from app.core import gemini_client
from app.core.logging import get_logger
from app.repositories.course import CourseRepository
from app.workflows.agents.roadmap.state import RoadmapState
from app.workflows.agents.roadmap.schema import RoadmapPlanSchema
from app.workflows.agents.roadmap.prompts import (
    ROADMAP_SYSTEM_PROMPT,
    ROADMAP_USER_PROMPT_TEMPLATE,
    CANDIDATE_COURSE_FORMAT,
)
from app.workflows.agents.shared.llm import get_gemini_llm

logger = get_logger(__name__)

CANDIDATE_COURSE_LIMIT = 10
MAX_WEEKS = 12


def _format_skill_gaps(skill_gaps: List[dict]) -> str:
    return "\n".join(
        f"- {gap.get('skill', 'Unknown')} (target level {gap.get('required_level', 0)})"
        for gap in skill_gaps
    )


def _rank_skill_gaps(skill_gaps: List[dict], skills: dict) -> List[dict]:
    """Orders skill gaps by biggest gap first (required_level - current level).

    When the roadmap is compressed into fewer weeks, listing the most important
    gaps first lets the LLM prioritise them and omit the least important skills
    instead of overloading each week.
    """
    def _gap_size(gap: dict) -> int:
        required = gap.get("required_level") or 0
        current = skills.get(gap.get("skill")) or 0
        return int(required) - int(current)

    return sorted(skill_gaps, key=_gap_size, reverse=True)


def _format_skills(skills: dict) -> str:
    if not skills:
        return "No skill data provided"
    return "\n".join(f"- {skill}: {level}/10" for skill, level in skills.items())


def _format_courses(courses: List[dict]) -> str:
    if not courses:
        return "No courses available"
    blocks = []
    for c in courses:
        blocks.append(
            CANDIDATE_COURSE_FORMAT.format(
                course_id=c.get("course_id", ""),
                course_name=c.get("course_name", "Unknown"),
                provider=c.get("provider") or "unspecified",
                difficulty_level=c.get("difficulty_level") or "unspecified",
                duration_hours=c.get("duration_hours") or "unspecified",
                skills_taught=", ".join(c.get("skills_taught") or []),
                description=(c.get("description") or "")[:200],
            )
        )
    return "\n\n".join(blocks)


async def node_retrieve_courses(state: RoadmapState) -> dict:
    """Embeds skill gaps and retrieves the most relevant courses via vector search."""
    if state.get("error"):
        return {"error": state["error"]}

    skill_gaps = state.get("skill_gaps", [])
    if not skill_gaps:
        logger.warning("No skill gaps provided for retrieval")
        return {"candidate_courses": []}

    if not get_settings().GEMINI_API_KEY:
        raise ConfigurationException("GEMINI_API_KEY is not configured. Roadmap generation requires embeddings.")

    gap_text = "Skills to learn: " + ", ".join(
        f"{gap.get('skill')} (target level {gap.get('required_level')})"
        for gap in skill_gaps
    )

    try:
        query_embedding = await gemini_client.embed_text(gap_text, task_type="retrieval_query")
    except Exception as exc:
        logger.error("Failed to generate embedding for skill gaps", exc_info=exc)
        raise LLMException(
            "Failed to generate embedding for skill gaps. Check GEMINI_API_KEY and network connectivity."
        ) from exc

    course_repo = CourseRepository()
    courses = await course_repo.list_by_embedding(query_embedding, limit=CANDIDATE_COURSE_LIMIT)
    if not courses:
        logger.warning("No courses found via vector search", gap_text=gap_text)
    return {"candidate_courses": courses}


async def node_generate_plan(state: RoadmapState) -> dict:
    """Calls Gemini to produce a structured plan referencing course IDs."""
    if state.get("error"):
        return {"error": state["error"]}

    candidate_courses = state.get("candidate_courses", [])
    if not candidate_courses:
        return {
            "error": "No candidate courses found for the provided skill gaps. Seed the courses table first."
        }

    llm = get_gemini_llm()
    structured_llm = llm.with_structured_output(RoadmapPlanSchema)

    skills = state.get("skills") or {}
    ranked_gaps = _rank_skill_gaps(state.get("skill_gaps", []), skills)

    available_weeks = state.get("available_weeks")
    max_weeks = MAX_WEEKS if not available_weeks else max(1, min(int(available_weeks), MAX_WEEKS))

    user_prompt = ROADMAP_USER_PROMPT_TEMPLATE.format(
        current_role=state.get("current_role") or "Unknown",
        target_role=state.get("target_role") or "Unknown",
        skills_text=_format_skills(skills),
        skill_gaps_text=_format_skill_gaps(ranked_gaps),
        courses_text=_format_courses(candidate_courses),
        max_weeks=max_weeks,
    )

    try:
        response = await structured_llm.ainvoke([
            SystemMessage(content=ROADMAP_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ])
        plan = response.model_dump(mode="json")
    except Exception as exc:
        logger.error("Failed to generate roadmap plan", exc_info=exc)
        return {"error": f"Failed to generate the roadmap plan: {exc}"}

    return {"llm_plan": plan}


async def node_enrich_plan(state: RoadmapState) -> dict:
    """Maps the LLM's course_ids back to full course objects and builds the final
    plan dict matching the API ``RoadmapPlan`` schema."""
    if state.get("error"):
        return {"error": state["error"]}

    llm_plan = state.get("llm_plan")
    if not llm_plan:
        return {"error": "No plan was generated by the LLM."}

    candidate_courses = state.get("candidate_courses", [])
    course_lookup = {str(c.get("course_id")): c for c in candidate_courses}

    enriched_weeks = []
    for week in llm_plan.get("weeks", []):
        enriched_courses = []
        for course_id in week.get("course_ids", []):
            source = course_lookup.get(course_id)
            if not source:
                logger.warning("Course referenced by LLM not found in candidates", course_id=course_id)
                continue
            enriched_courses.append(
                {
                    "course_id": source.get("course_id"),
                    "course_name": source.get("course_name"),
                    "provider": source.get("provider"),
                    "url": source.get("url"),
                }
            )
        enriched_weeks.append(
            {
                "week": week.get("week_number"),
                "focus": week.get("focus"),
                "skills": week.get("skills_covered", []),
                "activities": week.get("activities", []),
                "courses": enriched_courses,
            }
        )

    final_plan = {
        "summary": llm_plan.get("summary", ""),
        "total_weeks": llm_plan.get("total_weeks", len(enriched_weeks)),
        "weeks": enriched_weeks,
    }

    return {"final_plan": final_plan}


async def node_validate_plan(state: RoadmapState) -> dict:
    """Validation node — cleans the final plan before it is stored.

    - Removes duplicate courses that appear in more than one week (keeps the
      first occurrence, so a course is scheduled only once).
    - Drops any week left with no courses AND no activities.
    - Renumbers the remaining weeks sequentially and fixes ``total_weeks``.
    """
    if state.get("error"):
        return {"error": state["error"]}

    final_plan = state.get("final_plan")
    if not final_plan:
        return {"error": "No final plan to validate."}

    seen_course_ids = set()
    cleaned_weeks = []
    for week in final_plan.get("weeks", []):
        unique_courses = []
        for course in week.get("courses", []):
            course_id = str(course.get("course_id"))
            if course_id in seen_course_ids:
                continue  # already scheduled in an earlier week → skip duplicate
            seen_course_ids.add(course_id)
            unique_courses.append(course)

        # keep the week only if it still has something to do
        if not unique_courses and not week.get("activities"):
            continue

        week["courses"] = unique_courses
        cleaned_weeks.append(week)

    # renumber weeks 1..N after any removals
    for index, week in enumerate(cleaned_weeks, start=1):
        week["week"] = index

    final_plan["weeks"] = cleaned_weeks
    final_plan["total_weeks"] = len(cleaned_weeks)

    logger.info(
        "Validated roadmap plan",
        weeks=len(cleaned_weeks),
        unique_courses=len(seen_course_ids),
    )
    return {"final_plan": final_plan}
