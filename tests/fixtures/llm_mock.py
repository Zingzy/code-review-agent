"""LLM service mocking utilities for tests."""

from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock
import pytest

from app.services.llm_service import LLMService


@pytest.fixture
def mock_openai_responses() -> Dict[str, Any]:
    """Sample OpenAI API responses for testing."""
    return {
        "analysis_response": {
            "choices": [
                {
                    "message": {
                        "content": """[
                            {
                                "type": "security",
                                "severity": "high",
                                "line": 15,
                                "description": "Potential SQL injection vulnerability",
                                "suggestion": "Use parameterized queries instead of string concatenation",
                                "confidence": 0.9
                            },
                            {
                                "type": "style",
                                "severity": "low",
                                "line": 8,
                                "description": "Missing docstring for function",
                                "suggestion": "Add comprehensive docstring describing function purpose",
                                "confidence": 0.8
                            }
                        ]"""
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 200,
                "total_tokens": 350,
            },
        },
        "error_response": {
            "error": {
                "message": "Invalid API key",
                "type": "invalid_request_error",
                "code": "invalid_api_key",
            }
        },
    }


@pytest.fixture
def mock_llm_service(mock_openai_responses) -> Mock:
    """Mock LLM service with realistic responses."""
    service = AsyncMock(spec=LLMService)

    # Configure successful analysis response
    service.analyze_code.return_value = [
        {
            "type": "security",
            "severity": "high",
            "line": 15,
            "description": "Potential SQL injection vulnerability",
            "suggestion": "Use parameterized queries instead of string concatenation",
            "confidence": 0.9,
        },
        {
            "type": "style",
            "severity": "low",
            "line": 8,
            "description": "Missing docstring for function",
            "suggestion": "Add comprehensive docstring describing function purpose",
            "confidence": 0.8,
        },
    ]

    # Configure chat completion method
    service.chat_completion.return_value = {
        "choices": [{"message": {"content": "Analysis completed successfully"}}]
    }

    # Configure provider info
    service.provider = "openai"
    service.model = "gpt-4"
    service.is_available = True

    return service


@pytest.fixture
def mock_llm_service_with_errors() -> Mock:
    """Mock LLM service that simulates various error conditions."""
    service = AsyncMock(spec=LLMService)

    # Configure to raise exceptions
    service.analyze_code.side_effect = Exception("API rate limit exceeded")
    service.chat_completion.side_effect = Exception("Model not available")

    service.provider = "openai"
    service.model = "gpt-4"
    service.is_available = False

    return service


@pytest.fixture
def sample_code_analysis_request() -> Dict[str, Any]:
    """Sample code analysis request for testing."""
    return {
        "file_path": "app/auth/security.py",
        "code_content": '''"""Security module for authentication."""

import hashlib
import secrets
from typing import Optional


class SecurityManager:
    """Handles security operations."""
    
    def __init__(self):
        self.salt = secrets.token_bytes(32)
    
    def validate_token(self, token: str) -> bool:
        """Validate authentication token."""
        if not token:
            return False
        
        # Potential security issue: hardcoded salt
        hashed = hashlib.pbkdf2_hmac('sha256', token.encode(), b'fixed_salt', 100000)
        return len(hashed) == 32
''',
        "language": "python",
    }


@pytest.fixture
def sample_analysis_issues() -> List[Dict[str, Any]]:
    """Sample analysis issues for testing."""
    return [
        {
            "type": "security",
            "severity": "high",
            "line": 20,
            "description": "Hardcoded salt in password hashing",
            "suggestion": "Use randomly generated salt stored securely",
            "confidence": 0.95,
        },
        {
            "type": "bug",
            "severity": "medium",
            "line": 17,
            "description": "Missing input validation",
            "suggestion": "Add proper input validation and sanitization",
            "confidence": 0.85,
        },
        {
            "type": "style",
            "severity": "low",
            "line": 12,
            "description": "Variable name could be more descriptive",
            "suggestion": "Consider renaming 'hashed' to 'hashed_token'",
            "confidence": 0.7,
        },
        {
            "type": "performance",
            "severity": "medium",
            "line": 20,
            "description": "High iteration count may cause performance issues",
            "suggestion": "Consider using adaptive iteration count based on hardware",
            "confidence": 0.8,
        },
    ]
