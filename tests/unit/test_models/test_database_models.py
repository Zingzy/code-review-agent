"""Tests for database models."""

from datetime import datetime, timezone
from uuid import uuid4

from app.models.database import (
    AnalysisTask,
    AnalysisResult,
    AnalysisSummary,
    TaskStatus,
    IssueType,
    IssueSeverity,
)


class TestAnalysisTask:
    """Test AnalysisTask model."""

    def test_create_analysis_task(self):
        """Test creating an analysis task."""
        task = AnalysisTask(
            repo_url="https://github.com/testorg/testrepo",
            pr_number=42,
            github_token="test_token",
        )

        assert task.repo_url == "https://github.com/testorg/testrepo"
        assert task.pr_number == 42
        assert task.github_token == "test_token"
        assert task.status == TaskStatus.PENDING
        assert task.progress == 0.0
        assert task.retry_count == 0
        assert task.id is not None
        assert isinstance(task.created_at, datetime)

    def test_task_status_enum(self):
        """Test TaskStatus enum values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.PROCESSING.value == "processing"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_task_status_transition(self):
        """Test task status transitions."""
        task = AnalysisTask(
            repo_url="https://github.com/testorg/testrepo",
            pr_number=42,
        )

        # Initial state
        assert task.status == TaskStatus.PENDING
        assert task.started_at is None
        assert task.completed_at is None

        # Start processing
        task.status = TaskStatus.PROCESSING
        task.started_at = datetime.now(timezone.utc)
        task.progress = 50.0

        assert task.status == TaskStatus.PROCESSING
        assert task.started_at is not None
        assert task.progress == 50.0

        # Complete task
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)
        task.progress = 100.0

        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert task.progress == 100.0

    def test_task_with_error(self):
        """Test task with error handling."""
        task = AnalysisTask(
            repo_url="https://github.com/testorg/testrepo",
            pr_number=42,
        )

        task.status = TaskStatus.FAILED
        task.error_message = "GitHub API rate limit exceeded"
        task.retry_count = 3

        assert task.status == TaskStatus.FAILED
        assert task.error_message == "GitHub API rate limit exceeded"
        assert task.retry_count == 3

    def test_task_defaults(self):
        """Test task default values."""
        task = AnalysisTask(
            repo_url="https://github.com/testorg/testrepo",
            pr_number=42,
        )

        assert task.status == TaskStatus.PENDING
        assert task.progress == 0.0
        assert task.retry_count == 0
        assert task.github_token is None
        assert task.error_message is None
        assert task.celery_task_id is None
        assert task.requested_by is None


class TestAnalysisResult:
    """Test AnalysisResult model."""

    def test_create_analysis_result(self):
        """Test creating an analysis result."""
        task_id = uuid4()
        issues = [
            {
                "type": "style",
                "severity": "low",
                "line": 10,
                "description": "Missing docstring",
                "suggestion": "Add function docstring",
                "confidence": 0.8,
            }
        ]

        result = AnalysisResult(
            task_id=task_id,
            file_name="test_file.py",
            file_path="app/test_file.py",
            file_size=1024,
            language="python",
            issues=issues,
            analysis_duration=2.5,
        )

        assert result.task_id == task_id
        assert result.file_name == "test_file.py"
        assert result.file_path == "app/test_file.py"
        assert result.file_size == 1024
        assert result.language == "python"
        assert result.issues == issues
        assert result.analysis_duration == 2.5
        assert isinstance(result.created_at, datetime)

    def test_empty_issues_list(self):
        """Test analysis result with empty issues list."""
        result = AnalysisResult(
            task_id=uuid4(),
            file_name="clean_file.py",
            file_path="app/clean_file.py",
            language="python",
        )

        assert result.issues == []
        assert result.file_size == 0
        assert result.analysis_duration is None

    def test_multiple_issues(self):
        """Test analysis result with multiple issues."""
        issues = [
            {
                "type": "security",
                "severity": "high",
                "line": 15,
                "description": "SQL injection vulnerability",
                "suggestion": "Use parameterized queries",
                "confidence": 0.95,
            },
            {
                "type": "style",
                "severity": "low",
                "line": 8,
                "description": "Missing docstring",
                "suggestion": "Add comprehensive docstring",
                "confidence": 0.8,
            },
            {
                "type": "performance",
                "severity": "medium",
                "line": 25,
                "description": "Inefficient loop",
                "suggestion": "Use list comprehension",
                "confidence": 0.7,
            },
        ]

        result = AnalysisResult(
            task_id=uuid4(),
            file_name="complex_file.py",
            file_path="app/complex_file.py",
            language="python",
            issues=issues,
        )

        assert len(result.issues) == 3
        assert result.issues[0]["type"] == "security"
        assert result.issues[1]["type"] == "style"
        assert result.issues[2]["type"] == "performance"


class TestAnalysisSummary:
    """Test AnalysisSummary model."""

    def test_create_analysis_summary(self):
        """Test creating an analysis summary."""
        task_id = uuid4()
        summary = AnalysisSummary(
            task_id=task_id,
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

        assert summary.task_id == task_id
        assert summary.total_files == 5
        assert summary.total_issues == 10
        assert summary.critical_issues == 1
        assert summary.high_issues == 2
        assert summary.medium_issues == 3
        assert summary.low_issues == 4
        assert summary.code_quality_score == 75.5
        assert summary.maintainability_score == 80.0
        assert isinstance(summary.created_at, datetime)

    def test_summary_defaults(self):
        """Test summary default values."""
        summary = AnalysisSummary(task_id=uuid4())

        assert summary.total_files == 0
        assert summary.total_issues == 0
        assert summary.critical_issues == 0
        assert summary.high_issues == 0
        assert summary.medium_issues == 0
        assert summary.low_issues == 0
        assert summary.style_issues == 0
        assert summary.bug_issues == 0
        assert summary.performance_issues == 0
        assert summary.security_issues == 0
        assert summary.maintainability_issues == 0
        assert summary.best_practice_issues == 0
        assert summary.code_quality_score == 0.0
        assert summary.maintainability_score == 0.0

    def test_issue_counts_consistency(self):
        """Test that issue counts are consistent."""
        summary = AnalysisSummary(
            task_id=uuid4(),
            total_files=3,
            total_issues=15,
            critical_issues=2,
            high_issues=4,
            medium_issues=5,
            low_issues=4,
        )

        # Severity breakdown should sum to total
        severity_sum = (
            summary.critical_issues
            + summary.high_issues
            + summary.medium_issues
            + summary.low_issues
        )
        assert severity_sum == summary.total_issues

    def test_score_ranges(self):
        """Test score value ranges."""
        # Valid scores
        summary = AnalysisSummary(
            task_id=uuid4(),
            code_quality_score=85.5,
            maintainability_score=75.0,
        )

        assert 0.0 <= summary.code_quality_score <= 100.0
        assert 0.0 <= summary.maintainability_score <= 100.0


class TestEnums:
    """Test enum classes."""

    def test_issue_type_enum(self):
        """Test IssueType enum."""
        assert IssueType.STYLE.value == "style"
        assert IssueType.BUG.value == "bug"
        assert IssueType.PERFORMANCE.value == "performance"
        assert IssueType.SECURITY.value == "security"
        assert IssueType.MAINTAINABILITY.value == "maintainability"
        assert IssueType.BEST_PRACTICE.value == "best_practice"

    def test_issue_severity_enum(self):
        """Test IssueSeverity enum."""
        assert IssueSeverity.LOW.value == "low"
        assert IssueSeverity.MEDIUM.value == "medium"
        assert IssueSeverity.HIGH.value == "high"
        assert IssueSeverity.CRITICAL.value == "critical"

    def test_enum_membership(self):
        """Test enum membership."""
        # Test valid values
        assert "pending" in [status.value for status in TaskStatus]
        assert "security" in [issue_type.value for issue_type in IssueType]
        assert "high" in [severity.value for severity in IssueSeverity]

        # Test all TaskStatus values
        task_statuses = {status.value for status in TaskStatus}
        expected_statuses = {
            "pending",
            "processing",
            "completed",
            "failed",
            "cancelled",
        }
        assert task_statuses == expected_statuses
