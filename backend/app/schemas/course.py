from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class CourseCreate(BaseModel):
    course_name: str
    provider: Optional[str] = None
    external_course_id: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    difficulty_level: Optional[str] = None
    duration_hours: Optional[float] = None
    url: Optional[str] = None
    prerequisites: List[str] = []
    skills_taught: List[str] = []
    rating: Optional[float] = None
    enrollment_count: int = 0


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    course_id: UUID
    course_name: str
    provider: Optional[str]
    external_course_id: Optional[str]
    description: Optional[str]
    category: Optional[str]
    difficulty_level: Optional[str]
    duration_hours: Optional[Decimal]
    url: Optional[str]
    prerequisites: List[str]
    skills_taught: List[str]
    rating: Optional[Decimal]
    enrollment_count: int


class CourseBulkResponse(BaseModel):
    """Response body returned after creating courses in bulk via
    ``POST /api/v1/courses``. Includes the persisted courses and a count."""

    created_count: int
    courses: List[CourseResponse]


class CourseBulkCreate(BaseModel):
    courses: List[CourseCreate]
