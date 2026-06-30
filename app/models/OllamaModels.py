from langchain_ollama import ChatOllama, OllamaEmbeddings



"""
提供 Ollama 模型的初始化接口
"""


def get_ollama_llm(model_name: str) -> ChatOllama:
    return ChatOllama(model_name=model_name)


def get_ollama_embeddings(embedding_model_name: str) -> OllamaEmbeddings:
    return OllamaEmbeddings(model_name=embedding_model_name)
