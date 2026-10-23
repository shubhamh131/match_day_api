from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    football_api_key: str
    football_api_base_url: str = "https://api.football-data.org/v4"
    log_level: str = "INFO"
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
