"""Tests Package"""

# Test utilities and configurations

import os
import sys
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = (
    "postgresql://postgres:postgres@localhost:5433/code_review_test"
)
os.environ["REDIS_URL"] = "redis://localhost:6379/15"  # Use database 15 for tests
os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/15"
os.environ["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/15"
os.environ["OPENAI_API_KEY"] = "test-api-key"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["API_KEY"] = "test-api-key"
