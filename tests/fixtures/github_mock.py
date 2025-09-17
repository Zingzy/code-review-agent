"""GitHub API mocking utilities for tests."""

from typing import Dict, Any
from unittest.mock import Mock
import pytest
import responses

from app.services.github import GitHubService


@pytest.fixture
def sample_pr_data() -> Dict[str, Any]:
    """Sample pull request data for testing."""
    return {
        "id": 123456789,
        "number": 42,
        "title": "Fix critical bug in authentication",
        "body": "This PR fixes a critical security vulnerability in the authentication system.",
        "state": "open",
        "created_at": "2025-09-17T10:00:00Z",
        "updated_at": "2025-09-17T12:00:00Z",
        "merged_at": None,
        "closed_at": None,
        "author": {
            "login": "testuser",
            "id": 12345,
            "type": "User",
        },
        "base": {
            "ref": "main",
            "sha": "abc123def456",
            "repo": "testorg/testrepo",
        },
        "head": {
            "ref": "feature/auth-fix",
            "sha": "def456ghi789",
            "repo": "testorg/testrepo",
        },
        "stats": {
            "additions": 45,
            "deletions": 12,
            "changed_files": 3,
            "commits": 5,
        },
        "mergeable": True,
        "draft": False,
        "labels": ["bug", "security", "high-priority"],
    }


@pytest.fixture
def sample_pr_files() -> Dict[str, Any]:
    """Sample pull request files data for testing."""
    return {
        "files": [
            {
                "filename": "app/auth/security.py",
                "previous_filename": None,
                "status": "modified",
                "additions": 25,
                "deletions": 8,
                "changes": 33,
                "sha": "abc123",
                "blob_url": "https://github.com/testorg/testrepo/blob/def456/app/auth/security.py",
                "raw_url": "https://github.com/testorg/testrepo/raw/def456/app/auth/security.py",
                "patch": "@@ -10,8 +10,25 @@ class SecurityManager:\\n def validate_token(self, token):\\n-    # Old insecure validation\\n+    # New secure validation\\n",
                "size": 1024,
            },
            {
                "filename": "app/auth/models.py",
                "previous_filename": None,
                "status": "modified",
                "additions": 15,
                "deletions": 3,
                "changes": 18,
                "sha": "def456",
                "blob_url": "https://github.com/testorg/testrepo/blob/def456/app/auth/models.py",
                "raw_url": "https://github.com/testorg/testrepo/raw/def456/app/auth/models.py",
                "patch": "@@ -5,3 +5,15 @@ class User:\\n     email: str\\n+    # Added security fields\\n",
                "size": 512,
            },
            {
                "filename": "tests/test_auth.py",
                "previous_filename": None,
                "status": "added",
                "additions": 5,
                "deletions": 1,
                "changes": 6,
                "sha": "ghi789",
                "blob_url": "https://github.com/testorg/testrepo/blob/def456/tests/test_auth.py",
                "raw_url": "https://github.com/testorg/testrepo/raw/def456/tests/test_auth.py",
                "patch": "@@ -0,0 +1,5 @@\\n+def test_security():\\n+    pass\\n",
                "size": 256,
            },
        ],
        "metadata": {
            "total_files_in_pr": 3,
            "processed_files": 3,
            "total_size_bytes": 1792,
            "truncated": False,
        },
    }


@pytest.fixture
def sample_file_content() -> Dict[str, Any]:
    """Sample file content data for testing."""
    return {
        "path": "app/auth/security.py",
        "name": "security.py",
        "size": 1024,
        "sha": "abc123def456",
        "type": "file",
        "encoding": "base64",
        "content": """\"\"\"Security module for authentication.\"\"\"

import hashlib
import secrets
from typing import Optional


class SecurityManager:
    \"\"\"Handles security operations.\"\"\"
    
    def __init__(self):
        self.salt = secrets.token_bytes(32)
    
    def validate_token(self, token: str) -> bool:
        \"\"\"Validate authentication token.\"\"\"
        if not token:
            return False
        
        # New secure validation logic
        hashed = hashlib.pbkdf2_hmac('sha256', token.encode(), self.salt, 100000)
        return len(hashed) == 32
    
    def generate_token(self) -> str:
        \"\"\"Generate secure token.\"\"\"
        return secrets.token_urlsafe(32)
""",
        "is_text": True,
        "download_url": "https://api.github.com/repos/testorg/testrepo/contents/app/auth/security.py",
        "html_url": "https://github.com/testorg/testrepo/blob/main/app/auth/security.py",
    }


@responses.activate
@pytest.fixture
def mock_github_api(sample_pr_data, sample_pr_files, sample_file_content):
    """Mock GitHub API responses using responses library."""

    # Mock repository API
    responses.add(
        responses.GET,
        "https://api.github.com/repos/testorg/testrepo",
        json={
            "id": 123456,
            "full_name": "testorg/testrepo",
            "name": "testrepo",
            "owner": {"login": "testorg"},
            "private": False,
            "html_url": "https://github.com/testorg/testrepo",
        },
        status=200,
    )

    # Mock pull request API
    responses.add(
        responses.GET,
        "https://api.github.com/repos/testorg/testrepo/pulls/42",
        json={
            **sample_pr_data,
            "user": sample_pr_data["author"],
            "base": {
                **sample_pr_data["base"],
                "repo": {"full_name": "testorg/testrepo"},
            },
            "head": {
                **sample_pr_data["head"],
                "repo": {"full_name": "testorg/testrepo"},
            },
        },
        status=200,
    )

    # Mock pull request files API
    responses.add(
        responses.GET,
        "https://api.github.com/repos/testorg/testrepo/pulls/42/files",
        json=sample_pr_files["files"],
        status=200,
    )

    # Mock file content API
    responses.add(
        responses.GET,
        "https://api.github.com/repos/testorg/testrepo/contents/app/auth/security.py",
        json=sample_file_content,
        status=200,
    )

    # Mock rate limit API
    responses.add(
        responses.GET,
        "https://api.github.com/rate_limit",
        json={
            "rate": {
                "limit": 5000,
                "remaining": 4999,
                "reset": 1632150000,
                "used": 1,
            }
        },
        status=200,
    )

    return responses


@pytest.fixture
def mock_github_service(mock_github_api) -> Mock:
    """Mock GitHub service with realistic responses."""
    service = Mock(spec=GitHubService)

    # Configure the mock methods
    service.get_pull_request_metadata.return_value = {
        "id": 123456789,
        "number": 42,
        "title": "Fix critical bug in authentication",
        "body": "This PR fixes a critical security vulnerability.",
        "state": "open",
        "created_at": "2025-09-17T10:00:00Z",
        "updated_at": "2025-09-17T12:00:00Z",
        "merged_at": None,
        "closed_at": None,
        "author": {"login": "testuser", "id": 12345, "type": "User"},
        "base": {"ref": "main", "sha": "abc123def456", "repo": "testorg/testrepo"},
        "head": {
            "ref": "feature/auth-fix",
            "sha": "def456ghi789",
            "repo": "testorg/testrepo",
        },
        "stats": {"additions": 45, "deletions": 12, "changed_files": 3, "commits": 5},
        "mergeable": True,
        "draft": False,
        "labels": ["bug", "security", "high-priority"],
    }

    service.get_pull_request_files.return_value = {
        "files": [
            {
                "filename": "app/auth/security.py",
                "status": "modified",
                "additions": 25,
                "deletions": 8,
                "changes": 33,
                "content": "# Security improvements",
            }
        ],
        "metadata": {"total_files_in_pr": 1, "processed_files": 1},
    }

    service.get_file_content.return_value = {
        "content": "# Sample Python code for testing",
        "is_text": True,
        "size": 1024,
    }

    service.is_authenticated = True
    service.rate_limit_remaining = 4999

    return service
