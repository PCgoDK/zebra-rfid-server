from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "zebra-rfid-server"
    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_name: str = "zebra_rfid_server"
    db_user: str = "zebra_rfid_server"
    db_password: str = ""
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    tcp_host: str = "0.0.0.0"
    tcp_port: int = 5084
    log_level: str = "INFO"
    jwt_secret: str = ""
    jwt_access_token_minutes: int = 30
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 60
    duplicate_window_ms: int = 1000
    initial_admin_username: str = "admin"
    initial_admin_password: str = ""
    data_dir: str = "/var/lib/zebra-rfid-server"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}"
        )