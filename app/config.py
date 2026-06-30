class Config:
    CHAT_MODEL_NAME = "qwen3-vl:4b"
    EMBEDDING_MODEL_NAME = "qwen3-embedding:4b"
    ROUTER_MODEL_NAME = "qwen2.5:3b"

    def __repr__(self):
        return f"Config(chat_model={self.CHAT_MODEL_NAME}, embedding_model={self.EMBEDDING_MODEL_NAME}, router_model={self.ROUTER_MODEL_NAME})"
