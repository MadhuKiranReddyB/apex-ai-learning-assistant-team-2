import asyncio
from functools import lru_cache

from supabase import acreate_client, create_client, AsyncClient, Client

from app.core.config import get_settings


# ── Sync client (startup / scripts only) ──────────────────────────────────────

@lru_cache
def get_supabase() -> Client:
    """Sync service-role client — bypasses RLS. Used only outside the request loop."""
    s = get_settings()
    return create_client(s.SUPABASE_URL, s.SUPABASE_SERVICE_ROLE_KEY)


# ── Async client (all API request handlers) ───────────────────────────────────

_async_service: AsyncClient | None = None
_service_lock = asyncio.Lock()


async def get_async_supabase() -> AsyncClient:
    """Async service-role client — bypasses RLS. Used for all DB operations."""
    global _async_service
    if _async_service is None:
        async with _service_lock:
            if _async_service is None:
                s = get_settings()
                _async_service = await acreate_client(s.SUPABASE_URL, s.SUPABASE_SERVICE_ROLE_KEY)
    return _async_service
