"""
widgets/base 包
提供所有可复用组件的抽象基类与扩展接口。
"""

from widgets.base.base_widget import BaseWidget
from widgets.base.extensible_item import ExtensibleItem, ItemPayload

__all__ = ["BaseWidget", "ExtensibleItem", "ItemPayload"]
