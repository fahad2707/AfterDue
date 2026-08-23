from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", REPO_ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"
    log_level: str = "INFO"

    mongodb_uri: str = ""
    mongodb_db: str = "reclaim"

    internal_api_key: str = ""
    cors_origins: str = "http://localhost:3000"

    # The language layer is off by default. The measured economic path must
    # never depend on it.
    llm_enabled: bool = False
    anthropic_api_key: str = ""
    anthropic_model: str = ""
    llm_timeout_seconds: int = 8

    policy_version: str = "v1"
    model_artifact_path: str = "app/ml/artifacts/recovery_model.joblib"
    sim_default_seed: int = 42
    intervention_budget_default: int = 150

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
