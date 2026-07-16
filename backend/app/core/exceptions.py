from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from app.core.logging import get_logger

logger = get_logger(__name__)


class AppException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class DatabaseException(AppException):
    def __init__(self, detail: str = "A database error occurred"):
        super().__init__(status_code=500, detail=detail)


class ConnectionException(AppException):
    def __init__(self, detail: str = "A connection error occurred"):
        super().__init__(status_code=503, detail=detail)


class RoadmapNotFoundException(AppException):
    def __init__(self, employee_id: str):
        super().__init__(
            status_code=404,
            detail=f"Active roadmap for employee '{employee_id}' not found",
        )


class CourseNotFoundException(AppException):
    def __init__(self, course_id: str):
        super().__init__(
            status_code=404,
            detail=f"Course '{course_id}' not found",
        )


class ConfigurationException(AppException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=500,
            detail=f"Configuration error: {detail}",
        )


class LLMException(AppException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=500,
            detail=f"LLM/embedding error: {detail}",
        )


class WorkflowInputException(AppException):
    def __init__(self, detail: str):
        super().__init__(status_code=422, detail=detail)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(
            "Unhandled exception",
            method=request.method,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
