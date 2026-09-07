from pydantic_settings import BaseSettings, SettingsConfigDict
 
#More details to be included later
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    database_url: str = "postgresql+asyncpg://complianceops:complianceops@localhost:5432/complianceops"
    screening_service_url: str = "http://localhost:8002"
 
 
settings = Settings()