"""Async Gemini *embedding* client wrapper.

Generative text/JSON is now handled by LangChain (``app/workflows/agents/shared/llm.py``);
this module only exposes the embedding helper used for the vector DB. It is
intentionally thin so it can be swapped for a different provider without touching
business logic.
"""

from functools import lru_cache

from google import genai
from google.genai import types

from app.core.config import get_settings

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768   # truncated via output_dimensionality, matches schema.sql `vector(768)`

_TASK_TYPE_MAP = {
    "retrieval_document": "RETRIEVAL_DOCUMENT",
    "retrieval_query": "RETRIEVAL_QUERY",
}


@lru_cache
def _get_client() -> genai.Client:
    settings = get_settings()
    return genai.Client(api_key=settings.GEMINI_API_KEY)


async def embed_text(text: str, task_type: str = "retrieval_document") -> list[float]:
    """Embeds `text` into a 768-dim vector using Gemini.
    task_type: "retrieval_document" for courses being indexed,
               "retrieval_query" for the skill-gap search text."""
    client = _get_client()
    result = await client.aio.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type=_TASK_TYPE_MAP.get(task_type, "RETRIEVAL_DOCUMENT"),
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    return result.embeddings[0].values
