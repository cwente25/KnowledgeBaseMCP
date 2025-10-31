"""Configuration management using pydantic-settings"""
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    database_url: str = "sqlite:///./knowledge_base.db"

    # Knowledge Base (Phase 1)
    knowledge_base_path: Path = Path.home() / "knowledge-base"
    categories: str = "people,recipes,meetings,procedures,tasks"

    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    cors_origins: str = "http://localhost:8000"

    # Authentication
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # AI Integration
    anthropic_api_key: str = ""
    default_model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 4096

    # MCP Settings
    mcp_server_name: str = "Knowledge Base"
    mcp_enable_http: bool = True

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def categories_list(self) -> List[str]:
        """Parse categories from comma-separated string"""
        return [cat.strip() for cat in self.categories.split(",")]


# Global settings instance
settings = Settings()
