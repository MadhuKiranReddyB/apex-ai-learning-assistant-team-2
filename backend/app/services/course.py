import asyncio
import uuid

from app.repositories.course import CourseRepository
from app.schemas.course import CourseBulkCreate
from app.core.logging import get_logger
from app.core.config import get_settings
from app.core import gemini_client
from app.core.exceptions import ConfigurationException, LLMException

logger = get_logger(__name__)


def _embedding_text(data: dict) -> str:
    """Builds the text that gets embedded for vector search, from the fields
    most relevant to matching a course against a user's skill gaps."""
    parts = [
        data.get("course_name") or "",
        data.get("description") or "",
        "Category: " + (data.get("category") or ""),
        "Skills taught: " + ", ".join(data.get("skills_taught") or []),
    ]
    return ". ".join(p for p in parts if p)


class CourseService:
    async def create_courses_bulk(self, payload: CourseBulkCreate) -> list[dict]:
        repo = CourseRepository()
        rows = [p.model_dump() for p in payload.courses]
        for row in rows:
            row["course_id"] = str(uuid.uuid4())

        if not get_settings().GEMINI_API_KEY:
            raise ConfigurationException("GEMINI_API_KEY is not configured. Course creation requires LLM embeddings.")

        async def _embed(row: dict):
            try:
                row["embedding"] = await gemini_client.embed_text(
                    _embedding_text(row), task_type="retrieval_document"
                )
            except Exception as exc:
                logger.error("Failed to generate embedding for course", course_name=row["course_name"], exc_info=exc)
                raise LLMException(f"Failed to generate embedding for course '{row['course_name']}'. Check GEMINI_API_KEY and network connectivity.") from exc

        await asyncio.gather(*(_embed(row) for row in rows))

        courses = await repo.create_many(rows)
        logger.info("Bulk courses created", count=len(courses))
        return courses


course_service = CourseService()
