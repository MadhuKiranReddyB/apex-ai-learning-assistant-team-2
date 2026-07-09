from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.logging import setup_logging, get_logger
from app.core.exceptions import register_exception_handlers
from app.core.config import settings
from app.core.supabase_client import get_async_supabase
from app.workflows.loader import register_workflows

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    # Initialise the async Supabase client early so the first request has no cold-start.
    await get_async_supabase()
    # Register all LangGraph workflows before the first request can use them.
    register_workflows()
    logger.info("Application ready")
    yield
    logger.info("Shutting down...")


app = FastAPI(title="Learning Recommendation Engine", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
