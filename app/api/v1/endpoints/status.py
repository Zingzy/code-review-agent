"""
Task Status and Results API Endpoints

Handles status checking and result retrieval for analysis tasks.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config.database import get_db_session
from app.models.schemas import (
    TaskStatusResponse,
    AnalysisResponse,
    AnalysisSummaryResponse,
    FileAnalysisResponse,
    IssueDetail,
    ErrorResponse,
)
from app.models.database import AnalysisTask, IssueType, IssueSeverity
from app.utils.logger import logger

router = APIRouter()


def _convert_issues_to_details(issues_data: list, task_id: UUID) -> list[IssueDetail]:
    """Convert database issue data to IssueDetail objects."""
    issues = []
    for issue_data in issues_data:
        issue = IssueDetail(
            type=IssueType(issue_data.get("type", "style")),
            severity=IssueSeverity(issue_data.get("severity", "low")),
            line=issue_data.get("line", 1),
            description=issue_data.get("description", "No description"),
            suggestion=issue_data.get("suggestion", "No suggestion"),
            confidence=issue_data.get("confidence", 0.8),
        )
        issues.append(issue)
    return issues


def _convert_file_results(task_results, task_id: UUID) -> list[FileAnalysisResponse]:
    """Convert database results to FileAnalysisResponse objects."""
    file_results = []
    for result in task_results:
        issues = _convert_issues_to_details(result.issues, task_id)

        file_results.append(
            FileAnalysisResponse(
                name=result.file_name,
                path=result.file_path,
                language=result.language,
                size=result.file_size or 0,  # Ensure size is not None
                issues=issues,
            )
        )
    return file_results


def _convert_summary_to_response(task_summary) -> AnalysisSummaryResponse:
    """Convert database summary to AnalysisSummaryResponse."""
    if not task_summary:
        return None

    return AnalysisSummaryResponse(
        total_files=task_summary.total_files,
        total_issues=task_summary.total_issues,
        critical_issues=task_summary.critical_issues,
        high_issues=task_summary.high_issues,
        medium_issues=task_summary.medium_issues,
        low_issues=task_summary.low_issues,
        style_issues=task_summary.style_issues,
        bug_issues=task_summary.bug_issues,
        performance_issues=task_summary.performance_issues,
        security_issues=task_summary.security_issues,
        maintainability_issues=task_summary.maintainability_issues,
        best_practice_issues=task_summary.best_practice_issues,
        code_quality_score=task_summary.code_quality_score,
        maintainability_score=task_summary.maintainability_score,
    )


@router.get(
    "/status/{task_id}",
    response_model=TaskStatusResponse,
    summary="Get Task Status",
    description="Get the current status and progress of an analysis task.",
    responses={
        200: {"description": "Task status retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Task not found"},
    },
)
async def get_task_status(
    task_id: UUID, db_session: AsyncSession = Depends(get_db_session)
) -> TaskStatusResponse:
    """
    Get the current status and progress of an analysis task.

    Returns basic information about the task including status, progress,
    and timing information without the full analysis results.
    """
    try:
        # Find the task
        task = await db_session.get(AnalysisTask, task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        logger.debug(f"Retrieved status for task {task_id}: {task.status.value}")

        return TaskStatusResponse(
            task_id=task.id,
            status=task.status,
            progress=task.progress,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            error_message=task.error_message,
            retry_count=task.retry_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status for {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task status",
        ) from e


@router.get(
    "/results/{task_id}",
    response_model=AnalysisResponse,
    summary="Get Analysis Results",
    description="Get the complete analysis results for a completed task.",
    responses={
        200: {"description": "Analysis results retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        409: {"model": ErrorResponse, "description": "Analysis not completed yet"},
    },
)
async def get_analysis_results(
    task_id: UUID,
    db_session: AsyncSession = Depends(get_db_session),
) -> AnalysisResponse:
    """
    Get the complete analysis results for a completed task.

    Returns detailed analysis results including file-level analysis,
    issues found, and summary information.
    """
    try:
        # Find the task with all related data
        query = (
            select(AnalysisTask)
            .options(
                selectinload(AnalysisTask.results),
                selectinload(AnalysisTask.summary),
            )
            .where(AnalysisTask.id == task_id)
        )

        result = await db_session.execute(query)
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        # Check if analysis is completed
        if task.status.value not in ["completed", "failed"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Analysis is not completed yet. Current status: {task.status.value}",
            )

        logger.debug(
            f"Retrieved results for task {task_id} with {len(task.results)} files"
        )

        # Convert database results to response models
        file_results = _convert_file_results(task.results, task_id)
        summary_response = _convert_summary_to_response(task.summary)

        # Calculate total analysis duration
        analysis_duration = None
        if task.started_at and task.completed_at:
            analysis_duration = (task.completed_at - task.started_at).total_seconds()

        return AnalysisResponse(
            task_id=task.id,
            status=task.status,
            progress=task.progress,
            files=file_results,
            summary=summary_response,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            analysis_duration=analysis_duration,
            error_message=task.error_message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis results for {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analysis results",
        ) from e


@router.get(
    "/results/{task_id}/summary",
    response_model=AnalysisSummaryResponse,
    summary="Get Analysis Summary",
    description="Get just the summary information for an analysis task.",
    responses={
        200: {"description": "Analysis summary retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Task or summary not found"},
        409: {"model": ErrorResponse, "description": "Analysis not completed yet"},
    },
)
async def get_analysis_summary(
    task_id: UUID, db_session: AsyncSession = Depends(get_db_session)
) -> AnalysisSummaryResponse:
    """
    Get just the summary information for an analysis task.

    Returns high-level metrics and recommendations without detailed file analysis.
    """
    try:
        # Find the task and its summary
        query = (
            select(AnalysisTask)
            .options(selectinload(AnalysisTask.summary))
            .where(AnalysisTask.id == task_id)
        )

        result = await db_session.execute(query)
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        if not task.summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis summary not found",
            )

        # Check if analysis is completed
        if task.status.value not in ["completed", "failed"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Analysis is not completed yet. Current status: {task.status.value}",
            )

        logger.debug(f"Retrieved summary for task {task_id}")

        return _convert_summary_to_response(task.summary)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis summary for {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analysis summary",
        ) from e
