"""Integration tests for status API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


class TestStatusEndpoints:
    """Test status API endpoints."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "Ok!"
        assert data["service"] == "Code Reviewer Agent"
        assert "version" in data

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "version" in data
        assert "docs" in data
        assert "health" in data
        assert "api" in data
        assert data["docs"] == "/docs"
        assert data["health"] == "/health"
        assert data["api"] == "/api/v1"

    def test_openapi_docs(self, client):
        """Test OpenAPI documentation endpoint."""
        response = client.get("/docs")

        # Should return HTML page for Swagger UI
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc_docs(self, client):
        """Test ReDoc documentation endpoint."""
        response = client.get("/redoc")

        # Should return HTML page for ReDoc
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_openapi_json(self, client):
        """Test OpenAPI JSON schema endpoint."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()

        assert "openapi" in data
        assert "info" in data
        assert "paths" in data
        assert data["info"]["title"] == "Code Reviewer Agent"

    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        # Test preflight request
        response = client.options(
            "/api/v1/analyze-pr",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        # FastAPI should handle CORS preflight
        assert response.status_code in [200, 204]

    def test_nonexistent_endpoint(self, client):
        """Test accessing non-existent endpoint."""
        response = client.get("/api/v1/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_method_not_allowed(self, client):
        """Test method not allowed error."""
        # POST to a GET-only endpoint
        response = client.post("/health")

        assert response.status_code == 405
        data = response.json()
        assert "detail" in data


class TestErrorHandling:
    """Test API error handling."""

    def test_validation_error_response(self, client):
        """Test Pydantic validation error response."""
        # Send invalid data to trigger validation error
        invalid_data = {
            "repo_url": "invalid-url",  # Invalid URL format
            "pr_number": "not-a-number",  # Invalid type
        }

        response = client.post("/api/v1/analyze-pr", json=invalid_data)

        assert response.status_code == 422
        data = response.json()

        assert "detail" in data
        assert isinstance(data["detail"], list)
        # Should contain validation errors
        assert len(data["detail"]) > 0

    def test_json_parse_error(self, client):
        """Test malformed JSON error handling."""
        response = client.post(
            "/api/v1/analyze-pr",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_missing_content_type(self, client):
        """Test missing content type error."""
        # Test with malformed data and no content-type - should get validation error
        response = client.post(
            "/api/v1/analyze-pr",
            data='invalid json data',  # Invalid JSON
        )

        # FastAPI should return 422 for malformed JSON
        assert response.status_code == 422

    def test_large_request_body(self, client):
        """Test handling of large request bodies."""
        # Test with invalid data that would trigger validation before DB operations
        large_data = {
            "repo_url": "not-a-valid-url",  # Invalid URL format
            "pr_number": -1,  # Invalid PR number
            "github_token": "x" * 10000,  # Very long token
        }

        response = client.post("/api/v1/analyze-pr", json=large_data)

        # Should get validation error before hitting database
        assert response.status_code == 422

    def test_concurrent_requests(self, client):
        """Test handling of concurrent requests."""
        import concurrent.futures

        def make_request():
            return client.get("/health")

        # Make multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [future.result() for future in futures]

        # All should succeed
        for response in responses:
            assert response.status_code == 200


class TestContentNegotiation:
    """Test content negotiation and response formats."""

    def test_json_response_format(self, client):
        """Test JSON response format."""
        response = client.get("/health")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

        # Verify it's valid JSON
        data = response.json()
        assert isinstance(data, dict)

    def test_accept_header_handling(self, client):
        """Test Accept header handling."""
        # Request JSON explicitly
        response = client.get("/health", headers={"Accept": "application/json"})

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_unsupported_media_type(self, client):
        """Test unsupported media type request."""
        response = client.post(
            "/api/v1/analyze-pr",
            data="repo_url=test&pr_number=1",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # FastAPI should handle this appropriately
        assert response.status_code in [422, 415]


class TestRateLimiting:
    """Test rate limiting behavior (if implemented)."""

    def test_rate_limiting_basic(self, client):
        """Basic test for rate limiting behavior."""
        # This is a placeholder test - actual rate limiting would need configuration

        # Make multiple requests quickly
        responses = []
        for _ in range(10):
            response = client.get("/health")
            responses.append(response)

        # Without rate limiting, all should succeed
        for response in responses:
            assert response.status_code == 200