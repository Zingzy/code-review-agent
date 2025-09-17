"""
Pydantic Schemas for API

Defines request/response models for the API endpoints.
"""

import re
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.database import IssueType, IssueSeverity, TaskStatus


# Request Models
class AnalysisRequest(BaseModel):
    """Request model for PR analysis"""

    repo_url: str = Field(..., description="GitHub repository URL", max_length=500)
    pr_number: int = Field(..., description="Pull request number", gt=0, le=999999)
    github_token: Optional[str] = Field(
        None, description="Optional GitHub token for private repos"
    )

    @field_validator("repo_url")
    @classmethod
    def validate_github_repo_url(cls, v: str) -> str:
        """Validate and normalize GitHub repository URL."""
        # Basic GitHub URL validation
        github_pattern = r"^https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+/?$"

        normalized_url = v.strip().rstrip("/")

        if not re.match(github_pattern, normalized_url):
            raise ValueError(
                "Invalid GitHub repository URL format. Expected: https://github.com/owner/repo"
            )

        return normalized_url


class TaskCancelRequest(BaseModel):
    """Request model for task cancellation"""

    reason: Optional[str] = Field(None, description="Reason for cancellation")


# Response Models
class TaskResponse(BaseModel):
    """Basic task response"""

    task_id: UUID
    status: TaskStatus
    message: str


class TaskStatusResponse(BaseModel):
    """Task status response"""

    task_id: UUID
    status: TaskStatus
    progress: float = Field(..., ge=0.0, le=100.0)
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class IssueDetail(BaseModel):
    """Individual code issue detail"""

    type: IssueType
    severity: IssueSeverity = Field(default=IssueSeverity.LOW)
    line: int = Field(..., gt=0, description="Line number of the issue")
    description: str = Field(..., min_length=1)
    suggestion: str = Field(..., min_length=1)
    rule: Optional[str] = None
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class FileAnalysisResponse(BaseModel):
    """File analysis response model"""

    name: str
    path: str
    language: Optional[str]
    size: int = Field(..., ge=0)
    issues: List[IssueDetail] = []


class AnalysisSummaryResponse(BaseModel):
    """Analysis summary response model"""

    total_files: int = Field(..., ge=0)
    total_issues: int = Field(..., ge=0)
    critical_issues: int = Field(..., ge=0)
    high_issues: int = Field(..., ge=0)
    medium_issues: int = Field(..., ge=0)
    low_issues: int = Field(..., ge=0)

    # Issue breakdown by type
    style_issues: int = Field(..., ge=0)
    bug_issues: int = Field(..., ge=0)
    performance_issues: int = Field(..., ge=0)
    security_issues: int = Field(..., ge=0)
    maintainability_issues: int = Field(..., ge=0)
    best_practice_issues: int = Field(..., ge=0)

    # Overall metrics
    code_quality_score: float = Field(..., ge=0.0, le=100.0)
    maintainability_score: float = Field(..., ge=0.0, le=100.0)


class AnalysisResponse(BaseModel):
    """Complete analysis response"""

    task_id: UUID
    status: TaskStatus
    progress: float = Field(..., ge=0.0, le=100.0)
    files: List[FileAnalysisResponse] = []
    summary: Optional[AnalysisSummaryResponse] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    analysis_duration: Optional[float] = Field(None, ge=0.0)
    error_message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response model"""

    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Export all schemas
__all__ = [
    "AnalysisRequest",
    "TaskCancelRequest",
    "TaskResponse",
    "TaskStatusResponse",
    "IssueDetail",
    "FileAnalysisResponse",
    "AnalysisSummaryResponse",
    "AnalysisResponse",
    "ErrorResponse",
]
