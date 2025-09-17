"""Tests for settings configuration."""

import os
import tempfile
import pytest
from unittest.mock import patch, Mock

from app.config.settings import (
    Settings,
    AppConfig,
    APIConfig,
    DatabaseConfig,
    RedisConfig,
    CeleryConfig,
    GitHubConfig,
    LLMConfig,
    AgentConfig,
    CacheConfig,
    SecurityConfig,
    substitute_env_vars,
    load_config,
    get_settings,
    reload_settings,
)


class TestEnvironmentVariableSubstitution:
    """Test environment variable substitution."""

    def test_substitute_single_var(self):
        """Test substitution of a single environment variable."""
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            result = substitute_env_vars("url = '$TEST_VAR'")
            assert "test_value" in result

    def test_substitute_multiple_vars(self):
        """Test substitution of multiple environment variables."""
        with patch.dict(os.environ, {"HOST": "localhost", "PORT": "5432"}):
            result = substitute_env_vars(
                "url = 'postgresql://user:pass@$HOST:$PORT/db'"
            )
            assert "localhost" in result
            assert "5432" in result

    def test_substitute_missing_var(self):
        """Test substitution with missing environment variable."""
        result = substitute_env_vars("url = '$MISSING_VAR'")
        assert "$MISSING_VAR" in result  # Should remain unchanged

    def test_substitute_no_vars(self):
        """Test string with no environment variables."""
        original = "url = 'static_value'"
        result = substitute_env_vars(original)
        assert result == original

    def test_substitute_complex_pattern(self):
        """Test complex substitution patterns."""
        with patch.dict(os.environ, {"DB_USER": "postgres", "DB_PASS": "secret123"}):
            config_str = """
[database]
url = "postgresql://$DB_USER:$DB_PASS@localhost:5432/testdb"
backup_url = "postgresql://$DB_USER:$DB_PASS@backup:5432/testdb"
"""
            result = substitute_env_vars(config_str)
            assert "postgres" in result
            assert "secret123" in result
            assert "$DB_USER" not in result
            assert "$DB_PASS" not in result


class TestConfigModels:
    """Test configuration model classes."""

    def test_app_config_defaults(self):
        """Test AppConfig default values."""
        config = AppConfig()
        assert config.name == "Code Reviewer Agent"
        assert config.version == "1.0.0"
        assert config.debug is False
        assert config.log_level == "INFO"
        assert config.log_to_file is True

    def test_app_config_custom_values(self):
        """Test AppConfig with custom values."""
        config = AppConfig(
            name="Custom App",
            version="2.0.0",
            debug=True,
            log_level="DEBUG",
            log_to_file=False,
        )
        assert config.name == "Custom App"
        assert config.version == "2.0.0"
        assert config.debug is True
        assert config.log_level == "DEBUG"
        assert config.log_to_file is False

    def test_api_config_defaults(self):
        """Test APIConfig default values."""
        config = APIConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.cors_origins == ["*"]
        assert config.rate_limit_requests == 100
        assert config.rate_limit_window == 60

    def test_database_config_required(self):
        """Test DatabaseConfig requires URL."""
        config = DatabaseConfig(url="postgresql://localhost/test")
        assert config.url == "postgresql://localhost/test"

    def test_github_config_defaults(self):
        """Test GitHubConfig default values."""
        config = GitHubConfig()
        assert config.api_url == "https://api.github.com"
        assert config.timeout == 30
        assert config.max_files_per_pr == 50
        assert config.max_file_size_kb == 1024

    def test_llm_config_defaults(self):
        """Test LLMConfig default values."""
        config = LLMConfig()
        assert config.provider == "ollama"
        assert config.base_url is None
        assert config.model is None
        assert config.openai_api_key == ""

    def test_agent_config_defaults(self):
        """Test AgentConfig default values."""
        config = AgentConfig()
        assert config.max_analysis_time == 300
        assert config.max_concurrent_analyses == 5
        assert config.retry_attempts == 3
        assert "python" in config.analysis_languages
        assert "javascript" in config.analysis_languages

    def test_cache_config_defaults(self):
        """Test CacheConfig default values."""
        config = CacheConfig()
        assert config.ttl_analysis_results == 86400
        assert config.ttl_pr_data == 3600
        assert config.max_cache_size_mb == 512

    def test_security_config_required(self):
        """Test SecurityConfig requires secret key."""
        config = SecurityConfig(secret_key="test-secret")
        assert config.secret_key == "test-secret"
        assert config.api_key_header == "X-API-Key"


class TestConfigLoading:
    """Test configuration loading functionality."""

    def test_load_config_with_temp_file(self):
        """Test loading configuration from a temporary file."""
        config_content = """
[app]
name = "Test App"
version = "1.0.0"
debug = true

[api]
host = "127.0.0.1"
port = 9000

[database]
url = "postgresql://test:test@localhost/test"

[redis]
url = "redis://localhost:6379/0"

[celery]
broker_url = "redis://localhost:6379/0"
result_backend = "redis://localhost:6379/0"

[github]
api_url = "https://api.github.com"
timeout = 60

[llm]
provider = "openai"
openai_api_key = "test-key"

[agent]
max_analysis_time = 600

[cache]
ttl_analysis_results = 7200

[security]
secret_key = "test-secret-key"
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            # Mock the Path class to return our temp file
            with patch("app.config.settings.Path") as mock_path:
                mock_path_instance = Mock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance

                with patch("app.config.settings.toml.load") as mock_load:
                    mock_load.return_value = {
                        "app": {"name": "Test App", "debug": True},
                        "api": {"host": "127.0.0.1", "port": 9000},
                        "database": {"url": "postgresql://test:test@localhost/test"},
                        "redis": {"url": "redis://localhost:6379/0"},
                        "celery": {
                            "broker_url": "redis://localhost:6379/0",
                            "result_backend": "redis://localhost:6379/0",
                        },
                        "github": {"api_url": "https://api.github.com", "timeout": 60},
                        "llm": {"provider": "openai", "openai_api_key": "test-key"},
                        "agent": {"max_analysis_time": 600},
                        "cache": {"ttl_analysis_results": 7200},
                        "security": {"secret_key": "test-secret-key"},
                    }

                    settings = load_config()

                    assert settings.app.name == "Test App"
                    assert settings.app.debug is True
                    assert settings.api.host == "127.0.0.1"
                    assert settings.api.port == 9000
                    assert (
                        settings.database.url == "postgresql://test:test@localhost/test"
                    )

        finally:
            os.unlink(temp_path)

    def test_load_config_missing_file(self):
        """Test loading configuration when file is missing."""
        with patch("app.config.settings.Path") as mock_path:
            mock_path.return_value.exists.return_value = False

            with pytest.raises(FileNotFoundError):
                load_config()

    def test_load_config_with_env_substitution(self):
        """Test configuration loading with environment variable substitution."""
        with patch.dict(
            os.environ,
            {
                "TEST_DATABASE_URL": "postgresql://env_user:env_pass@localhost/env_db",
                "TEST_REDIS_URL": "redis://localhost:6379/1",
            },
        ):
            with patch("app.config.settings.Path") as mock_path:
                mock_path.return_value.exists.return_value = True

                with patch("app.config.settings.toml.load") as mock_load:
                    mock_load.return_value = {
                        "app": {"name": "Test App"},
                        "api": {},
                        "database": {"url": "$TEST_DATABASE_URL"},
                        "redis": {"url": "$TEST_REDIS_URL"},
                        "celery": {
                            "broker_url": "$TEST_REDIS_URL",
                            "result_backend": "$TEST_REDIS_URL",
                        },
                        "github": {},
                        "llm": {"openai_api_key": ""},
                        "agent": {},
                        "cache": {},
                        "security": {"secret_key": "test-secret"},
                    }

                    settings = load_config()

                    assert "env_user" in settings.database.url
                    assert "env_pass" in settings.database.url
                    assert "env_db" in settings.database.url
                    assert settings.redis.url == "redis://localhost:6379/1"


class TestSettingsGlobals:
    """Test global settings functions."""

    def test_get_settings_singleton(self):
        """Test that get_settings returns the same instance."""
        # This test may need to be adapted based on the actual implementation
        # since it involves global state
        with patch("app.config.settings.load_config") as mock_load:
            mock_settings = Settings(
                app=AppConfig(),
                api=APIConfig(),
                database=DatabaseConfig(url="test://localhost/test"),
                redis=RedisConfig(url="redis://localhost/test"),
                celery=CeleryConfig(
                    broker_url="redis://localhost", result_backend="redis://localhost"
                ),
                github=GitHubConfig(),
                llm=LLMConfig(),
                agent=AgentConfig(),
                cache=CacheConfig(),
                security=SecurityConfig(secret_key="test"),
            )
            mock_load.return_value = mock_settings

            # Clear the global settings first
            with patch("app.config.settings._settings", None):
                settings1 = get_settings()
                settings2 = get_settings()

                # Should be the same instance (singleton pattern)
                assert settings1 is settings2

    def test_reload_settings(self):
        """Test settings reload functionality."""
        with patch("app.config.settings.load_config") as mock_load:
            mock_settings = Settings(
                app=AppConfig(name="Reloaded App"),
                api=APIConfig(),
                database=DatabaseConfig(url="test://localhost/test"),
                redis=RedisConfig(url="redis://localhost/test"),
                celery=CeleryConfig(
                    broker_url="redis://localhost", result_backend="redis://localhost"
                ),
                github=GitHubConfig(),
                llm=LLMConfig(),
                agent=AgentConfig(),
                cache=CacheConfig(),
                security=SecurityConfig(secret_key="test"),
            )
            mock_load.return_value = mock_settings

            reloaded_settings = reload_settings()
            assert reloaded_settings.app.name == "Reloaded App"


class TestConfigValidation:
    """Test configuration validation."""

    def test_invalid_config_structure(self):
        """Test handling of invalid configuration structure."""
        with patch("app.config.settings.Path") as mock_path:
            mock_path.return_value.exists.return_value = True

            with patch("app.config.settings.toml.load") as mock_load:
                # Missing required fields
                mock_load.return_value = {
                    "app": {"name": "Test App"},
                    # Missing required sections
                }

                with pytest.raises(Exception):  # Pydantic validation error
                    load_config()

    def test_partial_config_with_defaults(self):
        """Test partial configuration with default values."""
        with patch("app.config.settings.Path") as mock_path:
            mock_path.return_value.exists.return_value = True

            with patch("app.config.settings.toml.load") as mock_load:
                # Minimal configuration with required fields only
                mock_load.return_value = {
                    "app": {},  # Will use defaults
                    "api": {},  # Will use defaults
                    "database": {"url": "postgresql://localhost/test"},
                    "redis": {"url": "redis://localhost:6379/0"},
                    "celery": {
                        "broker_url": "redis://localhost:6379/0",
                        "result_backend": "redis://localhost:6379/0",
                    },
                    "github": {},  # Will use defaults
                    "llm": {"openai_api_key": ""},
                    "agent": {},  # Will use defaults
                    "cache": {},  # Will use defaults
                    "security": {"secret_key": "test-secret"},
                }

                settings = load_config()

                # Should use default values
                assert settings.app.name == "Code Reviewer Agent"
                assert settings.api.port == 8000
                assert settings.github.timeout == 30
