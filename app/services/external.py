from abc import abstractmethod
from typing import Any, Dict, Optional
from .base import ExternalService


class VoiceService(ExternalService):
    @abstractmethod
    def text_to_speech(self, text: str, voice: Optional[str] = None, rate: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def speech_to_text(self, audio_data: bytes, language: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def list_voices(self) -> Dict[str, Any]:
        pass


class DocumentService(ExternalService):
    @abstractmethod
    def query_documents(self, query: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def add_document(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def update_document(self, document_id: str, content: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def delete_document(self, document_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_document(self, document_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def list_documents(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        pass


class LLMService(ExternalService):
    @abstractmethod
    def generate_text(self, prompt: str, model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 2048) -> Dict[str, Any]:
        pass

    @abstractmethod
    def chat_completion(self, messages: list, model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 2048) -> Dict[str, Any]:
        pass

    @abstractmethod
    def embeddings(self, text: str, model: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def list_models(self) -> Dict[str, Any]:
        pass


class MCPService(ExternalService):
    @abstractmethod
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def list_tools(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_tool_description(self, tool_name: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def validate_tool_arguments(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pass


class MemoryService(ExternalService):
    @abstractmethod
    def save_memory(self, user_id: str, memory_type: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def retrieve_memory(self, user_id: str, query: str, memory_type: Optional[str] = None, top_k: int = 5) -> Dict[str, Any]:
        pass

    @abstractmethod
    def update_memory(self, memory_id: str, content: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def list_memories(self, user_id: str, memory_type: Optional[str] = None) -> Dict[str, Any]:
        pass


class RedisService(ExternalService):
    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        pass

    @abstractmethod
    def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        pass

    @abstractmethod
    def delete(self, key: str) -> int:
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    def incr(self, key: str) -> int:
        pass

    @abstractmethod
    def decr(self, key: str) -> int:
        pass

    @abstractmethod
    def lpush(self, key: str, value: str) -> int:
        pass

    @abstractmethod
    def rpush(self, key: str, value: str) -> int:
        pass

    @abstractmethod
    def lpop(self, key: str) -> Optional[str]:
        pass

    @abstractmethod
    def rpop(self, key: str) -> Optional[str]:
        pass

    @abstractmethod
    def lrange(self, key: str, start: int, end: int) -> list:
        pass

    @abstractmethod
    def hset(self, key: str, field: str, value: str) -> int:
        pass

    @abstractmethod
    def hget(self, key: str, field: str) -> Optional[str]:
        pass

    @abstractmethod
    def hgetall(self, key: str) -> Dict[str, str]:
        pass


class EmailService(ExternalService):
    @abstractmethod
    def send_email(self, to: str, subject: str, body: str, html: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def send_batch_email(self, recipients: list, subject: str, body: str, html: Optional[str] = None) -> Dict[str, Any]:
        pass