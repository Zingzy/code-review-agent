"""
GitHub API Integration Service

Provides methods to interact with GitHub API for fetching PR data, diffs, and file contents.
"""

import os
import re
from datetime import datetime
from typing import Dict, Optional, Tuple, Any

from github import Github, GithubException
from github.PullRequest import PullRequest
from github.Repository import Repository

from app.config.settings import get_settings
from app.utils.logger import logger
from app.utils.exceptions import (
    GitHubAPIException,
    InvalidRepositoryException,
    RateLimitExceededException,
)


class GitHubService:
    """
    Service for interacting with GitHub API to fetch PR data and analyze code changes.
    """

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize GitHub service with authentication.

        Args:
            github_token: Optional GitHub personal access token.
            If not provided, will try to get from environment or settings.
        """
        self.settings = get_settings()

        # Determine token to use
        self._token = self._get_github_token(github_token)

        # Initialize PyGithub client
        if self._token:
            self._github = Github(
                self._token,
                timeout=self.settings.github.timeout,
                retry=self.settings.github.max_retries
                if hasattr(self.settings.github, "max_retries")
                else 3,
            )
            logger.info("GitHub service initialized with authentication")
        else:
            self._github = Github()
            logger.warning(
                "GitHub service initialized without authentication (rate limits will apply)"
            )

        # Track rate limit info
        self._rate_limit_remaining: Optional[int] = None
        self._rate_limit_reset: Optional[datetime] = None

    def _get_github_token(self, provided_token: Optional[str]) -> Optional[str]:
        """Get GitHub token from various sources."""
        # Priority: provided_token > environment variable > settings (though settings don't store tokens)
        if provided_token:
            return provided_token

        # Try environment variable
        env_token = os.getenv("GITHUB_TOKEN")
        if env_token:
            return env_token

        logger.info("No GitHub token provided - using unauthenticated requests")
        return None

    def _parse_repo_url(self, repo_url: str) -> Tuple[str, str]:
        """
        Parse GitHub repository URL to extract owner and repo name.

        Args:
            repo_url: GitHub repository URL

        Returns:
            Tuple of (owner, repo_name)

        Raises:
            InvalidRepositoryException: If URL format is invalid
        """
        try:
            # Clean up URL
            repo_url = repo_url.strip().rstrip("/")

            # Handle different GitHub URL formats
            patterns = [
                r"^https://github\.com/([^/]+)/([^/]+)/?$",  # https://github.com/owner/repo
                r"^git@github\.com:([^/]+)/([^/]+)\.git$",  # git@github.com:owner/repo.git
                r"^([^/]+)/([^/]+)$",  # owner/repo
            ]

            for pattern in patterns:
                match = re.match(pattern, repo_url)
                if match:
                    owner, repo = match.groups()
                    # Remove .git suffix if present
                    if repo.endswith(".git"):
                        repo = repo[:-4]
                    return owner, repo

            raise InvalidRepositoryException(
                repo_url,
                "Invalid GitHub repository URL format. Expected: https://github.com/owner/repo",
            )

        except Exception as e:
            if isinstance(e, InvalidRepositoryException):
                raise
            raise InvalidRepositoryException(
                repo_url, f"Failed to parse repository URL: {str(e)}"
            )

    def _update_rate_limit_info(self) -> None:
        """Update internal rate limit information."""
        try:
            rate_limit = self._github.get_rate_limit()
            self._rate_limit_remaining = rate_limit.core.remaining
            self._rate_limit_reset = rate_limit.core.reset

            logger.debug(
                f"GitHub rate limit: {self._rate_limit_remaining} requests remaining, "
                f"resets at {self._rate_limit_reset}"
            )

            # Warn if running low on requests
            if self._rate_limit_remaining and self._rate_limit_remaining < 100:
                logger.warning(
                    f"GitHub rate limit running low: {self._rate_limit_remaining} requests remaining"
                )

        except Exception as e:
            logger.warning(f"Failed to check GitHub rate limit: {e}")

    def _handle_github_exception(self, e: GithubException, operation: str) -> None:
        """
        Handle GitHub API exceptions and convert to application exceptions.

        Args:
            e: GitHub exception
            operation: Description of the operation that failed
        """
        if e.status == 401:
            raise GitHubAPIException(
                f"Authentication failed during {operation}. Check your GitHub token.",
                status_code=401,
                details={"operation": operation, "github_status": e.status},
            )
        elif e.status == 403:
            # Could be rate limit or permissions
            if "rate limit" in str(e.data).lower():
                reset_time = None
                if hasattr(e, "headers") and "X-RateLimit-Reset" in e.headers:
                    try:
                        reset_timestamp = int(e.headers["X-RateLimit-Reset"])
                        reset_time = datetime.fromtimestamp(reset_timestamp)
                    except (ValueError, TypeError):
                        pass

                raise RateLimitExceededException(
                    f"GitHub API rate limit exceeded during {operation}",
                    retry_after=3600,  # Default to 1 hour
                    details={
                        "operation": operation,
                        "reset_time": reset_time.isoformat() if reset_time else None,
                    },
                )
            else:
                raise GitHubAPIException(
                    f"Permission denied during {operation}. Check repository access.",
                    status_code=403,
                    details={"operation": operation, "github_status": e.status},
                )
        elif e.status == 404:
            raise GitHubAPIException(
                f"Resource not found during {operation}. Check repository URL and PR number.",
                status_code=404,
                details={"operation": operation, "github_status": e.status},
            )
        else:
            raise GitHubAPIException(
                f"GitHub API error during {operation}: {e.data.get('message', str(e))}",
                status_code=e.status or 500,
                details={
                    "operation": operation,
                    "github_status": e.status,
                    "github_message": e.data.get("message")
                    if hasattr(e, "data")
                    else None,
                },
            )

    def get_repository(self, repo_url: str) -> Repository:
        """
        Get GitHub repository object.

        Args:
            repo_url: GitHub repository URL

        Returns:
            GitHub repository object

        Raises:
            InvalidRepositoryException: If repository URL is invalid
            GitHubAPIException: If API request fails
        """
        try:
            owner, repo_name = self._parse_repo_url(repo_url)

            logger.debug(f"Fetching repository: {owner}/{repo_name}")

            repository = self._github.get_repo(f"{owner}/{repo_name}")

            # Update rate limit info
            self._update_rate_limit_info()

            logger.info(f"Successfully fetched repository: {repository.full_name}")
            return repository

        except GithubException as e:
            self._handle_github_exception(e, f"fetching repository {repo_url}")
        except InvalidRepositoryException:
            raise
        except Exception as e:
            raise GitHubAPIException(
                f"Unexpected error fetching repository {repo_url}: {str(e)}",
                details={"repo_url": repo_url},
            )

    def get_pull_request(self, repo_url: str, pr_number: int) -> PullRequest:
        """
        Get GitHub pull request object.

        Args:
            repo_url: GitHub repository URL
            pr_number: Pull request number

        Returns:
            GitHub pull request object

        Raises:
            InvalidRepositoryException: If repository URL is invalid
            GitHubAPIException: If API request fails
        """
        try:
            repository = self.get_repository(repo_url)

            logger.debug(f"Fetching PR #{pr_number} from {repository.full_name}")

            pull_request = repository.get_pull(pr_number)

            logger.info(
                f"Successfully fetched PR #{pr_number}: '{pull_request.title}' "
                f"by {pull_request.user.login}"
            )

            return pull_request

        except GithubException as e:
            self._handle_github_exception(
                e, f"fetching PR #{pr_number} from {repo_url}"
            )
        except (InvalidRepositoryException, GitHubAPIException):
            raise
        except Exception as e:
            raise GitHubAPIException(
                f"Unexpected error fetching PR #{pr_number} from {repo_url}: {str(e)}",
                details={"repo_url": repo_url, "pr_number": pr_number},
            )

    def get_pull_request_metadata(
        self, repo_url: str, pr_number: int
    ) -> Dict[str, Any]:
        """
        Get comprehensive metadata about a pull request.

        Args:
            repo_url: GitHub repository URL
            pr_number: Pull request number

        Returns:
            Dictionary containing PR metadata
        """
        try:
            pull_request = self.get_pull_request(repo_url, pr_number)

            metadata = {
                "id": pull_request.id,
                "number": pull_request.number,
                "title": pull_request.title,
                "body": pull_request.body,
                "state": pull_request.state,
                "created_at": pull_request.created_at.isoformat(),
                "updated_at": pull_request.updated_at.isoformat(),
                "merged_at": pull_request.merged_at.isoformat()
                if pull_request.merged_at
                else None,
                "closed_at": pull_request.closed_at.isoformat()
                if pull_request.closed_at
                else None,
                "author": {
                    "login": pull_request.user.login,
                    "id": pull_request.user.id,
                    "type": pull_request.user.type,
                },
                "base": {
                    "ref": pull_request.base.ref,
                    "sha": pull_request.base.sha,
                    "repo": pull_request.base.repo.full_name,
                },
                "head": {
                    "ref": pull_request.head.ref,
                    "sha": pull_request.head.sha,
                    "repo": pull_request.head.repo.full_name,
                },
                "stats": {
                    "additions": pull_request.additions,
                    "deletions": pull_request.deletions,
                    "changed_files": pull_request.changed_files,
                    "commits": pull_request.commits,
                },
                "mergeable": pull_request.mergeable,
                "draft": pull_request.draft,
                "labels": [label.name for label in pull_request.labels],
            }

            logger.debug(
                f"Retrieved metadata for PR #{pr_number}: {pull_request.changed_files} files changed"
            )
            return metadata

        except (InvalidRepositoryException, GitHubAPIException):
            raise
        except Exception as e:
            raise GitHubAPIException(
                f"Failed to get PR metadata for #{pr_number}: {str(e)}",
                details={"repo_url": repo_url, "pr_number": pr_number},
            )

    def get_pull_request_files(self, repo_url: str, pr_number: int) -> Dict[str, Any]:
        """
        Get list of files changed in a pull request with their details.

        Args:
            repo_url: GitHub repository URL
            pr_number: Pull request number

        Returns:
            Dictionary containing files data and metadata
        """
        try:
            pull_request = self.get_pull_request(repo_url, pr_number)
            files = pull_request.get_files()

            # Check file count limit
            max_files = self.settings.github.max_files_per_pr
            file_count = pull_request.changed_files

            if file_count > max_files:
                logger.warning(
                    f"PR #{pr_number} has {file_count} files, exceeding limit of {max_files}. "
                    "Only first files will be processed."
                )

            processed_files = []
            total_size = 0
            max_file_size = (
                self.settings.github.max_file_size_kb * 1024
            )  # Convert to bytes

            for file in files:
                # Check individual file size
                if hasattr(file, "size") and file.size and file.size > max_file_size:
                    logger.warning(
                        f"Skipping file {file.filename}: size {file.size} bytes exceeds limit of {max_file_size} bytes"
                    )
                    continue

                file_data = {
                    "filename": file.filename,
                    "previous_filename": file.previous_filename,
                    "status": file.status,  # added, removed, modified, renamed
                    "additions": file.additions,
                    "deletions": file.deletions,
                    "changes": file.changes,
                    "sha": file.sha,
                    "blob_url": file.blob_url,
                    "raw_url": file.raw_url,
                    "patch": file.patch,
                }

                # Add file size if available
                if hasattr(file, "size") and file.size:
                    file_data["size"] = file.size
                    total_size += file.size

                processed_files.append(file_data)

                # Stop if we hit the file limit
                if len(processed_files) >= max_files:
                    break

            result = {
                "files": processed_files,
                "metadata": {
                    "total_files_in_pr": file_count,
                    "processed_files": len(processed_files),
                    "total_size_bytes": total_size,
                    "truncated": len(processed_files) < file_count,
                },
            }

            logger.info(
                f"Retrieved {len(processed_files)} files for PR #{pr_number} "
                f"(total size: {total_size / 1024:.1f} KB)"
            )

            return result

        except (InvalidRepositoryException, GitHubAPIException):
            raise
        except Exception as e:
            raise GitHubAPIException(
                f"Failed to get PR files for #{pr_number}: {str(e)}",
                details={"repo_url": repo_url, "pr_number": pr_number},
            )

    def get_file_content(
        self, repo_url: str, file_path: str, commit_sha: str
    ) -> Dict[str, Any]:
        """
        Get the content of a specific file at a given commit.

        Args:
            repo_url: GitHub repository URL
            file_path: Path to the file in the repository
            commit_sha: Git commit SHA

        Returns:
            Dictionary containing file content and metadata
        """
        try:
            repository = self.get_repository(repo_url)

            # Get file content at specific commit
            file_content = repository.get_contents(file_path, ref=commit_sha)

            # Handle if it's a file (not a directory)
            if not hasattr(file_content, "decoded_content"):
                raise GitHubAPIException(
                    f"Path {file_path} is not a file",
                    details={
                        "repo_url": repo_url,
                        "file_path": file_path,
                        "commit_sha": commit_sha,
                    },
                )

            # Check file size
            max_file_size = self.settings.github.max_file_size_kb * 1024
            if file_content.size > max_file_size:
                raise GitHubAPIException(
                    f"File {file_path} size ({file_content.size} bytes) exceeds maximum ({max_file_size} bytes)",
                    details={
                        "repo_url": repo_url,
                        "file_path": file_path,
                        "file_size": file_content.size,
                        "max_size": max_file_size,
                    },
                )

            try:
                # Try to decode content as text
                content_text = file_content.decoded_content.decode("utf-8")
                is_text = True
            except UnicodeDecodeError:
                # Binary file
                content_text = None
                is_text = False
                logger.debug(f"File {file_path} appears to be binary")

            result = {
                "path": file_path,
                "name": file_content.name,
                "size": file_content.size,
                "sha": file_content.sha,
                "type": file_content.type,
                "encoding": file_content.encoding,
                "content": content_text,
                "is_text": is_text,
                "download_url": file_content.download_url,
                "html_url": file_content.html_url,
            }

            logger.debug(
                f"Retrieved content for file {file_path} ({file_content.size} bytes)"
            )
            return result

        except GithubException as e:
            self._handle_github_exception(e, f"fetching file content for {file_path}")
        except (InvalidRepositoryException, GitHubAPIException):
            raise
        except Exception as e:
            raise GitHubAPIException(
                f"Failed to get file content for {file_path}: {str(e)}",
                details={
                    "repo_url": repo_url,
                    "file_path": file_path,
                    "commit_sha": commit_sha,
                },
            )

    def get_pull_request_diff(self, repo_url: str, pr_number: int) -> Dict[str, Any]:
        """
        Get the complete diff for a pull request.

        Args:
            repo_url: GitHub repository URL
            pr_number: Pull request number

        Returns:
            Dictionary containing diff data and metadata
        """
        try:
            repository = self.get_repository(repo_url)
            pull_request = repository.get_pull(pr_number)

            # Get the comparison between base and head
            comparison = repository.compare(
                pull_request.base.sha, pull_request.head.sha
            )

            diff_data = {
                "base_commit": {
                    "sha": pull_request.base.sha,
                    "ref": pull_request.base.ref,
                },
                "head_commit": {
                    "sha": pull_request.head.sha,
                    "ref": pull_request.head.ref,
                },
                "stats": {
                    "ahead_by": comparison.ahead_by,
                    "behind_by": comparison.behind_by,
                    "total_commits": comparison.total_commits,
                },
                "commits": [],
            }

            # Get commit information
            for commit in comparison.commits:
                commit_data = {
                    "sha": commit.sha,
                    "message": commit.commit.message,
                    "author": {
                        "name": commit.commit.author.name,
                        "email": commit.commit.author.email,
                        "date": commit.commit.author.date.isoformat(),
                    },
                    "stats": {
                        "additions": commit.stats.additions,
                        "deletions": commit.stats.deletions,
                        "total": commit.stats.total,
                    },
                }
                diff_data["commits"].append(commit_data)

            logger.info(
                f"Retrieved diff for PR #{pr_number}: {comparison.total_commits} commits, "
                f"ahead by {comparison.ahead_by}"
            )

            return diff_data

        except GithubException as e:
            self._handle_github_exception(e, f"fetching diff for PR #{pr_number}")
        except (InvalidRepositoryException, GitHubAPIException):
            raise
        except Exception as e:
            raise GitHubAPIException(
                f"Failed to get PR diff for #{pr_number}: {str(e)}",
                details={"repo_url": repo_url, "pr_number": pr_number},
            )

    def get_rate_limit_info(self) -> Dict[str, Any]:
        """
        Get current GitHub API rate limit information.

        Returns:
            Dictionary with rate limit information
        """
        try:
            rate_limit = self._github.get_rate_limit()
            return {
                "core": {
                    "limit": rate_limit.core.limit,
                    "remaining": rate_limit.core.remaining,
                    "reset": rate_limit.core.reset.isoformat(),
                },
                "search": {
                    "limit": rate_limit.search.limit,
                    "remaining": rate_limit.search.remaining,
                    "reset": rate_limit.search.reset.isoformat(),
                },
            }
        except Exception as e:
            logger.error(f"Failed to get rate limit info: {e}")
            return {"error": str(e)}

    @property
    def is_authenticated(self) -> bool:
        """Check if service is authenticated with GitHub."""
        return self._token is not None

    @property
    def rate_limit_remaining(self) -> Optional[int]:
        """Get remaining API requests."""
        return self._rate_limit_remaining

    def __str__(self) -> str:
        """String representation of GitHub service."""
        auth_status = "authenticated" if self.is_authenticated else "unauthenticated"
        return f"GitHubService({auth_status})"


# Export the service class
__all__ = ["GitHubService"]
