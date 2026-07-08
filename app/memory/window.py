from __future__ import annotations

from collections.abc import Sequence
from typing import TypeAlias


Message: TypeAlias = object
MessageList: TypeAlias = list[Message]
IndexedGroup: TypeAlias = list[tuple[int, Message]]


def should_trim(messages: Sequence[Message], max_messages: int) -> bool:
    """Return whether a message list has crossed the short-term window limit."""
    _validate_max_messages(max_messages)
    return len(messages) > max_messages


def trim_messages(
    messages: Sequence[Message],
    max_messages: int,
    keep_recent_turns: int,
) -> tuple[MessageList, MessageList]:
    """Keep leading system prompts and the newest complete conversation turns.

    A conversation turn starts with a HumanMessage and includes following AI/tool
    messages until the next HumanMessage. Trimming by turns keeps tool results
    attached to the assistant message that requested them.
    """
    _validate_max_messages(max_messages)
    if keep_recent_turns < 0:
        raise ValueError("keep_recent_turns must be greater than or equal to 0")

    original = list(messages)
    if not should_trim(original, max_messages):
        return original, []

    pinned_count = _leading_system_count(original)
    pinned_indices = set(range(pinned_count))
    groups = _conversation_groups(original, start_index=pinned_count)
    retained_groups = groups[-keep_recent_turns:] if keep_recent_turns else []

    retained_indices = set(pinned_indices)
    for group in retained_groups:
        retained_indices.update(index for index, _ in group)

    while len(retained_indices) > max_messages and len(retained_groups) > 1:
        dropped_group = retained_groups.pop(0)
        for index, _ in dropped_group:
            retained_indices.discard(index)

    retained = [message for index, message in enumerate(original) if index in retained_indices]
    removed = [message for index, message in enumerate(original) if index not in retained_indices]
    return retained, removed


def select_messages_for_memory_write(removed_messages: Sequence[Message]) -> MessageList:
    """Return trimmed conversation messages that can feed long-term classifiers."""
    return [
        message
        for message in removed_messages
        if not (_is_system_message(message) or _is_remove_message(message))
    ]


def _validate_max_messages(max_messages: int) -> None:
    if max_messages < 1:
        raise ValueError("max_messages must be greater than or equal to 1")


def _leading_system_count(messages: Sequence[Message]) -> int:
    count = 0
    for message in messages:
        if not _is_system_message(message):
            break
        count += 1
    return count


def _conversation_groups(
    messages: Sequence[Message],
    start_index: int,
) -> list[IndexedGroup]:
    groups: list[IndexedGroup] = []
    current_group: IndexedGroup = []

    for index in range(start_index, len(messages)):
        message = messages[index]
        if _is_human_message(message) and current_group:
            groups.append(current_group)
            current_group = []
        current_group.append((index, message))

    if current_group:
        groups.append(current_group)

    return groups


def _is_human_message(message: Message) -> bool:
    return _message_kind(message) == "human" or message.__class__.__name__ == "HumanMessage"


def _is_system_message(message: Message) -> bool:
    return _message_kind(message) == "system" or message.__class__.__name__ == "SystemMessage"


def _is_remove_message(message: Message) -> bool:
    return _message_kind(message) == "remove" or message.__class__.__name__ == "RemoveMessage"


def _message_kind(message: Message) -> str | None:
    kind = getattr(message, "type", None)
    if isinstance(kind, str):
        return kind
    return None
