"""Integration tests for analysis API endpoints."""

import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.database import TaskStatus
from tests.fixtures import (
    create_test_task,
)


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


class TestAnalysisEndpoints:
    """Test analysis API endpoints."""

    def test_submit_pr_analysis_success(
        self, client, test_db_session, create_test_tables, mock_github_service
    ):
        """Test successful PR analysis submission."""
        with patch("app.api.v1.endpoints.analyze.get_db_session") as mock_get_db:
            mock_get_db.return_value = test_db_session

            with patch(
                "app.api.v1.endpoints.analyze.analyze_pr_task.delay"
            ) as mock_task:
                mock_task.return_value.id = "test-celery-id"

                request_data = {
                    "repo_url": "https://github.com/testorg/testrepo",
                    "pr_number": 42,
                    "github_token": "github_pat_test_token",
                }

                response = client.post("/api/v1/analyze-pr", json=request_data)

                assert response.status_code == 202
                data = response.json()

                assert "task_id" in data
                assert data["status"] == "pending"
                assert data["message"] == "Analysis task queued successfully"

                # Verify task was queued
                mock_task.assert_called_once()

    def test_submit_pr_analysis_invalid_url(self, client):
        """Test PR analysis submission with invalid URL."""
        request_data = {"repo_url": "invalid-url", "pr_number": 42}

        response = client.post("/api/v1/analyze-pr", json=request_data)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_submit_pr_analysis_invalid_pr_number(self, client):
        """Test PR analysis submission with invalid PR number."""
        request_data = {
            "repo_url": "https://github.com/testorg/testrepo",
            "pr_number": 0,  # Invalid: should be > 0
        }

        response = client.post("/api/v1/analyze-pr", json=request_data)

        assert response.status_code == 422

    def test_submit_pr_analysis_without_token(self, client, test_db_session, create_test_tables):
        """Test PR analysis submission without GitHub token."""
        with patch("app.api.v1.endpoints.analyze.get_db_session") as mock_get_db:
            mock_get_db.return_value = test_db_session

            with patch(
                "app.api.v1.endpoints.analyze.analyze_pr_task.delay"
            ) as mock_task:
                mock_task.return_value.id = "test-celery-id"

                request_data = {
                    "repo_url": "https://github.com/testorg/testrepo",
                    "pr_number": 42,
                    # No github_token provided
                }

                response = client.post("/api/v1/analyze-pr", json=request_data)

                assert response.status_code == 202
                data = response.json()

                assert "task_id" in data
                assert data["status"] == "pending"

    def test_cancel_analysis_task_success(self, client, test_db_session, create_test_tables):
        """Test successful task cancellation."""
        # Create a test task
        task = create_test_task(status=TaskStatus.PROCESSING)
        task.celery_task_id = "test-celery-id"

        with patch("app.api.v1.endpoints.analyze.get_db_session") as mock_get_db:
            mock_get_db.return_value = test_db_session

            with patch(
                "app.api.v1.endpoints.analyze.celery.control.revoke"
            ) as mock_revoke:
                # Mock the database session get method
                test_db_session.get = AsyncMock(return_value=task)
                test_db_session.commit = AsyncMock()

                request_data = {"reason": "User requested cancellation"}

                response = client.request(
                    "DELETE",
                    f"/api/v1/tasks/{task.id}",
                    json=request_data
                )

                assert response.status_code == 200
                data = response.json()

                assert str(data["task_id"]) == str(task.id)
                assert data["status"] == "cancelled"
                assert data["message"] == "Task cancelled successfully"

                # Verify Celery task was revoked
                mock_revoke.assert_called_once_with("test-celery-id", terminate=True)

    def test_cancel_analysis_task_not_found(self, client, test_db_session, create_test_tables):
        """Test cancelling non-existent task."""
        task_id = uuid4()

        with patch("app.api.v1.endpoints.analyze.get_db_session") as mock_get_db:
            mock_get_db.return_value = test_db_session

            # Mock the database session to return None (task not found)
            test_db_session.get = AsyncMock(return_value=None)

            request_data = {"reason": "Test cancellation"}

            response = client.request(
                "DELETE",
                f"/api/v1/tasks/{task_id}",
                json=request_data
            )

            assert response.status_code == 404
            data = response.json()
            assert data["detail"] == "Task not found"

    def test_cancel_analysis_task_already_completed(self, client, test_db_session, create_test_tables):
        """Test cancelling already completed task."""
        # Create a completed test task
        task = create_test_task(status=TaskStatus.COMPLETED)

        with patch("app.api.v1.endpoints.analyze.get_db_session") as mock_get_db:
            mock_get_db.return_value = test_db_session

            test_db_session.get = AsyncMock(return_value=task)

            request_data = {"reason": "Test cancellation"}

            response = client.request(
                "DELETE",
                f"/api/v1/tasks/{task.id}",
                json=request_data
            )

            assert response.status_code == 409
            data = response.json()
            assert "Cannot cancel task in completed status" in data["detail"]

    def test_list_analysis_tasks_success(self, client, test_db_session, create_test_tables):
        """Test successful tasks listing."""
        with patch("app.api.v1.endpoints.analyze.get_db_session") as mock_get_db:
            mock_get_db.return_value = test_db_session

            # Mock database query results
            mock_execute = AsyncMock()
            mock_scalars = AsyncMock()
            mock_scalars.all.return_value = [
                create_test_task(
                    repo_url="https://github.com/test1/repo1", pr_number=1
                ),
                create_test_task(
                    repo_url="https://github.com/test2/repo2", pr_number=2
                ),
            ]
            mock_execute.scalars.return_value = mock_scalars

            # Mock count query
            mock_count_result = AsyncMock()
            mock_count_result.scalar.return_value = 2

            test_db_session.execute = AsyncMock(
                side_effect=[mock_execute, mock_count_result]
            )

            response = client.get("/api/v1/tasks")

            assert response.status_code == 200
            data = response.json()

            assert "tasks" in data
            assert len(data["tasks"]) == 2
            assert data["total_count"] == 2
            assert data["limit"] == 20
            assert data["offset"] == 0
            assert data["has_more"] is False

    def test_list_analysis_tasks_with_pagination(self, client, test_db_session, create_test_tables):
        """Test tasks listing with pagination."""
        with patch("app.api.v1.endpoints.analyze.get_db_session") as mock_get_db:
            mock_get_db.return_value = test_db_session

            # Mock database query results
            mock_execute = AsyncMock()
            mock_scalars = AsyncMock()
            mock_scalars.all.return_value = [
                create_test_task(
                    repo_url="https://github.com/test1/repo1", pr_number=1
                ),
            ]
            mock_execute.scalars.return_value = mock_scalars

            # Mock count query
            mock_count_result = AsyncMock()
            mock_count_result.scalar.return_value = 10  # Total count

            test_db_session.execute = AsyncMock(
                side_effect=[mock_execute, mock_count_result]
            )

            response = client.get("/api/v1/tasks?limit=5&offset=5")

            assert response.status_code == 200
            data = response.json()

            assert data["limit"] == 5
            assert data["offset"] == 5
            assert data["total_count"] == 10
            assert data["has_more"] is True

    def test_list_analysis_tasks_with_status_filter(self, client, test_db_session, create_test_tables):
        """Test tasks listing with status filter."""
        with patch("app.api.v1.endpoints.analyze.get_db_session") as mock_get_db:
            mock_get_db.return_value = test_db_session

            # Mock database query results
            mock_execute = AsyncMock()
            mock_scalars = AsyncMock()
            mock_scalars.all.return_value = [
                create_test_task(status=TaskStatus.COMPLETED),
            ]
            mock_execute.scalars.return_value = mock_scalars

            # Mock count query
            mock_count_result = AsyncMock()
            mock_count_result.scalar.return_value = 1

            test_db_session.execute = AsyncMock(
                side_effect=[mock_execute, mock_count_result]
            )

            response = client.get("/api/v1/tasks?status_filter=completed")

            assert response.status_code == 200
            data = response.json()

            assert len(data["tasks"]) == 1

    def test_list_analysis_tasks_invalid_status_filter(self, client):
        """Test tasks listing with invalid status filter."""
        response = client.get("/api/v1/tasks?status_filter=invalid_status")

        assert response.status_code == 400
        data = response.json()
        assert "Invalid status filter" in data["detail"]

    def test_database_error_handling(self, client):
        """Test database error handling."""
        with patch("app.api.v1.endpoints.analyze.get_db_session") as mock_get_db:
            # Simulate database connection error
            mock_get_db.side_effect = Exception("Database connection failed")

            request_data = {
                "repo_url": "https://github.com/testorg/testrepo",
                "pr_number": 42,
            }

            response = client.post("/api/v1/analyze-pr", json=request_data)

            assert response.status_code == 500
            data = response.json()
            assert "Failed to submit analysis request" in data["detail"]

    def test_concurrent_task_submission(self, client, test_db_session, create_test_tables):
        """Test handling of concurrent task submissions."""
        with patch("app.api.v1.endpoints.analyze.get_db_session") as mock_get_db:
            mock_get_db.return_value = test_db_session

            with patch(
                "app.api.v1.endpoints.analyze.analyze_pr_task.delay"
            ) as mock_task:
                mock_task.return_value.id = "test-celery-id"

                request_data = {
                    "repo_url": "https://github.com/testorg/testrepo",
                    "pr_number": 42,
                }

                # Submit multiple requests
                responses = []
                for _ in range(3):
                    response = client.post("/api/v1/analyze-pr", json=request_data)
                    responses.append(response)

                # All should succeed
                for response in responses:
                    assert response.status_code == 202
                    data = response.json()
                    assert "task_id" in data

                # Verify all tasks were queued
                assert mock_task.call_count == 3
