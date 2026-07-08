from __future__ import annotations

import json
import os
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from app.memory.schema import (
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
    """Raised when the file-backed memory store cannot load or save data."""


MemoryObject = SemanticMemory | EpisodicMemory | ProceduralCandidate


class FileMemoryStore:
    def __init__(self, root_dir: str | Path | None = None) -> None:
        if root_dir is None:
            root_dir = Path(__file__).resolve().parents[2] / "data" / "memory" / "users"
        self.root_dir = Path(root_dir)

    def load_user_memory(self, user_id: str) -> UserMemoryFile:
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
        memory_file = self.load_user_memory(user_id)
        memory_object = self._coerce_memory(memory, user_id)
        self._list_for(memory_file, memory_object.type).append(memory_object)
        self.save_user_memory(memory_file)
        return memory_object.id

    def update_memory(self, user_id: str, memory_id: str, updates: dict[str, Any]) -> bool:
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
        return self.update_memory(user_id, memory_id, {"status": MemoryStatus.DELETED.value})

    def list_memories(
        self,
        user_id: str,
        memory_type: str | MemoryType | None = None,
        include_deleted: bool = False,
    ) -> list[MemoryObject]:
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
        self._validate_user_id(user_id)
        root = self.root_dir.resolve()
        path = (root / f"{user_id}.json").resolve()
        if path.parent != root:
            raise ValueError(f"Invalid user_id for memory file: {user_id!r}")
        return path

    def _validate_user_id(self, user_id: str) -> None:
        if not user_id or user_id.strip() != user_id:
            raise ValueError("user_id must be a non-empty file-safe string")
        forbidden = set('/\\:*?"<>|')
        if user_id in {".", ".."} or any(char in forbidden for char in user_id):
            raise ValueError(f"user_id contains path or filename separators: {user_id!r}")

    def _coerce_memory(self, memory: MemoryObject | dict[str, Any], user_id: str) -> MemoryObject:
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
        if memory_type is None:
            raise ValueError("memory_type is required")
        if isinstance(memory_type, MemoryType):
            return memory_type
        return MemoryType(memory_type)

    def _list_for(self, memory_file: UserMemoryFile, memory_type: MemoryType) -> list[MemoryObject]:
        if memory_type == MemoryType.SEMANTIC:
            return memory_file.semantic_memories
        if memory_type == MemoryType.EPISODIC:
            return memory_file.episodic_memories
        if memory_type == MemoryType.PROCEDURAL:
            return memory_file.procedural_candidates
        raise ValueError(f"Unsupported memory type: {memory_type!r}")

    def _find_memory(self, memory_file: UserMemoryFile, memory_id: str) -> MemoryObject | None:
        for memory in self.list_memories_in_file(memory_file, include_deleted=True):
            if memory.id == memory_id:
                return memory
        return None

    def list_memories_in_file(
        self,
        memory_file: UserMemoryFile,
        include_deleted: bool = False,
    ) -> list[MemoryObject]:
        memories: list[MemoryObject] = [
            *memory_file.semantic_memories,
            *memory_file.episodic_memories,
            *memory_file.procedural_candidates,
        ]
        if include_deleted:
            return memories
        return [memory for memory in memories if memory.status != MemoryStatus.DELETED]
