from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseService(ABC):
    @abstractmethod
    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass


class FrontendService(BaseService):
    @abstractmethod
    def handle_user_message(self, user_id: str, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_session_history(self, user_id: str, session_id: str, limit: int = 20) -> Dict[str, Any]:
        pass

    @abstractmethod
    def create_session(self, user_id: str, session_name: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def list_sessions(self, user_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def update_session(self, user_id: str, session_id: str, session_name: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def delete_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def update_user_info(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def send_notification(self, user_id: str, message: str, type: str = "info") -> Dict[str, Any]:
        pass


class ExternalService(BaseService):
    pass