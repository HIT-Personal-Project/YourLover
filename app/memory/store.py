"""基于文件的用户记忆存储。

该模块提供 FileMemoryStore，以 JSON 文件形式按用户维度持久化长期记忆。
每个用户对应一个 `{user_id}.json` 文件，存放语义/情节/程序性三类记忆。

写入采用"临时文件 + os.replace"的原子替换策略，避免并发写入导致文件损坏；
读取时校验 user_id 一致性与 schema 合法性，保证数据完整。
"""

from __future__ import annotations

import json
import os
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from memory.schema import (
    EpisodicMemory,
    MemoryEvidence,
    MemoryStatus,
    MemoryType,
    ProceduralCandidate,
    SemanticMemory,
    UserMemoryFile,
    now_iso,
)


class MemoryStoreError(RuntimeError):
    """文件记忆存储在加载或保存数据失败时抛出。"""


# 存储支持的记忆对象联合类型
MemoryObject = SemanticMemory | EpisodicMemory | ProceduralCandidate


class FileMemoryStore:
    """按用户维度持久化记忆的文件存储。

    核心职责：
        1. load_user_memory：读取用户记忆文件，不存在则创建空文件。
        2. save_user_memory：原子写入用户记忆文件（临时文件 + rename）。
        3. add_memory / update_memory / delete_memory / list_memories：CRUD 操作。

    路径安全：通过 _path_for_user 校验 user_id 不会逃逸出 root_dir，
    避免路径穿越攻击。
    """

    def __init__(self, root_dir: str | Path | None = None) -> None:
        """初始化存储根目录。

        参数：
            root_dir: 记忆文件存放根目录，默认为项目 data/memory/users。
        """
        if root_dir is None:
            root_dir = Path(__file__).resolve().parents[2] / "data" / "memory" / "users"
        self.root_dir = Path(root_dir)

    def load_user_memory(self, user_id: str) -> UserMemoryFile:
        """加载指定用户的记忆文件。

        逻辑：
            - 文件不存在时创建空文件并返回。
            - 文件存在但 JSON 解析失败、user_id 不匹配或 schema 非法时
              抛出 MemoryStoreError，避免脏数据被静默使用。
        """
        path = self._path_for_user(user_id)
        if not path.exists():
            memory_file = UserMemoryFile(user_id=user_id)
            self.save_user_memory(memory_file)
            return memory_file

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except JSONDecodeError as exc:
            raise MemoryStoreError(f"Memory file is not valid JSON: {path}") from exc
        except OSError as exc:
            raise MemoryStoreError(f"Failed to read memory file: {path}") from exc

        if payload.get("user_id") != user_id:
            raise MemoryStoreError(
                f"Memory file user_id mismatch: expected {user_id!r}, got {payload.get('user_id')!r}"
            )

        try:
            return UserMemoryFile.from_dict(payload)
        except (KeyError, TypeError, ValueError) as exc:
            raise MemoryStoreError(f"Memory file has invalid schema: {path}") from exc

    def save_user_memory(self, memory_file: UserMemoryFile) -> None:
        """原子写入用户记忆文件。

        采用"先写临时文件再 os.replace"的策略：
            1. 刷新 updated_at 与索引；
            2. 序列化为 JSON 写入 `.{name}.{pid}.tmp` 临时文件；
            3. os.replace 原子替换原文件（跨平台原子操作）；
            4. 写入失败时清理临时文件并抛出 MemoryStoreError。
        """
        path = self._path_for_user(memory_file.user_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        memory_file.updated_at = now_iso()
        memory_file.refresh_index()
        payload = json.dumps(memory_file.to_dict(), ensure_ascii=False, indent=2)
        temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")

        try:
            temp_path.write_text(payload + "\n", encoding="utf-8")
            os.replace(temp_path, path)
        except OSError as exc:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise MemoryStoreError(f"Failed to save memory file: {path}") from exc

    def add_memory(self, user_id: str, memory: MemoryObject | dict[str, Any]) -> str:
        """向用户记忆文件追加一条记忆并持久化。

        参数：
            user_id: 目标用户
            memory: 记忆对象或字典（dict 会按 type 字段还原为对应 dataclass）
        返回新增记忆的 ID。
        """
        memory_file = self.load_user_memory(user_id)
        memory_object = self._coerce_memory(memory, user_id)
        self._list_for(memory_file, memory_object.type).append(memory_object)
        self.save_user_memory(memory_file)
        return memory_object.id

    def update_memory(self, user_id: str, memory_id: str, updates: dict[str, Any]) -> bool:
        """按 ID 更新一条记忆的指定字段。

        逻辑：
            - id/user_id/type/created_at 等不可变字段被忽略；
            - status 字段会被强制转为 MemoryStatus；
            - evidence 若为 dict 会被还原为 MemoryEvidence；
            - 更新后刷新 updated_at 并持久化。
        返回是否找到并更新了对应记忆。
        """
        memory_file = self.load_user_memory(user_id)
        memory = self._find_memory(memory_file, memory_id)
        if memory is None:
            return False

        for key, value in updates.items():
            if key in {"id", "user_id", "type", "created_at"}:
                continue
            if not hasattr(memory, key):
                raise ValueError(f"Unknown memory field: {key}")
            if key == "status":
                value = MemoryStatus(value)
            elif key == "evidence" and isinstance(value, dict):
                value = MemoryEvidence.from_dict(value)
            setattr(memory, key, value)

        memory.updated_at = now_iso()
        self.save_user_memory(memory_file)
        return True

    def delete_memory(self, user_id: str, memory_id: str) -> bool:
        """软删除一条记忆（将 status 置为 DELETED），不真正移除数据。"""
        return self.update_memory(user_id, memory_id, {"status": MemoryStatus.DELETED.value})

    def list_memories(
        self,
        user_id: str,
        memory_type: str | MemoryType | None = None,
        include_deleted: bool = False,
    ) -> list[MemoryObject]:
        """列出用户的记忆。

        参数：
            user_id: 目标用户
            memory_type: 指定类型则只返回该类型，None 返回全部三类
            include_deleted: 是否包含已软删除的记忆，默认排除
        """
        memory_file = self.load_user_memory(user_id)
        lists = (
            [self._list_for(memory_file, self._memory_type(memory_type))]
            if memory_type is not None
            else [
                memory_file.semantic_memories,
                memory_file.episodic_memories,
                memory_file.procedural_candidates,
            ]
        )
        memories = [memory for memory_list in lists for memory in memory_list]
        if include_deleted:
            return memories
        return [memory for memory in memories if memory.status != MemoryStatus.DELETED]

    def _path_for_user(self, user_id: str) -> Path:
        """计算用户记忆文件路径，并校验 user_id 不会逃逸出 root_dir。"""
        self._validate_user_id(user_id)
        root = self.root_dir.resolve()
        path = (root / f"{user_id}.json").resolve()
        # 防止路径穿越：解析后的父目录必须仍是 root
        if path.parent != root:
            raise ValueError(f"Invalid user_id for memory file: {user_id!r}")
        return path

    def _validate_user_id(self, user_id: str) -> None:
        """校验 user_id 是文件安全的字符串：非空、不含路径分隔符与特殊字符。"""
        if not user_id or user_id.strip() != user_id:
            raise ValueError("user_id must be a non-empty file-safe string")
        forbidden = set('/\\:*?"<>|')
        if user_id in {".", ".."} or any(char in forbidden for char in user_id):
            raise ValueError(f"user_id contains path or filename separators: {user_id!r}")

    def _coerce_memory(self, memory: MemoryObject | dict[str, Any], user_id: str) -> MemoryObject:
        """将传入的记忆归一化为 dataclass 实例，并校验 user_id 一致。

        - 已是 dataclass 实例：直接使用；
        - dict：按 type 字段还原为对应记忆类型；
        - 其它类型：抛出 TypeError。
        user_id 不匹配时抛出 ValueError，防止串号写入。
        """
        if isinstance(memory, (SemanticMemory, EpisodicMemory, ProceduralCandidate)):
            memory_object = memory
        elif isinstance(memory, dict):
            payload = dict(memory)
            payload.setdefault("user_id", user_id)
            memory_type = self._memory_type(payload.get("type"))
            if memory_type == MemoryType.SEMANTIC:
                memory_object = SemanticMemory.from_dict(payload)
            elif memory_type == MemoryType.EPISODIC:
                memory_object = EpisodicMemory.from_dict(payload)
            else:
                memory_object = ProceduralCandidate.from_dict(payload)
        else:
            raise TypeError(f"Unsupported memory object: {type(memory)!r}")

        if memory_object.user_id != user_id:
            raise ValueError(
                f"Memory user_id mismatch: expected {user_id!r}, got {memory_object.user_id!r}"
            )
        return memory_object

    def _memory_type(self, memory_type: str | MemoryType | None) -> MemoryType:
        """将字符串或 MemoryType 统一转换为 MemoryType，None 抛错。"""
        if memory_type is None:
            raise ValueError("memory_type is required")
        if isinstance(memory_type, MemoryType):
            return memory_type
        return MemoryType(memory_type)

    def _list_for(self, memory_file: UserMemoryFile, memory_type: MemoryType) -> list[MemoryObject]:
        """根据记忆类型返回 UserMemoryFile 中对应的列表引用，便于追加。"""
        if memory_type == MemoryType.SEMANTIC:
            return memory_file.semantic_memories
        if memory_type == MemoryType.EPISODIC:
            return memory_file.episodic_memories
        if memory_type == MemoryType.PROCEDURAL:
            return memory_file.procedural_candidates
        raise ValueError(f"Unsupported memory type: {memory_type!r}")

    def _find_memory(self, memory_file: UserMemoryFile, memory_id: str) -> MemoryObject | None:
        """在用户记忆文件中按 ID 查找记忆，找不到返回 None。"""
        for memory in self.list_memories_in_file(memory_file, include_deleted=True):
            if memory.id == memory_id:
                return memory
        return None

    def list_memories_in_file(
        self,
        memory_file: UserMemoryFile,
        include_deleted: bool = False,
    ) -> list[MemoryObject]:
        """合并用户记忆文件中的三类记忆并返回列表。

        与 list_memories 的区别：本方法直接基于已加载的 memory_file 操作，
        不再触发磁盘读取，用于 _find_memory 等内部场景。
        """
        memories: list[MemoryObject] = [
            *memory_file.semantic_memories,
            *memory_file.episodic_memories,
            *memory_file.procedural_candidates,
        ]
        if include_deleted:
            return memories
        return [memory for memory in memories if memory.status != MemoryStatus.DELETED]
