"""
FastAPI Main Application

Entry point for the Code Reviewer Agent API server.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
from contextlib import asynccontextmanager

from app.config.settings import get_settings
from app.utils.logger import logger, log_api_request


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Code Reviewer Agent starting up...")
    yield
    # Shutdown
    logger.info("Code Reviewer Agent shutting down...")


# Initialize FastAPI app
def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()

    app = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        description="Autonomous AI-powered code review agent for GitHub PRs",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # Log API request
        log_api_request(
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            duration=process_time,
        )

        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        return response

    # Exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Global exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)},
        )

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": settings.app.name,
            "version": settings.app.version,
        }

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": f"Welcome to {settings.app.name}",
            "version": settings.app.version,
            "docs": "/docs",
            "health": "/health",
        }

    logger.info("FastAPI application configured successfully")
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    logger.info(f"Starting server on {settings.api.host}:{settings.api.port}")

    uvicorn.run(
        "app.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.app.debug,
        log_level=settings.app.log_level.lower(),
    )
