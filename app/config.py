class Settings():
    APP_NAME: str = "校园情感陪伴助手"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    CHAT_MODEL_NAME = "qwen3-vl:4b"
    EMBEDDING_MODEL_NAME = "qwen3-embedding:4b"
    ROUTER_MODEL_NAME = "qwen2.5:3b"
    DATABASE_URL: str = "sqlite:///./data/sqlite/example_db.sqlite3"
    CHROMA_PATH: str = "./data/chroma"
    REDIS_URL: str = "redis://localhost:6379/0"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "qwen-plus"
    VOICE_SERVICE: str = "edge-tts"

    TEST_SYSTEM_PROMPT: str = """你是一个温柔、善解人意的情感陪伴助手。请用温暖、关怀的语言回应用户。
        注意用户的情感状态，根据用户的情绪给予适当的安慰和鼓励。"""



settings = Settings()