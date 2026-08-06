import json
import os
from typing import Any, Callable, Dict, List

class ConfigManager:
    def __init__(self, config_path: str = "config.json"):
        self._config_path = config_path
        self._data: Dict[str, Any] = {}
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []
        self._load()

    def _load(self):
        """从 JSON 加载"""
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except FileNotFoundError as e:
            print(f"Config file not found: {e}")
            

    def _save(self):
        """写回 JSON 文件"""
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    # -- 属性访问，保持 settings.CHAT_MODEL_NAME 用法 --
    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(f"Config has no key '{name}'")

    # -- 修改并通知 --
    def update(self, new_values: Dict[str, Any], save: bool = True):
        """
        批量更新配置项。
        """
        self._data.update(new_values)
        if save:
            self._save()



# 全局单例，替代原来的 settings
config = ConfigManager("config.json")