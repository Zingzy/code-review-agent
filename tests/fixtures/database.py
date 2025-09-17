"""Database test fixtures and utilities."""

import asyncio
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlmodel import SQLModel


# Test database URL - separate from main database
TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/code_review_test"
TEST_DATABASE_URL_ASYNC = (
    "postgresql+asyncpg://postgres:postgres@localhost:5433/code_review_test"
)


@pytest_asyncio.fixture(scope="session")
async def test_db_engine():
    """Create test database engine for the session."""
    # Create synchronous engine for database creation
    sync_engine = create_engine(
        "postgresql://postgres:postgres@localhost:5433/postgres",
        isolation_level="AUTOCOMMIT",
    )

    # Create test database if it doesn't exist
    with sync_engine.connect() as conn:
        # Check if test database exists
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'code_review_test'")
        )
        if not result.fetchone():
            conn.execute(text("CREATE DATABASE code_review_test"))

    sync_engine.dispose()

    # Create async engine for tests
    async_engine = create_async_engine(
        TEST_DATABASE_URL_ASYNC,
        echo=False,
        pool_pre_ping=True,
    )

    yield async_engine

    # Cleanup
    await async_engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def create_test_tables(test_db_engine):
    """Create test tables once per session."""
    async with test_db_engine.begin() as conn:
        # Drop all tables first
        await conn.run_sync(SQLModel.metadata.drop_all)
        # Create all tables
        await conn.run_sync(SQLModel.metadata.create_all)

    yield

    # Cleanup tables after session
    async with test_db_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture
async def test_db_session(
    test_db_engine, create_test_tables
) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with transaction rollback."""
    async_session_maker = async_sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        # Start a transaction
        trans = await session.begin()

        try:
            yield session
        finally:
            # Always rollback the transaction
            await trans.rollback()
            await session.close()


@pytest.fixture
def cleanup_test_db():
    """Cleanup test database after tests."""
    yield

    # Additional cleanup if needed
    pass


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
