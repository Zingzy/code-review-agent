"""
Celery Tasks for Code Analysis

Contains async tasks for processing GitHub PR analysis with real GitHub integration.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List
from uuid import UUID
import concurrent.futures
import os

from app.tasks.celery_app import celery
from app.services.github import GitHubService
from app.utils.language_detection import LanguageDetector
from app.config.database import get_database_manager
from app.agents.analyzer import LangGraphAnalyzer
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
                )
                session.add(analysis_result)

            # Create task summary with fallbacks from breakdowns
            summary_in = analysis_results.get("summary", {}) or {}
            sev = summary_in.get("severity_breakdown", {}) or {}
            typ = summary_in.get("issue_type_breakdown", {}) or {}

            summary = AnalysisSummary(
                task_id=task_id,
                total_files=summary_in.get(
                    "total_files", summary_in.get("total_files_analyzed", 0)
                ),
                total_issues=summary_in.get("total_issues", 0),
                critical_issues=summary_in.get(
                    "critical_issues", sev.get("critical", 0)
                ),
                high_issues=summary_in.get("high_issues", sev.get("high", 0)),
                medium_issues=summary_in.get("medium_issues", sev.get("medium", 0)),
                low_issues=summary_in.get("low_issues", sev.get("low", 0)),
                style_issues=summary_in.get("style_issues", typ.get("quality", 0)),
                bug_issues=summary_in.get("bug_issues", typ.get("security", 0)),
                performance_issues=summary_in.get(
                    "performance_issues", typ.get("performance", 0)
                ),
                security_issues=summary_in.get(
                    "security_issues", typ.get("security", 0)
                ),
                maintainability_issues=summary_in.get(
                    "maintainability_issues", typ.get("maintainability", 0)
                ),
                best_practice_issues=summary_in.get("best_practice_issues", 0),
                code_quality_score=summary_in.get(
                    "code_quality_score", summary_in.get("overall_score", 0.0)
                ),
                maintainability_score=summary_in.get("maintainability_score", 0.0),
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

        # Initialize services
        github_service = GitHubService(github_token)
        language_detector = LanguageDetector()
        # Initialize LangGraph analyzer
        langgraph_analyzer = LangGraphAnalyzer()

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

        # Collect file contents for AI analysis
        files_for_analysis = []
        analyzed_count = 0

        logger.info(f"Processing {file_count} files for analysis")

        for i, file_info in enumerate(files):
            file_path = file_info["filename"]

            logger.debug(f"Processing file {i + 1}/{file_count}: {file_path}")

            # Update progress
            progress = 30 + (i / file_count) * 50  # 30-80% for file collection
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": int(progress),
                    "total": 100,
                    "status": f"Processing {file_path}...",
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

                # Get file content
                try:
                    file_content_data = github_service.get_file_content(
                        repo_url, file_path, pr_metadata["head"]["sha"]
                    )

                    # Extract the actual text content from the response
                    file_content = (
                        file_content_data.get("content", "")
                        if isinstance(file_content_data, dict)
                        else str(file_content_data)
                    )

                    # Skip binary files
                    if not file_content_data.get("is_text", True):
                        logger.info(f"Skipping binary file: {file_path}")
                        continue

                    # Try to detect language from content if still unknown
                    if language == "unknown" and file_content:
                        language = language_detector.detect_language_from_content(
                            file_content
                        )

                except Exception as e:
                    logger.warning(f"Could not fetch content for {file_path}: {e}")
                    file_content = ""
                    # Skip files we can't read
                    continue

                # Add to analysis list
                files_for_analysis.append(
                    {
                        "filename": file_path,
                        "language": language,
                        "content": file_content,
                        "additions": file_info.get("additions", 0),
                        "deletions": file_info.get("deletions", 0),
                        "changes": file_info.get("changes", 0),
                    }
                )
                analyzed_count += 1

            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")

        # Run LangGraph analysis
        run_async_in_celery(
            update_task_status(
                task_uuid, TaskStatus.PROCESSING, 80.0, "Running AI analysis..."
            )
        )

        self.update_state(
            state="PROGRESS",
            meta={
                "current": 85,
                "total": 100,
                "status": "Running AI analysis...",
                "task_id": task_id,
            },
        )

        try:
            analysis_results = run_async_in_celery(
                langgraph_analyzer.analyze_pr(pr_metadata, files_for_analysis)
            )

            # Check if the analysis returned an error result
            if analysis_results.get("status") == "failed":
                error_msg = (
                    f"Analysis failed: {analysis_results.get('error', 'Unknown error')}"
                )
                logger.error(f"Intelligent analysis returned error result: {error_msg}")

                # Mark task as failed with proper error message
                run_async_in_celery(
                    update_task_status(task_uuid, TaskStatus.FAILED, 0.0, error_msg)
                )
                return {"error": error_msg, "task_id": task_id}
            else:
                logger.info("Intelligent analysis completed successfully")

        except Exception as e:
            error_msg = f"Analysis engine failed: {str(e)}"
            logger.error(f"LangGraph analysis failed: {e}", exc_info=True)

            # Mark task as failed with proper error message
            run_async_in_celery(
                update_task_status(task_uuid, TaskStatus.FAILED, 0.0, error_msg)
            )
            return {"error": error_msg, "task_id": task_id}

        # Update progress after analysis
        run_async_in_celery(
            update_task_status(
                task_uuid, TaskStatus.PROCESSING, 90.0, "Saving results..."
            )
        )

        # Extract summary from analysis results
        summary = analysis_results.get("summary", {})
        summary["total_files"] = file_count
        summary["files_analyzed"] = analyzed_count

        # Save results to database
        database_results = adapt_analysis_results_for_database(
            analysis_results, files_for_analysis
        )
        run_async_in_celery(
            save_analysis_results(task_uuid, database_results, pr_metadata)
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
            "summary": summary,
            "files_analyzed": analyzed_count,
            "analysis_type": analysis_results.get(
                "analysis_type", "langgraph_analysis"
            ),
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


# Removed misleading generate_basic_analysis function
# When analysis fails, we now properly mark the task as failed
# instead of generating fake analysis results


def adapt_analysis_results_for_database(
    analysis_results: Dict[str, Any], files_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Adapt analysis results from the intelligent workflow to the database format.

    Args:
        analysis_results: Results from the intelligent workflow.
        files_data: Original files data (not used in this adapter but kept for signature consistency).

    Returns:
        A dictionary with 'files' and 'summary' keys, formatted for database saving.
    """
    # The new workflow already returns data in a compatible format.
    # This function now primarily acts as a pass-through and validation step.
    return {
        "files": analysis_results.get("files", {}),
        "summary": analysis_results.get("summary", {}),
    }
