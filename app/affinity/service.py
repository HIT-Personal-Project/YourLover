from __future__ import annotations

from threading import Lock

from affinity.schema import AffinityEvent


# MVP 阶段默认返回的固定好感度快照值（0-100）
DEFAULT_LOVE_SNAPSHOT = 77


class AffinityService:
    """权威好感度系统的可替换 MVP 边界。

    该存根实现的核心逻辑：
        1. get_love_snapshot 始终返回固定的好感度快照（默认 77），不真正计算分数。
        2. emit_affinity_event 将交互事件保存到内存列表，供后续处理消费。
    设计上刻意不读写 memory 模块数据，也不实现真实的好感度评分逻辑，
    以便后续用真正的 affinity 实现替换该存根而不影响其它模块。
    """

    def __init__(self, default_love_snapshot: int = DEFAULT_LOVE_SNAPSHOT) -> None:
        """初始化好感度服务。

        参数：
            default_love_snapshot: 默认好感度快照值，必须为 0-100 之间的整数。
        """
        # 拒绝 bool（Python 中 bool 是 int 的子类，需单独拦截）
        if isinstance(default_love_snapshot, bool) or not isinstance(
            default_love_snapshot, int
        ):
            raise TypeError("default_love_snapshot must be an int")
        if not 0 <= default_love_snapshot <= 100:
            raise ValueError("default_love_snapshot must be between 0 and 100")
        self._default_love_snapshot = default_love_snapshot
        self._events: list[AffinityEvent] = []
        # 事件列表的并发锁，保证多线程 emit/get_events 安全
        self._events_lock = Lock()

    def get_love_snapshot(self, user_id: str) -> int:
        """返回指定用户的好感度快照。

        MVP 阶段直接返回固定的默认值，不依赖 user_id 做差异化计算。
        """
        _require_user_id(user_id)
        return self._default_love_snapshot

    def emit_affinity_event(self, user_id: str, event: dict) -> None:
        """记录一次交互事件到内存列表。

        参数：
            user_id: 触发事件的用户
            event: 事件负载字典
        事件被包装为不可变的 AffinityEvent 后追加到内存列表，线程安全。
        """
        recorded_event = AffinityEvent(user_id=user_id, event=event)
        with self._events_lock:
            self._events.append(recorded_event)

    def get_events(self, user_id: str | None = None) -> tuple[AffinityEvent, ...]:
        """返回已记录事件的不可变快照。

        参数：
            user_id: 若提供则只返回该用户的事件；若为 None 则返回全部事件。
        返回值为新建的 AffinityEvent 元组，与内部列表解耦，调用方可安全持有。
        """

        if user_id is not None:
            _require_user_id(user_id)
        with self._events_lock:
            # 拷贝出新的 AffinityEvent 对象，避免调用方通过引用修改内部数据
            events = tuple(
                AffinityEvent(
                    user_id=item.user_id,
                    event=item.event,
                    created_at=item.created_at,
                )
                for item in self._events
            )
        if user_id is None:
            return events
        return tuple(item for item in events if item.user_id == user_id)


def _require_user_id(user_id: str) -> None:
    """校验 user_id：必须是非空字符串，否则抛出 ValueError。"""
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id must not be empty")
