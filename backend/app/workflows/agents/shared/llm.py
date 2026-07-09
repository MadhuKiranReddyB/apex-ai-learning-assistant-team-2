"""Shared LangChain LLM clients.

At the moment only the Gemini generative model is required for the roadmap
agent. The Groq client is kept available (commented) for future multi-LLM flows
that need a fast/cheap drafting step.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import get_settings


def get_gemini_llm() -> ChatGoogleGenerativeAI:
    """Returns the Gemini generative model used by agents."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=get_settings().GEMINI_API_KEY,
        temperature=0.3,
    )


# from langchain_groq import ChatGroq
# def get_groq_llm() -> ChatGroq:
#     return ChatGroq(
#         model="llama-3.1-8b-instant",
#         api_key=get_settings().GROQ_API_KEY,
#         temperature=0.3,
#     )
