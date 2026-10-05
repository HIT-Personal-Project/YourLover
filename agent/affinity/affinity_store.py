"""好感度持久化存储：按用户保存好感度分数（0-100）。

SQLite 单表 `affinity_state(user_id PK, love_value, updated_at)`。
新用户初始好感度为 0（首次读取时惰性创建）。
与短期记忆（sessions.sqlite3）、用户画像（profiles.sqlite3）同放 data/memory 下。
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class AffinityStoreError(RuntimeError):
    """好感度存储在读取或写入失败时抛出。"""


class AffinityStore:
    """SQLite 好感度存储。

    核心职责：
        1. get_love：读取用户好感度，不存在时创建 0 分记录并返回 0；
        2. update_love：写入新好感度（调用方需自行保证 0-100）。
    """

    def __init__(
        self,
        database_path: str | Path | None = None,
        timeout: float = 5.0,
    ) -> None:
        """初始化存储。

        参数：
            database_path: SQLite 数据库路径，默认 data/memory/affinity.sqlite3。
            timeout: SQLite 锁等待秒数。
        """
        if database_path is None:
            database_path = (
                Path(__file__).resolve().parents[2] / "data" / "memory" / "affinity.sqlite3"
            )
        self.database_path = Path(database_path)
        self.timeout = float(timeout)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        """打开数据库连接并启用行工厂与 WAL。"""
        connection = sqlite3.connect(
            str(self.database_path),
            timeout=self.timeout,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _init_schema(self) -> None:
        """建表（幂等）。"""
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS affinity_state (
                    user_id     TEXT PRIMARY KEY,
                    love_value  INTEGER NOT NULL CHECK (love_value BETWEEN 0 AND 100),
                    updated_at  TEXT NOT NULL
                )
                """
            )

    def get_love(self, user_id: str) -> int:
        """读取用户好感度；不存在时惰性创建 0 分记录并返回 0。"""
        self._validate_user_id(user_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT love_value FROM affinity_state WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row is not None:
                return int(row["love_value"])
            # 新用户：初始好感度为 0
            connection.execute(
                """
                INSERT OR IGNORE INTO affinity_state (user_id, love_value, updated_at)
                VALUES (?, 0, ?)
                """,
                (user_id, self._now()),
            )
            return 0

    def update_love(self, user_id: str, value: int) -> int:
        """写入用户好感度（调用方需保证 0-100），返回写入后的值。"""
        self._validate_user_id(user_id)
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("value must be an int")
        if not 0 <= value <= 100:
            raise ValueError("value must be between 0 and 100")
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO affinity_state (user_id, love_value, updated_at) VALUES (?, 0, ?)",
                (user_id, self._now()),
            )
            connection.execute(
                """
                UPDATE affinity_state
                SET love_value = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (value, self._now(), user_id),
            )
            return value

    @staticmethod
    def _now() -> str:
        """当前 UTC 时间 ISO 字符串。"""
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _validate_user_id(user_id: str) -> None:
        """校验 user_id 非空字符串。"""
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must not be empty")


__all__ = ["AffinityStore", "AffinityStoreError"]
