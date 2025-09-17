"""Test configuration for pytest."""

import os
import asyncio
from pathlib import Path

# Ensure we're in test mode
os.environ["ENVIRONMENT"] = "test"

# Configure test-specific environment variables
os.environ.setdefault(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/code_review_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/15")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/15")
os.environ.setdefault("OPENAI_API_KEY", "test-api-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("API_KEY", "test-api-key")

# Set up asyncio event loop policy for tests
if os.name == "nt":  # Windows
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Add project root to Python path
project_root = Path(__file__).parent.parent
import sys

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import pytest fixtures to make them available
pytest_plugins = [
    "tests.fixtures.database",
    "tests.fixtures.github_mock",
    "tests.fixtures.llm_mock",
    "tests.fixtures.test_data",
]
