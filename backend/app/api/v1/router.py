from fastapi import APIRouter
from app.api.v1.courses import router as courses_router
from app.api.v1.recommendations import router as recommendations_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(courses_router)
api_router.include_router(recommendations_router)
