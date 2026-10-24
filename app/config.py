from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    football_api_key: str
    football_api_base_url: str = "https://api.football-data.org/v4"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env")

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, v: str) -> str:
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix) :]
        return v


settings = Settings()
