"""
SQLModel Database Models

Defines all database models using SQLModel for type-safe ORM operations.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlmodel import Column, Field, JSON, Relationship, SQLModel


class TaskStatus(str, Enum):
    """Task execution status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IssueType(str, Enum):
    """Code issue classification"""

    STYLE = "style"
    BUG = "bug"
    PERFORMANCE = "performance"
    SECURITY = "security"
    MAINTAINABILITY = "maintainability"
    BEST_PRACTICE = "best_practice"


class IssueSeverity(str, Enum):
    """Issue severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnalysisTask(SQLModel, table=True):
    """Main analysis task tracking"""

    __tablename__ = "analysis_tasks"

    # Primary fields
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    repo_url: str = Field(max_length=500, index=True)
    pr_number: int = Field(index=True)
    github_token: Optional[str] = Field(default=None, max_length=500)

    # Status tracking
    status: TaskStatus = Field(default=TaskStatus.PENDING, index=True)
    progress: float = Field(default=0.0, ge=0.0, le=100.0)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Error handling
    error_message: Optional[str] = None
    retry_count: int = Field(default=0)

    # Metadata
    celery_task_id: Optional[str] = Field(max_length=255, index=True)
    requested_by: Optional[str] = Field(max_length=255)

    # Relationships
    results: List["AnalysisResult"] = Relationship(back_populates="task")
    summary: Optional["AnalysisSummary"] = Relationship(back_populates="task")


class AnalysisResult(SQLModel, table=True):
    """Individual file analysis results"""

    __tablename__ = "analysis_results"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    task_id: UUID = Field(foreign_key="analysis_tasks.id", index=True)

    # File information
    file_name: str = Field(max_length=1000, index=True)
    file_path: str = Field(max_length=2000)
    file_size: int = Field(default=0)
    language: Optional[str] = Field(max_length=50)

    # Analysis results (JSON fields)
    issues: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    metrics: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    suggestions: List[Dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON)
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    analysis_duration: Optional[float] = None  # seconds

    # Relationships
    task: AnalysisTask = Relationship(back_populates="results")


class AnalysisSummary(SQLModel, table=True):
    """Overall analysis summary"""

    __tablename__ = "analysis_summaries"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    task_id: UUID = Field(foreign_key="analysis_tasks.id", index=True)

    # Summary statistics
    total_files: int = Field(default=0)
    total_issues: int = Field(default=0)
    critical_issues: int = Field(default=0)
    high_issues: int = Field(default=0)
    medium_issues: int = Field(default=0)
    low_issues: int = Field(default=0)

    # Issue breakdown by type
    style_issues: int = Field(default=0)
    bug_issues: int = Field(default=0)
    performance_issues: int = Field(default=0)
    security_issues: int = Field(default=0)
    maintainability_issues: int = Field(default=0)
    best_practice_issues: int = Field(default=0)

    # Overall metrics
    code_quality_score: float = Field(default=0.0, ge=0.0, le=100.0)
    maintainability_score: float = Field(default=0.0, ge=0.0, le=100.0)

    # Recommendations (JSON field)
    overall_recommendations: List[str] = Field(
        default_factory=list, sa_column=Column(JSON)
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    task: AnalysisTask = Relationship(back_populates="summary")


# Export all models
__all__ = [
    "TaskStatus",
    "IssueType",
    "IssueSeverity",
    "AnalysisTask",
    "AnalysisResult",
    "AnalysisSummary",
]
