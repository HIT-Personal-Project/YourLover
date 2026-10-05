"""动态长期记忆管理器：候选提取、持久化与检索的统一入口。

动态长期记忆负责"跨 Session 的可召回信息"，分为三类：
    - semantic（语义记忆）：偏好、当前状态、事实陈述；
    - episodic（情节记忆）：一次"问题-行动-结果"对话的摘要；
    - procedural（程序性候选）：用户给出的未来交互规则（需确认后生效）。

主路径（新增）：LLM 提炼条目 → Chroma 向量存储 + 向量检索（带日期）；
降级路径：LLM/Chroma 不可用时回退到规则分类器（JSON）+ 关键词检索。

内部组合：
    - VectorMemoryStore（Chroma 向量存储，主路径）
    - FileMemoryStore（JSON 存储，降级路径）
    - MemoryClassifier（规则候选提取，降级路径）
    - MemoryRetriever（关键词检索，降级路径）
调用方（ChatAgent / 测试）只需面向本类。

用户画像不属于动态长期记忆，请使用 UserProfileManager。
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from agent.memory.classifier import MemoryClassifier
from agent.memory.llm_extractor import LLMMemoryEntry
from agent.memory.retriever import MemoryRetriever
from agent.memory.schema import (
    EpisodicMemory,
    MemoryType,
    SemanticMemory,
)
from agent.memory.store import FileMemoryStore, MemoryObject, MemoryStoreError
from agent.memory.vector_memory_store import VectorMemoryStore, VectorStoreError
from agent.memory.window import Message

logger = logging.getLogger(__name__)


class LongTermMemory:
    """动态长期记忆管理类：对外暴露动态记忆的读、写、检索能力。

    职责边界：
        1. 每轮检索：主走向量召回（带日期格式化），失败降级关键词召回，
           并格式化为可注入 system prompt 的字符串；
        2. 每轮写入：LLM 提炼条目主写向量库，失败降级写 JSON；
           规则候选（write_candidates）作为 LLM 提取失败的兜底；
        3. CRUD：单条记忆的增删改查（供维护、UI、调试使用）。

    不负责：
        - 短期窗口裁剪与会话摘要（见 ShortTermMemory / ChatAgent）；
        - 用户画像及其候选流程（见 UserProfileManager）；
        - LLM 合并提取本身（见 LLMMemoryExtractor）。
    """

    def __init__(
        self,
        store: FileMemoryStore | None = None,
        classifier: MemoryClassifier | None = None,
        retriever: MemoryRetriever | None = None,
        root_dir: str | Path | None = None,
        *,
        vector_store: VectorMemoryStore | None = None,
        preference_top_k: int = 20,
    ) -> None:
        """初始化长期记忆管理器。

        参数：
            store: 已构造的 FileMemoryStore；传入时忽略 root_dir。
            classifier: 候选分类器，默认规则实现 MemoryClassifier（降级路径）。
            retriever: 检索器，默认基于 store 创建（降级路径）。
            root_dir: 每用户 JSON 记忆文件根目录，默认 data/memory/users。
            vector_store: Chroma 向量存储；为 None 时全部走 JSON+关键词降级。
            preference_top_k: 偏好召回时最多检查的语义记忆条数（降级路径）。
        """
        self.store = store if store is not None else FileMemoryStore(root_dir)
        self.classifier = classifier if classifier is not None else MemoryClassifier()
        self.retriever = retriever if retriever is not None else MemoryRetriever(self.store)
        self.vector_store = vector_store  # 主路径；None 时走降级
        self.preference_top_k = preference_top_k  # 偏好召回的扫描上限

    # ------------------------------------------------------------------
    # 检索（每轮调用）
    # ------------------------------------------------------------------

    def retrieve(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[MemoryObject]:
        """按当前用户输入检索相关记忆（降级路径：关键词，相关度降序）。"""
        return self.retriever.retrieve_memories(user_id, query, top_k=top_k)

    def retrieve_context(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
    ) -> str:
        """检索并格式化本轮的长期记忆上下文字符串（直接注入 system prompt）。

        主路径：Chroma 向量召回（每条带日期，语义相似）；
        降级路径：关键词 + 偏好无条件召回（见 _legacy_retrieve_context）。
        主路径失败（Chroma 不可用、Ollama 未启动等）时自动降级，
        不中断聊天。
        """
        if self.vector_store is not None:
            try:
                entries = self.vector_store.search(user_id, query, top_k=top_k)
                return self.vector_store.format_context(entries)
            except VectorStoreError as exc:
                logger.warning("向量检索失败，已降级为关键词检索：%s", exc)
        return self._legacy_retrieve_context(user_id, query, top_k)

    def _legacy_retrieve_context(
        self,
        user_id: str,
        query: str,
        top_k: int,
    ) -> str:
        """降级检索：关键词召回 + 用户稳定偏好无条件召回（保"回答要简短"这类偏好）。"""
        recalled = self.retrieve(user_id, query, top_k=top_k)
        preferences = [
            item
            for item in self.retriever.retrieve_memories(
                user_id, "", memory_type=MemoryType.SEMANTIC, top_k=self.preference_top_k
            )
            if isinstance(item, SemanticMemory) and item.scope == "preference"
        ]
        merged = _unique_memories([*preferences, *recalled])[:top_k]
        return self.retriever.format_memory_context(merged)

    # ------------------------------------------------------------------
    # 写入（每轮调用）
    # ------------------------------------------------------------------

    def write_llm_memories(
        self,
        user_id: str,
        memories: Sequence[LLMMemoryEntry],
        session_id: str | None = None,
    ) -> list[str]:
        """写入 LLM 提炼的长期记忆条目，返回条目 ID 列表。

        主路径：写入 Chroma（向量化，系统盖章日期）；
        降级：Chroma 不可用时把条目作为语义记忆写入 JSON，关键词可检索。
        空条目列表直接返回 []，不产生任何写入。
        """
        if not memories:
            return []

        if self.vector_store is not None:
            try:
                return self.vector_store.add_entries(user_id, list(memories), session_id)
            except VectorStoreError as exc:
                logger.warning("向量写入失败，已降级为 JSON 写入：%s", exc)

        # 降级：作为语义记忆写入 JSON，便于关键词检索
        ids: list[str] = []
        for entry in memories:
            memory = SemanticMemory(
                user_id=user_id,
                scope="fact",
                content=entry.content,
                predicate="fact",
                object=entry.content,
                confidence=1.0,
                importance=0.8,
                tags=[entry.memory_type],
            )
            ids.append(self.store.add_memory(user_id, memory))
        return ids

    def write_candidates(
        self,
        messages: Sequence[Message] | list[Any],
        user_id: str,
        love_snapshot: int | None = None,
    ) -> list[str]:
        """从消息列表提取长期记忆候选并持久化（规则降级路径），返回写入的记忆 ID。

        写入流程：
            1. 语义记忆：按 (scope, content) 与已有记忆去重后写入；
            2. 程序性候选：直接追加（默认需用户确认后生效）；
            3. 情节记忆：仅当消息构成完整"问题-行动-结果"时生成一条。
        """
        memory_ids: list[str] = []

        # 语义记忆：与已存在记忆按 (scope, content) 去重
        for memory in self.classifier.extract_semantic_memories(messages, user_id):
            if not self._semantic_exists(user_id, memory):
                memory_ids.append(self.store.add_memory(user_id, memory))

        # 程序性候选：直接追加（默认需用户确认）
        for memory in self.classifier.extract_procedural_candidates(messages, user_id):
            memory_ids.append(self.store.add_memory(user_id, memory))

        # 情节记忆：仅当构成完整"问题-行动-结果"时生成
        episode = self.classifier.summarize_episodic_memory(
            messages, user_id, love_snapshot=love_snapshot
        )
        if episode is not None:
            memory_ids.append(self.store.add_memory(user_id, episode))

        return memory_ids

    def _semantic_exists(self, user_id: str, candidate: SemanticMemory) -> bool:
        """判断用户已有的语义记忆中是否已存在相同 (scope, content) 的记忆。"""
        return any(
            isinstance(item, SemanticMemory)
            and item.scope == candidate.scope
            and item.content == candidate.content
            for item in self.store.list_memories(user_id, MemoryType.SEMANTIC)
        )

    # ------------------------------------------------------------------
    # CRUD（供维护、UI、调试使用）
    # ------------------------------------------------------------------

    def add(self, user_id: str, memory: MemoryObject | dict[str, Any]) -> str:
        """手动追加一条记忆（对象或字典），返回新记忆 ID。"""
        return self.store.add_memory(user_id, memory)

    def update(self, user_id: str, memory_id: str, updates: dict[str, Any]) -> bool:
        """按 ID 更新一条记忆的指定字段；找不到返回 False。"""
        return self.store.update_memory(user_id, memory_id, updates)

    def delete(self, user_id: str, memory_id: str) -> bool:
        """软删除一条记忆（status 置为 DELETED，数据保留）。"""
        return self.store.delete_memory(user_id, memory_id)

    def list(
        self,
        user_id: str,
        memory_type: str | MemoryType | None = None,
        include_deleted: bool = False,
    ) -> list[MemoryObject]:
        """列出用户的记忆；可按类型过滤，默认排除已删除项。"""
        return self.store.list_memories(user_id, memory_type, include_deleted)

    # ------------------------------------------------------------------
    # 便捷属性（供测试与调试）
    # ------------------------------------------------------------------

    @property
    def root_dir(self) -> Path:
        """每用户 JSON 记忆文件的根目录。"""
        return self.store.root_dir

    @property
    def error_type(self) -> type[MemoryStoreError]:
        """暴露存储异常类型，供调用方按需捕获。"""
        return MemoryStoreError

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        return f"LongTermMemory(root_dir={str(self.root_dir)!r})"


def _unique_memories(memories: Iterable[MemoryObject]) -> list[MemoryObject]:
    """按记忆 id 去重，保留首次出现的顺序（合并偏好召回与相关召回时使用）。"""
    unique: list[MemoryObject] = []
    seen: set[str] = set()
    for memory in memories:
        memory_id = str(getattr(memory, "id", id(memory)))
        if memory_id not in seen:
            unique.append(memory)
            seen.add(memory_id)
    return unique


__all__ = [
    "LongTermMemory",
    "FileMemoryStore",
    "MemoryClassifier",
    "MemoryRetriever",
    "MemoryStoreError",
    "VectorMemoryStore",
    "VectorStoreError",
    "SemanticMemory",
    "EpisodicMemory",
    "MemoryType",
    "MemoryObject",
]
