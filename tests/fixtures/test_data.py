"""Test data creation utilities."""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from uuid import uuid4, UUID

from app.models.database import (
    AnalysisTask,
    AnalysisResult,
    AnalysisSummary,
    TaskStatus,
)


def create_test_task(
    repo_url: str = "https://github.com/testorg/testrepo",
    pr_number: int = 42,
    status: TaskStatus = TaskStatus.PENDING,
    progress: float = 0.0,
    github_token: Optional[str] = None,
    **kwargs,
) -> AnalysisTask:
    """Create a test analysis task."""
    task_data = {
        "id": uuid4(),
        "repo_url": repo_url,
        "pr_number": pr_number,
        "github_token": github_token,
        "status": status,
        "progress": progress,
        "created_at": datetime.now(timezone.utc),
        "started_at": datetime.now(timezone.utc)
        if status != TaskStatus.PENDING
        else None,
        "completed_at": datetime.now(timezone.utc) + timedelta(minutes=5)
        if status == TaskStatus.COMPLETED
        else None,
        "error_message": None,
        "retry_count": 0,
        "celery_task_id": f"task_{uuid4().hex[:8]}",
        "requested_by": "test_user",
        **kwargs,
    }

    return AnalysisTask(**task_data)


def create_test_analysis_result(
    task_id: UUID,
    file_name: str = "test_file.py",
    file_path: str = "app/test_file.py",
    language: str = "python",
    issues: Optional[list] = None,
    **kwargs,
) -> AnalysisResult:
    """Create a test analysis result."""
    if issues is None:
        issues = [
            {
                "type": "style",
                "severity": "low",
                "line": 10,
                "description": "Missing docstring",
                "suggestion": "Add function docstring",
                "confidence": 0.8,
            },
            {
                "type": "security",
                "severity": "high",
                "line": 25,
                "description": "SQL injection vulnerability",
                "suggestion": "Use parameterized queries",
                "confidence": 0.95,
            },
        ]

    result_data = {
        "id": uuid4(),
        "task_id": task_id,
        "file_name": file_name,
        "file_path": file_path,
        "file_size": len(file_name) * 100,  # Mock size
        "language": language,
        "issues": issues,
        "created_at": datetime.now(timezone.utc),
        "analysis_duration": 2.5,
        **kwargs,
    }

    return AnalysisResult(**result_data)


def create_test_analysis_summary(
    task_id: UUID, total_files: int = 3, total_issues: int = 5, **kwargs
) -> AnalysisSummary:
    """Create a test analysis summary."""
    summary_data = {
        "id": uuid4(),
        "task_id": task_id,
        "total_files": total_files,
        "total_issues": total_issues,
        "critical_issues": 1,
        "high_issues": 2,
        "medium_issues": 1,
        "low_issues": 1,
        "style_issues": 2,
        "bug_issues": 1,
        "performance_issues": 1,
        "security_issues": 1,
        "maintainability_issues": 0,
        "best_practice_issues": 0,
        "code_quality_score": 75.5,
        "maintainability_score": 80.0,
        "created_at": datetime.now(timezone.utc),
        **kwargs,
    }

    return AnalysisSummary(**summary_data)


def create_sample_pr_analysis_data() -> Dict[str, Any]:
    """Create comprehensive sample PR analysis data."""
    return {
        "pr_metadata": {
            "id": 123456789,
            "number": 42,
            "title": "Fix authentication security issues",
            "body": "This PR addresses several security vulnerabilities in the auth system.",
            "state": "open",
            "created_at": "2025-09-17T10:00:00Z",
            "updated_at": "2025-09-17T12:00:00Z",
            "author": {"login": "dev_user", "id": 12345, "type": "User"},
            "base": {"ref": "main", "sha": "abc123", "repo": "testorg/testrepo"},
            "head": {
                "ref": "fix/auth-security",
                "sha": "def456",
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
            "labels": ["security", "bug", "high-priority"],
        },
        "files_data": [
            {
                "filename": "app/auth/security.py",
                "language": "python",
                "content": '''"""Security module."""

import hashlib
import secrets

class SecurityManager:
    def validate_token(self, token):
        # Missing input validation
        return hashlib.md5(token.encode()).hexdigest()
''',
                "additions": 25,
                "deletions": 8,
                "changes": 33,
            },
            {
                "filename": "app/auth/models.py",
                "language": "python",
                "content": '''"""User models."""

class User:
    def __init__(self, username, password):
        self.username = username
        self.password = password  # Plain text password!
''',
                "additions": 15,
                "deletions": 3,
                "changes": 18,
            },
            {
                "filename": "tests/test_auth.py",
                "language": "python",
                "content": '''"""Authentication tests."""

def test_user_creation():
    user = User("test", "password123")
    assert user.username == "test"
''',
                "additions": 5,
                "deletions": 1,
                "changes": 6,
            },
        ],
        "expected_issues": {
            "app/auth/security.py": [
                {
                    "type": "security",
                    "severity": "critical",
                    "line": 8,
                    "description": "MD5 is cryptographically broken",
                    "suggestion": "Use SHA-256 or bcrypt for password hashing",
                    "confidence": 0.98,
                },
                {
                    "type": "bug",
                    "severity": "medium",
                    "line": 7,
                    "description": "Missing input validation",
                    "suggestion": "Add null and type checks for token parameter",
                    "confidence": 0.85,
                },
            ],
            "app/auth/models.py": [
                {
                    "type": "security",
                    "severity": "critical",
                    "line": 6,
                    "description": "Plain text password storage",
                    "suggestion": "Hash passwords before storing",
                    "confidence": 0.99,
                }
            ],
        },
    }


def create_celery_task_data() -> Dict[str, Any]:
    """Create sample Celery task data for testing."""
    return {
        "task_id": str(uuid4()),
        "repo_url": "https://github.com/testorg/testrepo",
        "pr_number": 42,
        "github_token": "github_pat_test_token",
        "status": "PENDING",
        "progress": 0.0,
        "result": None,
        "traceback": None,
        "meta": {
            "current": 0,
            "total": 100,
            "status": "Task queued",
        },
    }
