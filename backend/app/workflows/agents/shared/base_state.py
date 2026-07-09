"""Shared base state for every LangGraph agent."""

from typing import TypedDict, Optional


class BaseState(TypedDict, total=False):
    """Every agent state carries an optional error field so nodes can fail
    gracefully and downstream nodes can short-circuit."""

    error: Optional[str]
