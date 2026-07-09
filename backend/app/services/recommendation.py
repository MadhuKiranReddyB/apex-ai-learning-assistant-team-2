"""Business logic for the learning-recommendation flow.

The heavy lifting is now performed by the LangGraph roadmap workflow (see
``app/workflows/agents/roadmap``). This service is a thin orchestration layer:

1. Reads the skill analysis from ``user_skill_details`` using ``skill_id``.
2. Resolves and executes the roadmap workflow via the registry.
3. Stores the workflow's ``final_plan`` as a JSONB document in ``roadmaps``.
4. Returns the persisted record.

No skill-analysis JSON is required in the request body: every input the
workflow needs is already stored in the database and is looked up by ``skill_id``.
"""

import uuid
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.supabase_client import get_async_supabase
from app.core.exceptions import (
    ConfigurationException,
    RoadmapNotFoundException,
    DatabaseException,
    WorkflowInputException,
)
from app.core.logging import get_logger
from app.repositories.roadmap import RoadmapRepository
from app.workflows.registry import workflow_registry
from app.workflows.loader import ROADMAP_WORKFLOW_ID

logger = get_logger(__name__)


class RecommendationService:
    """Generates, saves and fetches employee learning roadmaps."""

    async def _get_skill_details(self, skill_id: UUID) -> dict:
        """Fetches the full ``user_skill_details`` row for ``skill_id``."""
        sb = await get_async_supabase()
        try:
            result = await (
                sb.table("user_skill_details")
                .select("*")
                .eq("skill_id", str(skill_id))
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise DatabaseException(
                f"Failed to fetch skill details for skill {skill_id}: {str(exc)}"
            ) from exc
        if not result.data:
            raise RoadmapNotFoundException(f"No skill details found for skill {skill_id}")
        return result.data[0]

    @staticmethod
    def _extract_skills(skills_assessment: Optional[Any]) -> Dict[str, int]:
        """Normalises ``skills_assessment`` JSONB into a ``{skill: level}`` map.

        Accepts:
        * a plain object ``{"skill": level}``,
        * an object wrapping such a map under ``skills``,
        * an array of objects ``[{"skill": "...", "level": n}]``.
        """
        if skills_assessment is None:
            return {}
        data = skills_assessment
        if isinstance(data, dict) and "skills" in data and isinstance(data["skills"], dict):
            data = data["skills"]
        if isinstance(data, dict):
            skills: Dict[str, int] = {}
            for k, v in data.items():
                if isinstance(v, bool):
                    continue
                if isinstance(v, (int, float)):
                    skills[str(k)] = int(v)
                elif isinstance(v, str):
                    try:
                        skills[str(k)] = int(float(v))
                    except ValueError:
                        pass
            return skills
        if isinstance(data, list):
            list_skills: Dict[str, int] = {}
            for item in data:
                if not isinstance(item, dict):
                    continue
                skill = item.get("skill") or item.get("name")
                level = item.get("level") or item.get("proficiency")
                if skill and isinstance(level, (int, float)):
                    list_skills[str(skill)] = int(level)
            return list_skills
        return {}

    @staticmethod
    def _extract_skill_gaps(skills_gap_analysis: Optional[Any]) -> List[dict]:
        """Normalises ``skills_gap_analysis`` JSONB into a list of gaps.

        Accepts either a plain array ``[{skill, required_level}]`` or an object
        wrapping such an array (e.g. ``{"gaps": [...]}``).
        """
        if skills_gap_analysis is None:
            return []
        gaps: List[dict] = []
        data = skills_gap_analysis
        if isinstance(data, dict):
            if all(isinstance(v, (int, float)) for v in data.values()):
                # shape: {"skill": required_level}
                return [
                    {"skill": str(k), "required_level": int(v)}
                    for k, v in data.items()
                ]
            for candidate_key in ("gaps", "skillGaps", "skill_gaps"):
                if candidate_key in data and isinstance(data[candidate_key], list):
                    data = data[candidate_key]
                    break
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                skill = item.get("skill") or item.get("name")
                level = (
                    item.get("required_level")
                    or item.get("requiredLevel")
                    or item.get("level")
                    or item.get("target_level")
                )
                if skill and isinstance(level, (int, float)):
                    gaps.append({"skill": str(skill), "required_level": int(level)})
        return gaps

    async def generate(self, skill_id: UUID) -> dict:
        """Generates a week-by-week roadmap for a skill, stores it,
        and returns the persisted record.

        All inputs (user_id, current/target roles, skills and skill gaps) are
        read from ``user_skill_details`` using the provided ``skill_id``.
        """
        skill_details = await self._get_skill_details(skill_id)
        user_id = UUID(skill_details["user_id"])
        current_role = skill_details.get("current_role")
        target_role = skill_details.get("targeted_role")
        skills = self._extract_skills(skill_details.get("skills_assessment"))
        skill_gaps = self._extract_skill_gaps(skill_details.get("skills_gap_analysis"))

        if not skill_gaps:
            raise RoadmapNotFoundException(
                f"No skill gaps found for skill {skill_id}; cannot build a roadmap."
            )

        workflow = workflow_registry.get(ROADMAP_WORKFLOW_ID)
        if not workflow:
            raise ConfigurationException("Roadmap workflow is not registered.")

        workflow_input = {
            "employee_id": str(user_id),
            "current_role": current_role,
            "target_role": target_role,
            "skills": skills,
            "skill_gaps": skill_gaps,
        }

        try:
            result = await workflow.run(workflow_input)
        except RuntimeError as exc:
            raise WorkflowInputException(str(exc)) from exc
        final_plan = result["final_plan"]

        roadmap_repo = RoadmapRepository()
        roadmap = await roadmap_repo.create(
            {
                "roadmap_id": str(uuid.uuid4()),
                "user_id": str(user_id),
                "skill_id": str(skill_id),
                "target_role": target_role,
                "status": "active",
                "plan": final_plan,
            }
        )
        logger.info(
            "Roadmap generated and saved",
            user_id=str(user_id),
            skill_id=str(skill_id),
            roadmap_id=roadmap["roadmap_id"],
            total_weeks=final_plan.get("total_weeks"),
        )
        return roadmap

    async def get_roadmaps_by_user_id(
        self, user_id: UUID, skill_id: Optional[UUID] = None
    ) -> List[dict]:
        """Fetches roadmaps for a user, ordered by created_at desc.

        If ``skill_id`` is provided, returns only the most recent roadmap for that
        specific skill. Otherwise, returns all roadmaps for the user.
        """
        roadmap_repo = RoadmapRepository()
        if skill_id is not None:
            roadmap = await roadmap_repo.get_by_user_id_and_skill_id(user_id, skill_id)
            if not roadmap:
                raise RoadmapNotFoundException(f"No roadmap found for user {user_id} and skill {skill_id}")
            return [roadmap]
        else:
            roadmaps = await roadmap_repo.get_all_by_user_id(user_id)
            if not roadmaps:
                raise RoadmapNotFoundException(str(user_id))
            return roadmaps


recommendation_service = RecommendationService()
