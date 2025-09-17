"""Tests for Pydantic schemas."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import ValidationError

from app.models.schemas import (
    AnalysisRequest,
    TaskResponse,
    TaskStatusResponse,
    IssueDetail,
    FileAnalysisResponse,
    AnalysisSummaryResponse,
    ErrorResponse,
)
from app.models.database import TaskStatus, IssueType, IssueSeverity


class TestAnalysisRequest:
    """Test AnalysisRequest schema."""

    def test_valid_analysis_request(self):
        """Test valid analysis request."""
        request = AnalysisRequest(
            repo_url="https://github.com/testorg/testrepo",
            pr_number=42,
            github_token="github_pat_test_token",
        )

        assert request.repo_url == "https://github.com/testorg/testrepo"
        assert request.pr_number == 42
        assert request.github_token == "github_pat_test_token"

    def test_request_without_token(self):
        """Test request without GitHub token."""
        request = AnalysisRequest(
            repo_url="https://github.com/testorg/testrepo",
            pr_number=42,
        )

        assert request.repo_url == "https://github.com/testorg/testrepo"
        assert request.pr_number == 42
        assert request.github_token is None

    def test_invalid_repo_url(self):
        """Test invalid repository URL."""
        with pytest.raises(ValidationError) as exc_info:
            AnalysisRequest(
                repo_url="invalid-url",
                pr_number=42,
            )

        assert "Invalid GitHub repository URL format" in str(exc_info.value)

    @pytest.mark.parametrize("url", [
        "https://github.com/owner/repo",
        "https://github.com/owner/repo/", 
        "https://github.com/user_name/repo-name",
        "https://github.com/org123/project_name",
    ])
    def test_various_valid_repo_urls(self, url):
        """Test various valid repository URL formats."""
        request = AnalysisRequest(repo_url=url, pr_number=1)
        # URL should be normalized (trailing slash removed)
        assert not request.repo_url.endswith("/") or request.repo_url == url

    def test_invalid_pr_number(self):
        """Test invalid PR numbers."""
        with pytest.raises(ValidationError):
            AnalysisRequest(
                repo_url="https://github.com/testorg/testrepo",
                pr_number=0,  # Should be > 0
            )

        with pytest.raises(ValidationError):
            AnalysisRequest(
                repo_url="https://github.com/testorg/testrepo",
                pr_number=-1,  # Should be > 0
            )

        with pytest.raises(ValidationError):
            AnalysisRequest(
                repo_url="https://github.com/testorg/testrepo",
                pr_number=1000000,  # Should be <= 999999
            )


class TestTaskResponse:
    """Test TaskResponse schema."""

    def test_task_response(self):
        """Test task response creation."""
        task_id = uuid4()
        response = TaskResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="Analysis task queued successfully",
        )

        assert response.task_id == task_id
        assert response.status == TaskStatus.PENDING
        assert response.message == "Analysis task queued successfully"


class TestTaskStatusResponse:
    """Test TaskStatusResponse schema."""

    def test_complete_task_status(self):
        """Test complete task status response."""
        task_id = uuid4()
        created_at = datetime.now(timezone.utc)
        started_at = datetime.now(timezone.utc)
        completed_at = datetime.now(timezone.utc)

        response = TaskStatusResponse(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            progress=100.0,
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
            retry_count=0,
        )

        assert response.task_id == task_id
        assert response.status == TaskStatus.COMPLETED
        assert response.progress == 100.0
        assert response.created_at == created_at
        assert response.started_at == started_at
        assert response.completed_at == completed_at
        assert response.error_message is None
        assert response.retry_count == 0

    def test_failed_task_status(self):
        """Test failed task status response."""
        task_id = uuid4()
        response = TaskStatusResponse(
            task_id=task_id,
            status=TaskStatus.FAILED,
            progress=50.0,
            created_at=datetime.now(timezone.utc),
            error_message="GitHub API rate limit exceeded",
            retry_count=3,
        )

        assert response.status == TaskStatus.FAILED
        assert response.progress == 50.0
        assert response.error_message == "GitHub API rate limit exceeded"
        assert response.retry_count == 3

    def test_invalid_progress(self):
        """Test invalid progress values."""
        task_id = uuid4()

        # Progress > 100
        with pytest.raises(ValidationError):
            TaskStatusResponse(
                task_id=task_id,
                status=TaskStatus.PROCESSING,
                progress=150.0,
                created_at=datetime.now(timezone.utc),
            )

        # Progress < 0
        with pytest.raises(ValidationError):
            TaskStatusResponse(
                task_id=task_id,
                status=TaskStatus.PROCESSING,
                progress=-10.0,
                created_at=datetime.now(timezone.utc),
            )


class TestIssueDetail:
    """Test IssueDetail schema."""

    def test_valid_issue_detail(self):
        """Test valid issue detail."""
        issue = IssueDetail(
            type=IssueType.SECURITY,
            severity=IssueSeverity.HIGH,
            line=15,
            description="SQL injection vulnerability",
            suggestion="Use parameterized queries",
            confidence=0.95,
        )

        assert issue.type == IssueType.SECURITY
        assert issue.severity == IssueSeverity.HIGH
        assert issue.line == 15
        assert issue.description == "SQL injection vulnerability"
        assert issue.suggestion == "Use parameterized queries"
        assert issue.confidence == 0.95

    def test_issue_with_defaults(self):
        """Test issue detail with default values."""
        issue = IssueDetail(
            type=IssueType.STYLE,
            line=10,
            description="Missing docstring",
            suggestion="Add function docstring",
        )

        assert issue.severity == IssueSeverity.LOW  # Default
        assert issue.confidence == 0.8  # Default

    def test_invalid_line_number(self):
        """Test invalid line numbers."""
        with pytest.raises(ValidationError):
            IssueDetail(
                type=IssueType.STYLE,
                line=0,  # Should be > 0
                description="Issue description",
                suggestion="Fix suggestion",
            )

    def test_invalid_confidence(self):
        """Test invalid confidence values."""
        with pytest.raises(ValidationError):
            IssueDetail(
                type=IssueType.STYLE,
                line=10,
                description="Issue description",
                suggestion="Fix suggestion",
                confidence=1.5,  # Should be <= 1.0
            )


class TestFileAnalysisResponse:
    """Test FileAnalysisResponse schema."""

    def test_file_analysis_with_issues(self):
        """Test file analysis response with issues."""
        issues = [
            IssueDetail(
                type=IssueType.SECURITY,
                severity=IssueSeverity.HIGH,
                line=15,
                description="Security issue",
                suggestion="Fix it",
            ),
            IssueDetail(
                type=IssueType.STYLE,
                line=8,
                description="Style issue",
                suggestion="Fix style",
            ),
        ]

        response = FileAnalysisResponse(
            name="security.py",
            path="app/auth/security.py",
            language="python",
            size=1024,
            issues=issues,
        )

        assert response.name == "security.py"
        assert response.path == "app/auth/security.py"
        assert response.language == "python"
        assert response.size == 1024
        assert len(response.issues) == 2

    def test_file_analysis_no_issues(self):
        """Test file analysis response with no issues."""
        response = FileAnalysisResponse(
            name="clean_file.py",
            path="app/clean_file.py",
            language="python",
            size=512,
        )

        assert response.issues == []
        assert response.language == "python"

    def test_invalid_file_size(self):
        """Test invalid file size."""
        with pytest.raises(ValidationError):
            FileAnalysisResponse(
                name="file.py",
                path="app/file.py",
                size=-1,  # Should be >= 0
            )


class TestAnalysisSummaryResponse:
    """Test AnalysisSummaryResponse schema."""

    def test_complete_summary(self):
        """Test complete analysis summary."""
        summary = AnalysisSummaryResponse(
            total_files=5,
            total_issues=10,
            critical_issues=1,
            high_issues=2,
            medium_issues=3,
            low_issues=4,
            style_issues=3,
            bug_issues=2,
            performance_issues=2,
            security_issues=2,
            maintainability_issues=1,
            best_practice_issues=0,
            code_quality_score=75.5,
            maintainability_score=80.0,
        )

        assert summary.total_files == 5
        assert summary.total_issues == 10
        assert summary.code_quality_score == 75.5
        assert summary.maintainability_score == 80.0

    def test_invalid_scores(self):
        """Test invalid score values."""
        with pytest.raises(ValidationError):
            AnalysisSummaryResponse(
                total_files=1,
                total_issues=1,
                critical_issues=0,
                high_issues=0,
                medium_issues=0,
                low_issues=1,
                style_issues=1,
                bug_issues=0,
                performance_issues=0,
                security_issues=0,
                maintainability_issues=0,
                best_practice_issues=0,
                code_quality_score=150.0,  # Should be <= 100
                maintainability_score=50.0,
            )


class TestErrorResponse:
    """Test ErrorResponse schema."""

    def test_error_response(self):
        """Test error response creation."""
        error = ErrorResponse(
            error="Validation failed",
            detail="Invalid repository URL format",
        )

        assert error.error == "Validation failed"
        assert error.detail == "Invalid repository URL format"
        assert isinstance(error.timestamp, datetime)

    def test_error_response_minimal(self):
        """Test error response with minimal data."""
        error = ErrorResponse(error="Something went wrong")

        assert error.error == "Something went wrong"
        assert error.detail is None
        assert isinstance(error.timestamp, datetime)
