"""Pydantic schemas used as the *structured output* of the LLM nodes in the
roadmap workflow.

These schemas are intentionally simpler than the API's ``RoadmapPlan`` schema:
- Course references are just UUID strings (``course_ids``), not full objects.
- The final enrichment node maps those IDs back to the real course rows selected
  via vector search and builds the full API response.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class RoadmapWeekSchema(BaseModel):
    """A single week of the learning plan, as returned by the LLM."""

    week_number: int = Field(..., ge=1)
    focus: str
    skills_covered: List[str] = Field(default_factory=list)
    course_ids: List[str] = Field(default_factory=list)
    activities: List[str] = Field(default_factory=list)


class RoadmapPlanSchema(BaseModel):
    """Structured output schema for the LLM-generated roadmap."""

    summary: str = Field(..., description="High-level summary of the learning plan")
    total_weeks: int = Field(..., ge=1, le=26)
    weeks: List[RoadmapWeekSchema]
