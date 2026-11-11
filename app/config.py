from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "CampusFlow AI"
    database_url: str = "sqlite:///./campusflow.db"
    agent_mode: str = "demo"
    model_api_key: str = ""
    model_base_url: str = "https://api.openai.com/v1"
    model_name: str = "gpt-4o-mini"
    max_tool_steps: int = 8


settings = Settings()
