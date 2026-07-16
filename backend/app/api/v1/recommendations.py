"""Recommendation (learning-roadmap) API.

Endpoints:
* ``POST /skills/{skill_id}/recommendations`` - build a week-by-week
  roadmap from the skill details already stored in ``user_skill_details``,
  store it, and return it. Only ``skill_id`` is required.
* ``GET  /employees/{employee_id}/recommendations`` - fetch all roadmaps for an employee.
  Optionally filter by skill_id via query param.
"""

from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Query

from app.schemas.recommendation import RoadmapPlan, RoadmapResponse
from app.services.recommendation import recommendation_service

router = APIRouter(tags=["Recommendations"])


def _to_roadmap_response(roadmap: dict) -> RoadmapResponse:
    """Maps a persisted ``roadmaps`` row into the API response schema."""
    return RoadmapResponse(
        roadmap_id=roadmap["roadmap_id"],
        user_id=roadmap["user_id"],
        skill_id=roadmap.get("skill_id"),
        target_role=roadmap.get("target_role"),
        status=roadmap["status"],
        plan=RoadmapPlan.model_validate(roadmap.get("plan") or {}),
        created_at=roadmap.get("created_at"),
    )


@router.post("/skills/{skill_id}/roadmap", response_model=RoadmapResponse)
async def create_recommendation(
    skill_id: UUID,
    available_weeks: Optional[int] = Query(
        default=None,
        ge=1,
        le=12,
        description=(
            "How many weeks the employee is available for. If provided, the "
            "roadmap is compressed to fit within this many weeks, prioritising "
            "the largest skill gaps. Defaults to up to 12 weeks."
        ),
    ),
) -> RoadmapResponse:
    """Generates and stores a week-by-week roadmap for a skill.

    Only ``skill_id`` is required. All inputs (current/target roles, existing
    skills and skill gaps) are read from ``user_skill_details``. Runs a vector
    search over the course catalogue, prompts Gemini to produce the plan, saves
    it, and returns the persisted roadmap.

    Pass ``available_weeks`` to cap the roadmap length for busy employees.
    """
    roadmap = await recommendation_service.generate(skill_id, available_weeks=available_weeks)
    return _to_roadmap_response(roadmap)


@router.get("/employees/{employee_id}/roadmaps", response_model=List[RoadmapResponse])
async def get_roadmaps_by_employee(
    employee_id: UUID,
    skill_id: Optional[UUID] = Query(
        default=None,
        description="Filter to the roadmap for this specific skill. If omitted, all roadmaps for the employee are returned.",
    ),
) -> List[RoadmapResponse]:
    """Fetches roadmaps for an employee, ordered by created_at desc.

    If ``skill_id`` is provided, returns only the most recent roadmap for that
    specific skill. Otherwise, returns all roadmaps for the employee.
    """
    roadmaps = await recommendation_service.get_roadmaps_by_user_id(employee_id, skill_id)
    return [_to_roadmap_response(r) for r in roadmaps]
