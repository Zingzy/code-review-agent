"""Tests for GitHub service."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.services.github import GitHubService
from app.utils.exceptions import (
    GitHubAPIException,
    InvalidRepositoryException,
)


class TestGitHubService:
    """Test GitHubService class."""

    def test_init_with_token(self):
        """Test GitHub service initialization with token."""
        service = GitHubService("test_token")
        assert service._token == "test_token"
        assert service.is_authenticated is True

    def test_init_without_token(self):
        """Test GitHub service initialization without token."""
        service = GitHubService()
        assert service._token is None or service._token == ""
        # Should still work but with rate limits

    @patch.dict("os.environ", {"GITHUB_TOKEN": "env_token"})
    def test_init_with_env_token(self):
        """Test GitHub service initialization with environment token."""
        service = GitHubService()
        assert service._token == "env_token"

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://github.com/owner/repo", ("owner", "repo")),
            ("https://github.com/owner/repo/", ("owner", "repo")),
            ("https://github.com/user-name/repo_name", ("user-name", "repo_name")),
            ("git@github.com:owner/repo.git", ("owner", "repo")),
            ("owner/repo", ("owner", "repo")),
        ],
    )
    def test_parse_repo_url_valid(self, url, expected):
        """Test parsing valid repository URLs."""
        service = GitHubService()
        result = service._parse_repo_url(url)
        assert result == expected

    @pytest.mark.parametrize(
        "url",
        [
            "not-a-url",
            "https://gitlab.com/owner/repo",
            "https://github.com/",
            "https://github.com/owner",
            "",
        ],
    )
    def test_parse_repo_url_invalid(self, url):
        """Test parsing invalid repository URLs."""
        service = GitHubService()
        with pytest.raises(InvalidRepositoryException):
            service._parse_repo_url(url)

    def test_get_pull_request_metadata_success(self):
        """Test successful PR metadata retrieval."""
        service = GitHubService("test_token")

        # Mock repository and PR
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.id = 123456789
        mock_pr.number = 42
        mock_pr.title = "Test PR"
        mock_pr.body = "Test description"
        mock_pr.state = "open"
        mock_pr.created_at = datetime(2025, 9, 17, 10, 0, 0)
        mock_pr.updated_at = datetime(2025, 9, 17, 12, 0, 0)
        mock_pr.merged_at = None
        mock_pr.closed_at = None
        mock_pr.user = Mock()
        mock_pr.user.login = "testuser"
        mock_pr.user.id = 12345
        mock_pr.user.type = "User"
        mock_pr.base = Mock()
        mock_pr.base.ref = "main"
        mock_pr.base.sha = "abc123"
        mock_pr.base.repo = Mock()
        mock_pr.base.repo.full_name = "testorg/testrepo"
        mock_pr.head = Mock()
        mock_pr.head.ref = "feature-branch"
        mock_pr.head.sha = "def456"
        mock_pr.head.repo = Mock()
        mock_pr.head.repo.full_name = "testorg/testrepo"
        mock_pr.additions = 45
        mock_pr.deletions = 12
        mock_pr.changed_files = 3
        mock_pr.commits = 5
        mock_pr.mergeable = True
        mock_pr.draft = False
        mock_pr.labels = []

        mock_repo.get_pull.return_value = mock_pr

        with patch.object(service, "get_repository", return_value=mock_repo):
            metadata = service.get_pull_request_metadata(
                "https://github.com/testorg/testrepo", 42
            )

            assert metadata["id"] == 123456789
            assert metadata["number"] == 42
            assert metadata["title"] == "Test PR"
            assert metadata["state"] == "open"
            assert metadata["author"]["login"] == "testuser"

    def test_get_pull_request_files_success(self):
        """Test successful PR files retrieval."""
        service = GitHubService("test_token")

        # Mock file objects
        mock_file1 = Mock()
        mock_file1.filename = "app/main.py"
        mock_file1.previous_filename = None
        mock_file1.status = "modified"
        mock_file1.additions = 10
        mock_file1.deletions = 5
        mock_file1.changes = 15
        mock_file1.sha = "abc123"
        mock_file1.blob_url = (
            "https://github.com/testorg/testrepo/blob/main/app/main.py"
        )
        mock_file1.raw_url = "https://github.com/testorg/testrepo/raw/main/app/main.py"
        mock_file1.patch = "@@ -1,5 +1,10 @@"
        mock_file1.size = 1024

        mock_file2 = Mock()
        mock_file2.filename = "tests/test_main.py"
        mock_file2.previous_filename = None
        mock_file2.status = "added"
        mock_file2.additions = 20
        mock_file2.deletions = 0
        mock_file2.changes = 20
        mock_file2.sha = "def456"
        mock_file2.blob_url = (
            "https://github.com/testorg/testrepo/blob/main/tests/test_main.py"
        )
        mock_file2.raw_url = (
            "https://github.com/testorg/testrepo/raw/main/tests/test_main.py"
        )
        mock_file2.patch = "@@ -0,0 +1,20 @@"
        mock_file2.size = 512

        mock_pr = Mock()
        mock_pr.changed_files = 2
        mock_pr.get_files.return_value = [mock_file1, mock_file2]

        with patch.object(service, "get_pull_request", return_value=mock_pr):
            files_data = service.get_pull_request_files(
                "https://github.com/testorg/testrepo", 42
            )

            assert len(files_data["files"]) == 2
            assert files_data["files"][0]["filename"] == "app/main.py"
            assert files_data["files"][1]["filename"] == "tests/test_main.py"
            assert files_data["metadata"]["total_files_in_pr"] == 2
            assert files_data["metadata"]["processed_files"] == 2

    def test_get_file_content_success(self):
        """Test successful file content retrieval."""
        service = GitHubService("test_token")

        # Mock file content
        mock_content = Mock()
        mock_content.name = "main.py"
        mock_content.size = 1024
        mock_content.sha = "abc123"
        mock_content.type = "file"
        mock_content.encoding = "base64"
        mock_content.decoded_content = b"print('Hello, World!')"
        mock_content.download_url = (
            "https://raw.githubusercontent.com/testorg/testrepo/main/app/main.py"
        )
        mock_content.html_url = (
            "https://github.com/testorg/testrepo/blob/main/app/main.py"
        )

        mock_repo = Mock()
        mock_repo.get_contents.return_value = mock_content

        with patch.object(service, "get_repository", return_value=mock_repo):
            content_data = service.get_file_content(
                "https://github.com/testorg/testrepo", "app/main.py", "main"
            )

            assert content_data["path"] == "app/main.py"
            assert content_data["name"] == "main.py"
            assert content_data["size"] == 1024
            assert content_data["is_text"] is True
            assert "Hello, World!" in content_data["content"]

    def test_get_file_content_binary(self):
        """Test binary file content handling."""
        service = GitHubService("test_token")

        # Mock binary file content
        mock_content = Mock()
        mock_content.name = "image.png"
        mock_content.size = 2048
        mock_content.sha = "def456"
        mock_content.type = "file"
        mock_content.encoding = "base64"
        mock_content.decoded_content = b"\x89PNG\r\n\x1a\n"  # PNG header
        mock_content.download_url = (
            "https://raw.githubusercontent.com/testorg/testrepo/main/image.png"
        )
        mock_content.html_url = (
            "https://github.com/testorg/testrepo/blob/main/image.png"
        )

        mock_repo = Mock()
        mock_repo.get_contents.return_value = mock_content

        with patch.object(service, "get_repository", return_value=mock_repo):
            content_data = service.get_file_content(
                "https://github.com/testorg/testrepo", "image.png", "main"
            )

            assert content_data["is_text"] is False
            assert content_data["content"] is None

    def test_file_too_large(self):
        """Test handling of files that are too large."""
        service = GitHubService("test_token")

        # Mock large file
        mock_content = Mock()
        mock_content.size = 2 * 1024 * 1024  # 2MB (larger than 1MB limit)

        mock_repo = Mock()
        mock_repo.get_contents.return_value = mock_content

        with patch.object(service, "get_repository", return_value=mock_repo):
            with pytest.raises(GitHubAPIException) as exc_info:
                service.get_file_content(
                    "https://github.com/testorg/testrepo", "large_file.py", "main"
                )

            assert "exceeds maximum" in str(exc_info.value)

    def test_rate_limit_info_update(self):
        """Test rate limit information update."""
        service = GitHubService("test_token")

        # Mock rate limit response
        mock_rate_limit = Mock()
        mock_core = Mock()
        mock_core.remaining = 4500
        mock_core.reset = "2025-09-17T14:00:00Z"
        mock_rate_limit.core = mock_core

        with patch.object(
            service._github, "get_rate_limit", return_value=mock_rate_limit
        ):
            service._update_rate_limit_info()

            assert service.rate_limit_remaining == 4500

    def test_string_representation(self):
        """Test string representation of GitHubService."""
        service_auth = GitHubService("test_token")
        GitHubService()  # Test no-auth case

        assert "authenticated" in str(service_auth)
        # The no-auth case depends on environment variables
