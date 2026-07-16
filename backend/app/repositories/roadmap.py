from uuid import UUID
from typing import List, Optional

from app.core.supabase_client import get_async_supabase
from app.core.exceptions import DatabaseException, ConnectionException

ROADMAP_TABLE = "roadmaps"


class RoadmapRepository:
    """Data access for the ``roadmaps`` table. Each row stores a full
    week-by-week learning plan as a JSONB ``plan`` document."""

    async def get_all_by_user_id(self, user_id: UUID) -> List[dict]:
        """Returns all roadmaps for a user, ordered by created_at desc."""
        sb = await get_async_supabase()
        try:
            result = await (
                sb.table(ROADMAP_TABLE)
                .select("*, user_skill_details(current_role)")
                .eq("user_id", str(user_id))
                .order("created_at", desc=True)
                .execute()
            )
        except Exception as exc:
            error_msg = str(exc).lower()
            if any(keyword in error_msg for keyword in ['connection', 'timeout', 'network', 'credential', 'auth']):
                raise ConnectionException(f"Failed to connect to database: {str(exc)}") from exc
            raise DatabaseException(f"Failed to fetch roadmaps for user {user_id}: {str(exc)}") from exc
        return result.data or []

    async def get_latest_by_user_id(self, user_id: UUID) -> Optional[dict]:
        """Returns the most recently created roadmap for a user, or ``None``."""
        sb = await get_async_supabase()
        try:
            result = await (
                sb.table(ROADMAP_TABLE)
                .select("*, user_skill_details(current_role)")
                .eq("user_id", str(user_id))
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            error_msg = str(exc).lower()
            if any(keyword in error_msg for keyword in ['connection', 'timeout', 'network', 'credential', 'auth']):
                raise ConnectionException(f"Failed to connect to database: {str(exc)}") from exc
            raise DatabaseException(f"Failed to fetch roadmap for user {user_id}: {str(exc)}") from exc
        data = result.data
        return data[0] if data else None

    async def get_by_user_id_and_skill_id(
        self, user_id: UUID, skill_id: UUID
    ) -> Optional[dict]:
        """Returns the most recent roadmap for a user and skill, or ``None``."""
        sb = await get_async_supabase()
        try:
            result = await (
                sb.table(ROADMAP_TABLE)
                .select("*, user_skill_details(current_role)")
                .eq("user_id", str(user_id))
                .eq("skill_id", str(skill_id))
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            error_msg = str(exc).lower()
            if any(keyword in error_msg for keyword in ['connection', 'timeout', 'network', 'credential', 'auth']):
                raise ConnectionException(f"Failed to connect to database: {str(exc)}") from exc
            raise DatabaseException(
                f"Failed to fetch roadmap for user {user_id} and skill {skill_id}: {str(exc)}"
            ) from exc
        data = result.data
        return data[0] if data else None

    async def create(self, data: dict) -> dict:
        """Inserts a new roadmap row and returns the persisted record with joined user_skill_details."""
        sb = await get_async_supabase()
        try:
            result = await sb.table(ROADMAP_TABLE).insert(data).select("*, user_skill_details(current_role)").execute()
        except Exception as exc:
            error_msg = str(exc).lower()
            if any(keyword in error_msg for keyword in ['connection', 'timeout', 'network', 'credential', 'auth']):
                raise ConnectionException(f"Failed to connect to database: {str(exc)}") from exc
            raise DatabaseException(f"Failed to create roadmap: {str(exc)}") from exc
        return result.data[0]
