from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    """
    Application-wide settings loaded from environment variables or .env file.
    All configuration lives here — no scattered os.getenv() calls elsewhere.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str = "sqlite:///./data/finance_tracker.db"
    app_env: str = "development"
    log_level: str = "INFO"
    groq_api_key: str = ""

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def db_path(self) -> Path:
        """Resolve the local file path from the SQLite URL."""
        raw = self.database_url.replace("sqlite:///", "")
        return Path(raw).resolve()


settings = Settings()
