from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    database_url: str = "sqlite:///./echoes.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
