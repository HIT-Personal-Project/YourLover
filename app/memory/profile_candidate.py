"""用户画像候选数据模型。

ProfileCandidate 表示一个待应用的画像字段更新建议，
本身不直接修改用户画像，需由其它子系统（如画像服务）消费并落地。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from memory.schema import MemoryEvidence, now_iso


@dataclass
class ProfileCandidate:
    """用户画像更新候选：一个待应用的画像字段更新建议。

    该类只描述"想更新哪个字段、更新成什么值、为什么"，不直接修改画像。
    needs_user_confirmation 为 True 时必须经用户确认后才可落地。

    字段：
        user_id: 目标用户
        field: 画像字段名（如 nickname/name/identity/inferred_preference）
        value: 字段目标值
        reason: 更新理由（人类可读）
        needs_user_confirmation: 是否需要用户确认，默认 False
        confidence: 候选置信度 0~1
        evidence: 记忆证据（来源消息）
        created_at: 创建时间
    """

    user_id: str
    field: str
    value: str
    reason: str
    needs_user_confirmation: bool = False
    confidence: float = 1.0
    evidence: MemoryEvidence = field(default_factory=MemoryEvidence)
    created_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        """初始化后处理：若 evidence 为 dict 则还原为 MemoryEvidence 实例。"""
        if isinstance(self.evidence, dict):
            self.evidence = MemoryEvidence.from_dict(self.evidence)

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "user_id": self.user_id,
            "field": self.field,
            "value": self.value,
            "reason": self.reason,
            "needs_user_confirmation": self.needs_user_confirmation,
            "confidence": self.confidence,
            "evidence": self.evidence.to_dict(),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProfileCandidate":
        """从字典反序列化，缺失字段使用默认值。"""
        return cls(
            user_id=data["user_id"],
            field=data["field"],
            value=data["value"],
            reason=data["reason"],
            needs_user_confirmation=bool(data.get("needs_user_confirmation", False)),
            confidence=float(data.get("confidence", 1.0)),
            evidence=MemoryEvidence.from_dict(data.get("evidence")),
            created_at=data.get("created_at") or now_iso(),
        )
