from typing import List

from app.core.supabase_client import get_async_supabase
from app.core.exceptions import DatabaseException

TABLE = "courses"


class CourseRepository:
    async def list_by_embedding(self, embedding: List[float], limit: int = 10) -> List[dict]:
        """Vector similarity search via the `match_courses` Postgres function
        (see app/db/schema.sql) — finds courses whose embedding is closest to
        the given query embedding using cosine distance (pgvector)."""
        sb = await get_async_supabase()
        try:
            result = await sb.rpc(
                "match_courses",
                {"query_embedding": embedding, "match_count": limit},
            ).execute()
        except Exception as exc:
            raise DatabaseException() from exc
        return result.data or []

    async def create_many(self, rows: List[dict]) -> List[dict]:
        sb = await get_async_supabase()
        try:
            result = await sb.table(TABLE).insert(rows).execute()
        except Exception as exc:
            raise DatabaseException() from exc
        return result.data or []
