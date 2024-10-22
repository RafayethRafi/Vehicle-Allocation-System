# app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # MongoDB settings
    MONGODB_URI: str
    MONGODB_DB_NAME: str = "vehicle_allocation"
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    
    # API settings
    API_PREFIX: str = "/api"
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
