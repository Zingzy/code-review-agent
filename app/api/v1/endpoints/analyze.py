"""
PR Analysis API Endpoints

Handles pull request analysis requests and task management.
"""

from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db_session
from app.models.schemas import (
    AnalysisRequest,
    TaskResponse,
    TaskCancelRequest,
    ErrorResponse,
)
from app.models.database import AnalysisTask, TaskStatus
from app.tasks.analyze_tasks import analyze_pr_task
from app.tasks.celery_app import celery
from app.utils.logger import logger

router = APIRouter()


@router.post(
    "/analyze-pr",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit PR for Analysis",
    description="Submit a GitHub pull request for analysis. Returns a task ID for tracking progress.",
    responses={
        202: {"description": "Analysis task queued successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request data"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def submit_pr_analysis(
    request: AnalysisRequest, db_session: AsyncSession = Depends(get_db_session)
) -> TaskResponse:
    """
    Submit a GitHub pull request for analysis.

    This endpoint queues an analysis task and returns a task ID that can be used
    to track the progress and retrieve results.
    """
    try:
        logger.info(
            f"Received analysis request for {request.repo_url} PR #{request.pr_number}"
        )

        # Create a new analysis task record
        task = AnalysisTask(
            repo_url=request.repo_url,
            pr_number=request.pr_number,
            github_token=request.github_token,
            status=TaskStatus.PENDING,
            progress=0.0,
        )

        # Save task to database
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        # Submit task to Celery
        celery_task = analyze_pr_task.delay(
            str(task.id),  # Pass the database task ID
            request.repo_url,
            request.pr_number,
            request.github_token,
        )

        # Update task with Celery task ID
        task.celery_task_id = celery_task.id
        await db_session.commit()

        logger.info(
            f"Task {task.id} queued successfully with Celery ID {celery_task.id}"
        )

        return TaskResponse(
            task_id=task.id,
            status=TaskStatus.PENDING,
            message="Analysis task queued successfully",
        )

    except Exception as e:
        logger.error(f"Failed to submit analysis request: {e}")
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit analysis request",
        ) from e


@router.delete(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Cancel Analysis Task",
    description="Cancel a running or pending analysis task.",
    responses={
        200: {"description": "Task cancelled successfully"},
        404: {"model": ErrorResponse, "description": "Task not found"},
        409: {"model": ErrorResponse, "description": "Task cannot be cancelled"},
    },
)
async def cancel_analysis_task(
    task_id: UUID,
    request: TaskCancelRequest,
    db_session: AsyncSession = Depends(get_db_session),
) -> TaskResponse:
    """
    Cancel a running or pending analysis task.

    Only tasks in PENDING or PROCESSING status can be cancelled.
    """
    try:
        # Find the task
        task = await db_session.get(AnalysisTask, task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        # Check if task can be cancelled
        if task.status not in [TaskStatus.PENDING, TaskStatus.PROCESSING]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot cancel task in {task.status.value} status",
            )

        # Cancel the Celery task if it exists
        if task.celery_task_id:
            celery.control.revoke(task.celery_task_id, terminate=True)
            logger.info(f"Cancelled Celery task {task.celery_task_id}")

        # Update task status
        task.status = TaskStatus.CANCELLED
        task.error_message = request.reason or "Task cancelled by user"
        await db_session.commit()

        logger.info(f"Task {task_id} cancelled successfully")

        return TaskResponse(
            task_id=task.id,
            status=TaskStatus.CANCELLED,
            message="Task cancelled successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel task",
        ) from e


@router.get(
    "/tasks",
    response_model=Dict[str, Any],
    summary="List Analysis Tasks",
    description="List recent analysis tasks with optional filtering.",
)
async def list_analysis_tasks(
    limit: int = 20,
    offset: int = 0,
    status_filter: str = None,
    db_session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    List recent analysis tasks with pagination and optional status filtering.
    """
    try:
        # Build query with optional filtering
        query = select(AnalysisTask)
        if status_filter:
            try:
                status_enum = TaskStatus(status_filter.lower())
                query = query.where(AnalysisTask.status == status_enum)
            except ValueError as ve:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status filter: {status_filter}",
                ) from ve

        # Add pagination and ordering
        query = (
            query.order_by(AnalysisTask.created_at.desc()).limit(limit).offset(offset)
        )

        # Get total count
        count_query = select(func.count(AnalysisTask.id))
        if status_filter:
            status_enum = TaskStatus(status_filter.lower())
            count_query = count_query.where(AnalysisTask.status == status_enum)

        # Execute queries
        result = await db_session.execute(query)
        tasks = result.scalars().all()

        count_result = await db_session.execute(count_query)
        total_count = count_result.scalar()

        # Format response
        task_list = []
        for task in tasks:
            task_list.append(
                {
                    "task_id": task.id,
                    "repo_url": task.repo_url,
                    "pr_number": task.pr_number,
                    "status": task.status.value,
                    "progress": task.progress,
                    "created_at": task.created_at.isoformat(),
                    "started_at": task.started_at.isoformat()
                    if task.started_at
                    else None,
                    "completed_at": task.completed_at.isoformat()
                    if task.completed_at
                    else None,
                }
            )

        return {
            "tasks": task_list,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(tasks) < total_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tasks",
        ) from e
