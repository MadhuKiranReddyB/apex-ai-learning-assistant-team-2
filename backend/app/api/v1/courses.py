from fastapi import APIRouter
from app.schemas.course import CourseResponse, CourseBulkResponse, CourseBulkCreate
from app.services.course import course_service

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.post("", response_model=CourseBulkResponse)
async def create_courses(payload: CourseBulkCreate):
    """
    TODO : get the details from the udemy , as of now we are inserting test data 
    Seed one or many courses into the vector database. Pass an array in `courses`:
    Each course is embedded with Gemini before insertion so it can be matched via
    vector similarity search during roadmap generation."""
    courses = await course_service.create_courses_bulk(payload)
    return CourseBulkResponse(
        created_count=len(courses),
        courses=[CourseResponse.model_validate(c) for c in courses],
    )
