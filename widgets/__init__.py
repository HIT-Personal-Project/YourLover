"""
widgets 包
提供所有可复用的 UI 组件，按功能分为 base、menu、chat、settings 四个子包。
"""

from widgets.base import BaseWidget, ExtensibleItem, ItemPayload
from widgets.menu import ContextMenu, MenuBuilder, MenuItem, MenuItemType
from widgets.chat import ChatBubble, ChatHeader, ChatHistory, ChatInput, MessageRole
from widgets.settings import (
    OptionSettingItem,
    SettingItem,
    SettingPanel,
    SliderSettingItem,
    TextSettingItem,
    ToggleSettingItem,
)

__all__ = [
    # base
    "BaseWidget",
    "ExtensibleItem",
    "ItemPayload",
    # menu
    "ContextMenu",
    "MenuBuilder",
    "MenuItem",
    "MenuItemType",
    # chat
    "ChatBubble",
    "ChatHeader",
    "ChatHistory",
    "ChatInput",
    "MessageRole",
    # settings
    "SettingItem",
    "ToggleSettingItem",
    "TextSettingItem",
    "SliderSettingItem",
    "OptionSettingItem",
    "SettingPanel",
]
