"""
Celery Tasks for Code Analysis

Contains async tasks for processing GitHub PR analysis with real GitHub integration.
Uses proper asyncio event loop handling for Celery workers.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any
from uuid import UUID
import concurrent.futures
import os

from app.tasks.celery_app import celery
from app.services.github import GitHubService
from app.utils.language_detection import LanguageDetector
from app.config.database import get_database_manager
from app.models.database import (
    AnalysisTask,
    AnalysisResult,
    AnalysisSummary,
    TaskStatus,
)
from app.utils.logger import logger
from app.utils.exceptions import (
    GitHubAPIException,
    InvalidRepositoryException,
    RateLimitExceededException,
)


def run_async_in_celery(coro):
    """
    Helper to properly run async code in Celery workers.

    Celery workers may or may not have an event loop, so we need to handle both cases.
    """
    try:
        # Try to get the current loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, we need a new thread

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            # Loop exists but not running, we can use it
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(coro)


async def update_task_status(
    task_id: UUID, status: TaskStatus, progress: float, message: str = None
) -> None:
    """
    Update task status in database using proper async SQLModel operations.

    Args:
        task_id: Task UUID
        status: New task status
        progress: Progress percentage
        message: Optional status message
    """
    try:
        db_manager = get_database_manager()
        if not db_manager._initialized:
            db_manager.initialize()

        async with db_manager.get_session() as session:
            task = await session.get(AnalysisTask, task_id)
            if task:
                task.status = status
                task.progress = progress

                # Handle datetime fields properly (using naive datetimes)
                now = datetime.now()  # This creates a naive datetime

                if status == TaskStatus.PROCESSING and not task.started_at:
                    task.started_at = now
                elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    task.completed_at = now

                if message:
                    task.error_message = (
                        message if status == TaskStatus.FAILED else None
                    )

                await session.commit()
                logger.debug(f"Updated task {task_id} status to {status}")
            else:
                logger.warning(f"Task {task_id} not found for status update")

    except Exception as e:
        logger.error(f"Failed to update task status: {e}")


async def save_analysis_results(
    task_id: UUID, analysis_results: Dict[str, Any], pr_metadata: Dict[str, Any]
) -> None:
    """
    Save analysis results to database using proper async SQLModel operations.

    Args:
        task_id: Task UUID
        analysis_results: Analysis results data
        pr_metadata: Pull request metadata
    """
    try:
        db_manager = get_database_manager()
        if not db_manager._initialized:
            db_manager.initialize()

        async with db_manager.get_session() as session:
            # Create analysis results for each file
            for file_path, file_analysis in analysis_results.get("files", {}).items():
                file_name = os.path.basename(file_path)

                analysis_result = AnalysisResult(
                    task_id=task_id,
                    file_name=file_name,
                    file_path=file_path,
                    language=file_analysis.get("language", "unknown"),
                    issues=file_analysis.get("issues", []),
                    metrics=file_analysis.get("metrics", {}),
                    suggestions=file_analysis.get("suggestions", []),
                )
                session.add(analysis_result)

            # Create task summary
            summary = AnalysisSummary(
                task_id=task_id,
                total_files=analysis_results.get("summary", {}).get("total_files", 0),
                total_issues=analysis_results.get("summary", {}).get("total_issues", 0),
                critical_issues=analysis_results.get("summary", {}).get(
                    "critical_issues", 0
                ),
                high_issues=analysis_results.get("summary", {}).get("high_issues", 0),
                medium_issues=analysis_results.get("summary", {}).get(
                    "medium_issues", 0
                ),
                low_issues=analysis_results.get("summary", {}).get("low_issues", 0),
                style_issues=analysis_results.get("summary", {}).get("style_issues", 0),
                bug_issues=analysis_results.get("summary", {}).get("bug_issues", 0),
                performance_issues=analysis_results.get("summary", {}).get(
                    "performance_issues", 0
                ),
                security_issues=analysis_results.get("summary", {}).get(
                    "security_issues", 0
                ),
                maintainability_issues=analysis_results.get("summary", {}).get(
                    "maintainability_issues", 0
                ),
                best_practice_issues=analysis_results.get("summary", {}).get(
                    "best_practice_issues", 0
                ),
                code_quality_score=analysis_results.get("summary", {}).get(
                    "code_quality_score", 0.0
                ),
                maintainability_score=analysis_results.get("summary", {}).get(
                    "maintainability_score", 0.0
                ),
                overall_recommendations=analysis_results.get("summary", {}).get(
                    "overall_recommendations", []
                ),
            )
            session.add(summary)

            await session.commit()
            logger.info(f"Saved analysis results for task {task_id}")

    except Exception as e:
        logger.error(f"Failed to save analysis results: {e}")
        raise


@celery.task(bind=True)
def analyze_pr_task(
    self, task_id: str, repo_url: str, pr_number: int, github_token: str = None
):
    """
    Analyze a GitHub Pull Request asynchronously.

    Args:
        task_id: Database task ID (UUID as string)
        repo_url: GitHub repository URL
        pr_number: Pull request number
        github_token: Optional GitHub token for private repos

    Returns:
        dict: Analysis results
    """
    task_uuid = UUID(task_id)

    try:
        logger.info(f"Starting analysis for PR #{pr_number} from {repo_url}")

        # Update task status to processing
        run_async_in_celery(
            update_task_status(
                task_uuid, TaskStatus.PROCESSING, 0.0, "Starting analysis..."
            )
        )

        # Initialize GitHub service
        github_service = GitHubService(github_token)

        # Fetch PR metadata
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 10,
                "total": 100,
                "status": "Fetching PR metadata...",
                "task_id": task_id,
            },
        )

        pr_metadata = github_service.get_pull_request_metadata(repo_url, pr_number)
        run_async_in_celery(
            update_task_status(
                task_uuid, TaskStatus.PROCESSING, 10.0, "PR metadata fetched"
            )
        )

        logger.info(f"Fetched metadata for PR: '{pr_metadata['title']}'")

        # Check if PR is analyzable
        if pr_metadata["state"] not in ["open", "closed"]:
            run_async_in_celery(
                update_task_status(
                    task_uuid,
                    TaskStatus.FAILED,
                    0.0,
                    f"PR is in '{pr_metadata['state']}' state",
                )
            )
            return {"error": f"PR is in '{pr_metadata['state']}' state"}

        # Fetch PR files
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 30,
                "total": 100,
                "status": "Fetching changed files...",
                "task_id": task_id,
            },
        )

        pr_files_data = github_service.get_pull_request_files(repo_url, pr_number)
        files = pr_files_data["files"]
        file_count = len(files)

        run_async_in_celery(
            update_task_status(
                task_uuid,
                TaskStatus.PROCESSING,
                30.0,
                f"Found {file_count} files to analyze",
            )
        )

        logger.info(f"Found {file_count} files to analyze")

        if file_count == 0:
            run_async_in_celery(
                update_task_status(
                    task_uuid, TaskStatus.COMPLETED, 100.0, "No files to analyze"
                )
            )
            return {"message": "No files to analyze", "files": []}

        # Initialize language detector
        language_detector = LanguageDetector()

        # Analyze each file
        analysis_results = {"files": {}, "summary": {"total_files": file_count}}
        analyzed_count = 0

        for i, file_info in enumerate(files):
            file_path = file_info["filename"]

            # Update progress
            progress = 30 + (i / file_count) * 60  # 30-90% for file analysis
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": int(progress),
                    "total": 100,
                    "status": f"Analyzing {file_path}...",
                    "task_id": task_id,
                },
            )

            try:
                # Skip very large files or binary files
                if file_info.get("additions", 0) + file_info.get("deletions", 0) > 1000:
                    logger.info(f"Skipping large file: {file_path}")
                    continue

                # Detect language
                language = language_detector.detect_language_from_filename(file_path)
                if language == "unknown":
                    # Try to detect from content if available
                    try:
                        file_content = github_service.get_file_content(
                            repo_url, file_path, pr_metadata["head"]["sha"]
                        )
                        language = language_detector.detect_language_from_content(
                            file_content
                        )
                    except Exception as e:
                        logger.warning(f"Could not fetch content for {file_path}: {e}")
                        file_content = ""

                # Analyze file (placeholder implementation)
                file_analysis = analyze_single_file(
                    file_path,
                    file_info,
                    language,
                    file_content if "file_content" in locals() else "",
                )
                analysis_results["files"][file_path] = file_analysis
                analyzed_count += 1

            except Exception as e:
                logger.error(f"Error analyzing file {file_path}: {e}")
                analysis_results["files"][file_path] = {
                    "language": "unknown",
                    "issues": [],
                    "metrics": {},
                    "suggestions": [],
                    "error": str(e),
                }

        # Update progress after file analysis
        run_async_in_celery(
            update_task_status(
                task_uuid, TaskStatus.PROCESSING, 90.0, "Generating summary..."
            )
        )

        # Generate summary
        summary = generate_analysis_summary(analysis_results["files"])
        analysis_results["summary"].update(summary)
        analysis_results["summary"]["files_analyzed"] = analyzed_count

        # Save results to database
        run_async_in_celery(
            save_analysis_results(task_uuid, analysis_results, pr_metadata)
        )

        # Mark task as completed
        run_async_in_celery(
            update_task_status(
                task_uuid, TaskStatus.COMPLETED, 100.0, "Analysis completed"
            )
        )

        logger.info(f"Analysis completed for PR #{pr_number}")
        return {
            "task_id": task_id,
            "status": "completed",
            "summary": analysis_results["summary"],
            "files_analyzed": analyzed_count,
        }

    except (
        GitHubAPIException,
        InvalidRepositoryException,
        RateLimitExceededException,
    ) as e:
        # Handle known exceptions
        error_msg = f"GitHub API error: {str(e)}"
        logger.error(error_msg)

        run_async_in_celery(
            update_task_status(task_uuid, TaskStatus.FAILED, 0.0, error_msg)
        )

        return {"error": error_msg, "task_id": task_id}

    except Exception as exc:
        # Handle unexpected exceptions
        error_msg = f"Unexpected error during analysis: {str(exc)}"
        logger.error(error_msg, exc_info=True)

        run_async_in_celery(
            update_task_status(task_uuid, TaskStatus.FAILED, 0.0, error_msg)
        )

        raise exc  # Re-raise for Celery to handle


def analyze_single_file(
    file_path: str, file_info: Dict[str, Any], language: str, content: str = ""
) -> Dict[str, Any]:
    """
    Analyze a single file (placeholder implementation).

    Args:
        file_path: Path to the file
        file_info: File information from GitHub
        language: Detected language
        content: File content (optional)

    Returns:
        dict: Analysis results for the file
    """
    # Placeholder implementation
    # In a real implementation, this would use AI/static analysis tools

    issues = []
    metrics = {
        "lines_added": file_info.get("additions", 0),
        "lines_removed": file_info.get("deletions", 0),
        "changes": file_info.get("changes", 0),
    }
    suggestions = []

    # Simple heuristic-based analysis
    if language in ["python", "javascript", "typescript"]:
        # Check for large files
        if metrics["lines_added"] > 100:
            issues.append(
                {
                    "type": "maintainability",
                    "severity": "medium",
                    "line": 1,
                    "message": "Large file changes detected. Consider breaking into smaller commits.",
                    "description": f"This file has {metrics['lines_added']} lines added, which is quite large for a single change.",
                }
            )

        # Check for potential security issues (very basic)
        if content and any(
            keyword in content.lower()
            for keyword in ["password", "secret", "key", "token"]
        ):
            issues.append(
                {
                    "type": "security",
                    "severity": "high",
                    "line": 1,
                    "message": "Potential hardcoded secrets detected",
                    "description": "This file contains keywords that might indicate hardcoded secrets.",
                }
            )

    return {
        "language": language,
        "issues": issues,
        "metrics": metrics,
        "suggestions": suggestions,
    }


def generate_analysis_summary(files_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate summary statistics from file analysis results.

    Args:
        files_analysis: Dictionary of file analysis results

    Returns:
        dict: Summary statistics
    """
    total_issues = 0
    issues_by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for file_analysis in files_analysis.values():
        file_issues = file_analysis.get("issues", [])
        total_issues += len(file_issues)

        for issue in file_issues:
            severity = issue.get("severity", "low")
            if severity in issues_by_severity:
                issues_by_severity[severity] += 1

    return {
        "total_issues": total_issues,
        "critical_issues": issues_by_severity["critical"],
        "high_issues": issues_by_severity["high"],
        "medium_issues": issues_by_severity["medium"],
        "low_issues": issues_by_severity["low"],
    }
