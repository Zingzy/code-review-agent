"""
Application Exceptions and Handlers

Custom exceptions and FastAPI exception handlers for the Code Reviewer Agent.
"""

from datetime import datetime

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError


class CodeReviewerException(Exception):
    """Base exception for all application-specific errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN_ERROR",
        details: dict = None,
        status_code: int = 500,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code


class TaskNotFoundException(CodeReviewerException):
    """Raised when a requested task is not found."""

    def __init__(self, task_id: str, details: dict = None):
        super().__init__(
            message=f"Task '{task_id}' not found",
            error_code="TASK_NOT_FOUND",
            details=details,
            status_code=404,
        )


class TaskNotCompletedException(CodeReviewerException):
    """Raised when trying to get results from an incomplete task."""

    def __init__(self, task_id: str, current_status: str, details: dict = None):
        super().__init__(
            message=f"Task '{task_id}' is not completed (status: {current_status})",
            error_code="TASK_NOT_COMPLETED",
            details=details,
            status_code=409,
        )


class InvalidRepositoryException(CodeReviewerException):
    """Raised when repository URL or access is invalid."""

    def __init__(self, repo_url: str, reason: str = None, details: dict = None):
        message = f"Invalid repository: {repo_url}"
        if reason:
            message += f" - {reason}"
        super().__init__(
            message=message,
            error_code="INVALID_REPOSITORY",
            details=details,
            status_code=400,
        )


class GitHubAPIException(CodeReviewerException):
    """Raised when GitHub API requests fail."""

    def __init__(
        self,
        message: str,
        status_code: int = None,
        rate_limit_exceeded: bool = False,
        details: dict = None,
    ):
        # If it's a rate limit, use 429, otherwise use 502 for API errors
        http_status = 429 if rate_limit_exceeded else 502

        super().__init__(
            message=f"GitHub API error: {message}",
            error_code="GITHUB_API_ERROR",
            details=details,
            status_code=http_status,
        )


class RateLimitExceededException(CodeReviewerException):
    """Raised when API rate limits are exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int = None,
        details: dict = None,
    ):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details,
            status_code=429,
        )
        self.retry_after = retry_after


# Exception Handlers


async def code_reviewer_exception_handler(
    request: Request, exc: CodeReviewerException
) -> JSONResponse:
    """Handle application-specific exceptions."""
    from app.utils.logger import logger

    logger.warning(
        f"Application exception: {exc.message}",
        extra={
            "exception_type": type(exc).__name__,
            "error_code": exc.error_code,
            "path": request.url.path,
            "method": request.method,
        },
    )

    # Use the status_code from the exception, or default to 500
    status_code = getattr(exc, "status_code", 500)

    # Add retry-after header for rate limit exceptions
    headers = {}
    if (
        isinstance(exc, RateLimitExceededException)
        and hasattr(exc, "retry_after")
        and exc.retry_after
    ):
        headers["Retry-After"] = str(exc.retry_after)

    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
        headers=headers if headers else None,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    from app.utils.logger import logger

    logger.warning(
        f"HTTP exception: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    from app.utils.logger import logger

    logger.warning(
        f"Validation error: {exc}",
        extra={
            "error_count": exc.error_count(),
            "path": request.url.path,
            "method": request.method,
        },
    )

    # Simplified error formatting
    errors = [
        {
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]

    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation failed",
            "details": errors,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )


async def database_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """Handle SQLAlchemy database errors."""
    from app.utils.logger import logger

    logger.error(
        f"Database error: {exc}",
        extra={
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Database operation failed",
            "error_code": "DATABASE_ERROR",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other unexpected exceptions."""
    from app.utils.logger import logger

    logger.error(
        f"Unexpected error: {exc}",
        extra={
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )


def setup_exception_handlers(app):
    """Register all exception handlers with the FastAPI app."""
    from app.utils.logger import logger

    # Application-specific exceptions
    app.add_exception_handler(CodeReviewerException, code_reviewer_exception_handler)

    # FastAPI exceptions
    app.add_exception_handler(HTTPException, http_exception_handler)

    # Pydantic validation errors
    app.add_exception_handler(ValidationError, validation_exception_handler)

    # Database errors
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)

    # Catch-all for unexpected errors
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("Exception handlers registered successfully")


__all__ = [
    # Exception classes
    "CodeReviewerException",
    "TaskNotFoundException",
    "TaskNotCompletedException",
    "InvalidRepositoryException",
    "GitHubAPIException",
    "RateLimitExceededException",
    # Exception handlers
    "setup_exception_handlers",
]
