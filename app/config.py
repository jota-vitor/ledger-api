from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Ledger API"
    database_url: str = "sqlite:///./ledger.db"


settings = Settings()
