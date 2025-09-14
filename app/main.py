"""
FastAPI Main Application

Entry point for the Code Reviewer Agent API server.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import Settings, get_settings
from app.config.database import db_manager
from app.utils.logger import logger
from app.utils.exceptions import setup_exception_handlers
from app.api.v1.router import router as v1_router


# Initialize FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management - handle startup and shutdown"""
    # Startup
    logger.info("Starting up application...")

    # Initialize database connection (but not create tables - migrations handle that)
    db_manager.initialize()
    logger.info("Database connection initialized")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    await db_manager.close()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()

    app = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        description="Autonomous AI-powered code review agent for GitHub PRs",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    logger.info(f"CORS configured with origins: {settings.api.cors_origins}")

    # Setup exception handlers
    setup_exception_handlers(app)

    # Include API routers
    app.include_router(v1_router)

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "message": f"Welcome to {settings.app.name}",
            "version": settings.app.version,
            "docs": "/docs",
            "health": "/health",
            "api": "/api/v1",
        }

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "Ok!",
            "service": settings.app.name,
            "version": settings.app.version,
        }

    logger.info("FastAPI application configured successfully")
    return app


# Create app instance
app: FastAPI = create_app()


if __name__ == "__main__":
    import uvicorn

    settings: Settings = get_settings()

    logger.info(f"Starting server on {settings.api.host}:{settings.api.port}")

    uvicorn.run(
        "app.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.app.debug,
        log_level=settings.app.log_level.lower(),
    )
