from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "校园情感陪伴助手"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    DATABASE_URL: str = "sqlite:///./data/sqlite/example_db.sqlite3"
    CHROMA_PATH: str = "./data/chroma"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "qwen-plus"
    
    VOICE_SERVICE: str = "edge-tts"
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
