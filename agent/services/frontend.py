from abc import abstractmethod
from typing import Any, Dict, List, Optional
from .base import FrontendService


class ChatService(FrontendService):
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


class UserService(FrontendService):
    @abstractmethod
    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def update_user_info(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def login_user(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def logout_user(self, user_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def authenticate_token(self, token: str) -> Dict[str, Any]:
        pass


class NotificationService(FrontendService):
    @abstractmethod
    def send_notification(self, user_id: str, message: str, type: str = "info") -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_notifications(self, user_id: str, limit: int = 10) -> Dict[str, Any]:
        pass

    @abstractmethod
    def mark_notification_read(self, user_id: str, notification_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def delete_notification(self, user_id: str, notification_id: str) -> Dict[str, Any]:
        pass


class SessionService(FrontendService):
    @abstractmethod
    def create_session(self, user_id: str, session_name: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def list_sessions(self, user_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def update_session(self, user_id: str, session_id: str, session_name: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def delete_session(self, user_id: str, session_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def clear_session_history(self, user_id: str, session_id: str) -> Dict[str, Any]:
        pass