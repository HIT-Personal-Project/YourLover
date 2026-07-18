"""
窗口模块
包含所有GUI窗口组件（PetWindow、ChatWindow、SettingWindow）
"""

from windows.avatar_controller_protocol import AvatarControllerProtocol
from windows.base_window import BaseWindow
from windows.lover_window import LoverWindow
from windows.chat_window import ChatWindow
from windows.setting_window import SettingWindow
from windows.window_manager import WindowManager

__all__ = [
    "AvatarControllerProtocol",
    "BaseWindow",
    "LoverWindow",
    "ChatWindow",
    "SettingWindow",
    "WindowManager",
]
