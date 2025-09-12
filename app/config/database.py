"""
Database Connection and Engine Configuration

Provides database engine setup, connection pooling, and utilities.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.config.settings import get_settings
from app.utils.logger import logger


class DatabaseManager:
    """Database connection and session management"""

    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.async_session_factory: Optional[sessionmaker] = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize database engine and session factory"""
        if self._initialized:
            return

        settings = get_settings()

        # Convert PostgreSQL URL to async version if needed
        db_url = settings.database.url
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

        # Create async engine
        self.engine = create_async_engine(
            db_url,
            echo=settings.app.debug,  # Log SQL queries in debug mode
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=-1,
            pool_pre_ping=True,  # Validate connections before use
        )

        # Create async session factory
        self.async_session_factory = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        self._initialized = True
        logger.info("Database manager initialized successfully")

    async def create_tables(self) -> None:
        """Create all database tables"""
        if not self.engine:
            raise RuntimeError("Database not initialized")

        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

        logger.info("Database tables created successfully")

    async def drop_tables(self) -> None:
        """Drop all database tables (use with caution!)"""
        if not self.engine:
            raise RuntimeError("Database not initialized")

        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)

        logger.warning("All database tables dropped")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session with automatic cleanup"""
        if not self.async_session_factory:
            raise RuntimeError("Database not initialized")

        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def close(self) -> None:
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()


def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance"""
    return db_manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions"""
    if not db_manager._initialized:
        db_manager.initialize()

    async with db_manager.get_session() as session:
        yield session


async def init_database() -> None:
    """Initialize database on startup generally; not used on our application as migrations are managed by Alembic"""
    logger.info("Initializing database...")

    db_manager.initialize()

    # Create tables if they don't exist
    await db_manager.create_tables()

    logger.info("Database initialization completed")


async def close_database() -> None:
    """Close database connections on application shutdown"""
    logger.info("Closing database connections...")
    await db_manager.close()


__all__ = [
    "DatabaseManager",
    "db_manager",
    "get_database_manager",
    "get_db_session",
    "init_database",
    "close_database",
]
