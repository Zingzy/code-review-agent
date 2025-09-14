"""
Simple Configuration Management System
"""

import os
import re
import toml
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv


class AppConfig(BaseModel):
    """Application configuration"""

    name: str = "Code Reviewer Agent"
    version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file_path: str = "logs/app.log"


class APIConfig(BaseModel):
    """API server configuration"""

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = ["*"]
    rate_limit_requests: int = 100
    rate_limit_window: int = 60


class DatabaseConfig(BaseModel):
    """Database configuration"""

    url: str


class RedisConfig(BaseModel):
    """Redis configuration"""

    url: str


class CeleryConfig(BaseModel):
    """Celery configuration"""

    broker_url: str
    result_backend: str


class GitHubConfig(BaseModel):
    """GitHub API configuration"""

    api_url: str = "https://api.github.com"
    timeout: int = 30
    max_files_per_pr: int = 50
    max_file_size_kb: int = 1024


class LLMConfig(BaseModel):
    """LLM configuration"""

    provider: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "codellama:13b"
    ollama_timeout: int = 60
    openai_api_key: str = ""
    openai_model: str = "gpt-4"
    openai_max_tokens: int = 4000
    openai_temperature: float = 0.1
    max_context_length: int = 8192
    chunk_size: int = 1000


class AgentConfig(BaseModel):
    """AI Agent configuration"""

    max_analysis_time: int = 300
    chunk_size: int = 1000
    max_concurrent_analyses: int = 5
    retry_attempts: int = 3
    analysis_languages: List[str] = [
        "python",
        "javascript",
        "typescript",
        "java",
        "go",
        "rust",
        "cpp",
        "c#",
        "php",
        "ruby",
    ]


class CacheConfig(BaseModel):
    """Cache configuration"""

    ttl_analysis_results: int = 86400
    ttl_pr_data: int = 3600
    ttl_github_user_data: int = 7200
    max_cache_size_mb: int = 512


class SecurityConfig(BaseModel):
    """Security configuration"""

    api_key_header: str = "X-API-Key"
    secret_key: str


class Settings(BaseModel):
    """Main application settings"""

    app: AppConfig
    api: APIConfig
    database: DatabaseConfig
    redis: RedisConfig
    celery: CeleryConfig
    github: GitHubConfig
    llm: LLMConfig
    agent: AgentConfig
    cache: CacheConfig
    security: SecurityConfig


def substitute_env_vars(config_str: str) -> str:
    """Substitute environment variables in config string"""
    pattern = r"\$([A-Z_][A-Z0-9_]*)"

    def replacer(match):
        var_name = match.group(1)
        return os.getenv(var_name, f"${var_name}")

    return re.sub(pattern, replacer, config_str)


def load_config() -> Settings:
    """Load configuration from TOML file"""
    load_dotenv()

    config_path = Path("config.toml")
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    config_data = toml.load(config_path)
    config_str = toml.dumps(config_data)
    config_str = substitute_env_vars(config_str)
    config_data = toml.loads(config_str)

    # Create nested configuration objects
    settings = Settings(
        app=AppConfig(**config_data.get("app", {})),
        api=APIConfig(**config_data.get("api", {})),
        database=DatabaseConfig(**config_data.get("database", {})),
        redis=RedisConfig(**config_data.get("redis", {})),
        celery=CeleryConfig(**config_data.get("celery", {})),
        github=GitHubConfig(**config_data.get("github", {})),
        llm=LLMConfig(**config_data.get("llm", {})),
        agent=AgentConfig(**config_data.get("agent", {})),
        cache=CacheConfig(**config_data.get("cache", {})),
        security=SecurityConfig(**config_data.get("security", {})),
    )

    return settings


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance"""
    global _settings
    if _settings is None:
        _settings = load_config()
    return _settings


def reload_settings() -> Settings:
    """Force reload of settings"""
    global _settings
    _settings = None
    return get_settings()


if __name__ == "__main__":
    try:
        config = get_settings()
        print("Configuration loaded successfully!")
        print(f"App Name: {config.app.name}")
        print(f"API Port: {config.api.port}")
        print(f"Log Level: {config.app.log_level}")
    except Exception as e:
        print(f"Configuration loading failed: {e}")
