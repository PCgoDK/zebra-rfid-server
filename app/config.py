"""Application configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file="/etc/zebra-rfid-server/server.env")

    app_name: str = "zebra-rfid-server"
    db_name: str = "zebra_rfid_server"
    db_user: str = "zebra_rfid_server"
    db_password: str = Field(default="", repr=False)
    db_host: str = "localhost"
    db_port: int = 5432
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    tcp_host: str = "0.0.0.0"
    tcp_port: int = 5084
    log_level: str = "INFO"
    duplicate_window_ms: int = Field(default=1000, ge=0)

    @property
    def database_url(self) -> str:
        """Return the PostgreSQL URL without exposing it in configuration."""
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
