"""Test configuration for pytest."""

import os
import asyncio
from pathlib import Path
import sys

# Ensure we're in test mode
os.environ["ENVIRONMENT"] = "test"

# Configure minimal test environment variables
os.environ.setdefault("OPENAI_API_KEY", "test-api-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("API_KEY", "test-api-key")

# Set up asyncio event loop policy for tests
if os.name == "nt":  # Windows
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Add project root to Python path
project_root = Path(__file__).parent.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
