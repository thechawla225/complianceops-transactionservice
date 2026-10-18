from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql+asyncpg://complianceops:complianceops@localhost:5432/complianceops"
    screening_service_url: str = "http://localhost:8002"
    # Flagged transactions are published here for the notifier. Empty = publishing disabled (local dev).
    sqs_queue_url: str = ""
    aws_region: str = "us-west-2"


settings = Settings()
