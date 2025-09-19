from pydantic_settings import BaseSettings
from pydantic import Field
from core.enums import LogLevels
from functools import lru_cache

class Settings(BaseSettings):

    APP_NAME: str = "Threat Detection API"
    DEBUG: bool = True
    ENV: str = 'development'

    ALLOWED_ORIGINS: list[str] = Field(default_factory=list)

    # DB Settings

    DB_USER: str 
    DB_PASS: str
    DB_HOST: str
    DB_PORT: str = "5432"
    DB_NAME: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 Days

    # THIRD PARTY KEYS HERE 

    # Logs
    log_level: LogLevels = Field(LogLevels.info, env="LOG_LEVEL")

    # ENV stuff

    class Config:
        env_file = "./.env"
        enf_file_encoding = "utf-8"

    @property
    def SQLALCHEMY_DATABASE_URL(self):
        return f"postgresql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}/{self.DB_NAME}"
    

@lru_cache()
def get_settings() -> Settings:
    return Settings()

