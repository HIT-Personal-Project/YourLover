from dataclasses import dataclass

import pytest

from app.memory.window import (
    select_messages_for_memory_write,
    should_trim,
    trim_messages,
)


@dataclass(frozen=True)
class Message:
    type: str
    content: str
    tool_call_id: str | None = None


def HumanMessage(content: str) -> Message:
    return Message(type="human", content=content)


def AIMessage(content: str) -> Message:
    return Message(type="ai", content=content)


def SystemMessage(content: str) -> Message:
    return Message(type="system", content=content)


def ToolMessage(content: str, tool_call_id: str) -> Message:
    return Message(type="tool", content=content, tool_call_id=tool_call_id)


def RemoveMessage(id: str) -> Message:
    return Message(type="remove", content=id)


def test_should_trim_only_when_messages_exceed_limit():
    messages = [HumanMessage(content="one"), AIMessage(content="two")]

    assert should_trim(messages, max_messages=2) is False
    assert should_trim(messages, max_messages=1) is True


def test_trim_messages_returns_original_when_under_limit():
    messages = [
        SystemMessage(content="You are helpful."),
        HumanMessage(content="Hello"),
        AIMessage(content="Hi"),
    ]

    retained, removed = trim_messages(messages, max_messages=3, keep_recent_turns=1)

    assert retained == messages
    assert removed == []


def test_trim_messages_keeps_leading_system_and_recent_turns():
    messages = [
        SystemMessage(content="System prompt"),
        HumanMessage(content="turn 1 user"),
        AIMessage(content="turn 1 ai"),
        HumanMessage(content="turn 2 user"),
        AIMessage(content="turn 2 ai"),
        HumanMessage(content="turn 3 user"),
        AIMessage(content="turn 3 ai"),
    ]

    retained, removed = trim_messages(messages, max_messages=5, keep_recent_turns=2)

    assert retained == [
        messages[0],
        messages[3],
        messages[4],
        messages[5],
        messages[6],
    ]
    assert removed == [messages[1], messages[2]]


def test_trim_messages_drops_oldest_retained_turns_to_respect_limit():
    messages = [
        SystemMessage(content="System prompt"),
        HumanMessage(content="turn 1 user"),
        AIMessage(content="turn 1 ai"),
        HumanMessage(content="turn 2 user"),
        AIMessage(content="turn 2 ai"),
        HumanMessage(content="turn 3 user"),
        AIMessage(content="turn 3 ai"),
    ]

    retained, removed = trim_messages(messages, max_messages=3, keep_recent_turns=3)

    assert retained == [messages[0], messages[5], messages[6]]
    assert removed == [messages[1], messages[2], messages[3], messages[4]]


def test_trim_messages_keeps_tool_turn_together():
    messages = [
        SystemMessage(content="System prompt"),
        HumanMessage(content="old user"),
        AIMessage(content="old ai"),
        HumanMessage(content="new user"),
        AIMessage(content="searching"),
        ToolMessage(content="sunny", tool_call_id="call_1"),
        AIMessage(content="It is sunny."),
    ]

    retained, removed = trim_messages(messages, max_messages=4, keep_recent_turns=1)

    assert retained == [messages[0], messages[3], messages[4], messages[5], messages[6]]
    assert removed == [messages[1], messages[2]]


def test_select_messages_for_memory_write_filters_control_messages():
    removed = [
        SystemMessage(content="System prompt"),
        HumanMessage(content="remember this"),
        AIMessage(content="ok"),
        RemoveMessage(id="old-message-id"),
    ]

    selected = select_messages_for_memory_write(removed)

    assert selected == [removed[1], removed[2]]


def test_trim_messages_validates_arguments():
    with pytest.raises(ValueError, match="max_messages"):
        should_trim([], max_messages=0)

    with pytest.raises(ValueError, match="keep_recent_turns"):
        trim_messages([HumanMessage(content="hi")], max_messages=1, keep_recent_turns=-1)
