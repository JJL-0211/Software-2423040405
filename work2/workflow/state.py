"""Workflow state management and inter-agent message passing."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentMessage:
    sender: str
    receiver: str
    content: Any
    msg_type: str
    timestamp: float = field(default_factory=time.time)

    def __repr__(self) -> str:
        return f"[{self.msg_type}] {self.sender} -> {self.receiver}"


class WorkflowState:
    """Shared blackboard — agents read/write data and send messages here."""

    def __init__(self, initial_data: dict | None = None):
        self._data: dict[str, Any] = dict(initial_data or {})
        self._messages: list[AgentMessage] = []
        self._current_step: int = 0
        self._round: int = 0

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def update(self, mapping: dict) -> None:
        self._data.update(mapping)

    @property
    def data(self) -> dict:
        return dict(self._data)

    def send_message(self, sender: str, receiver: str, content: Any, msg_type: str = "data") -> AgentMessage:
        msg = AgentMessage(sender=sender, receiver=receiver, content=content, msg_type=msg_type)
        self._messages.append(msg)
        return msg

    def get_messages(self, receiver: str | None = None, msg_type: str | None = None) -> list[AgentMessage]:
        result = self._messages
        if receiver is not None:
            result = [m for m in result if m.receiver in (receiver, "ALL")]
        if msg_type is not None:
            result = [m for m in result if m.msg_type == msg_type]
        return result

    @property
    def messages(self) -> list[AgentMessage]:
        return list(self._messages)

    @property
    def current_step(self) -> int:
        return self._current_step

    def advance_step(self) -> int:
        self._current_step += 1
        return self._current_step

    @property
    def round(self) -> int:
        return self._round

    def increment_round(self) -> int:
        self._round += 1
        return self._round

    def reset_round(self) -> None:
        self._round = 0

    def summary(self) -> dict:
        return {
            "current_step": self._current_step,
            "round": self._round,
            "data_keys": list(self._data.keys()),
            "message_count": len(self._messages),
            "messages": [
                {"sender": m.sender, "receiver": m.receiver, "type": m.msg_type,
                 "preview": str(m.content)[:60]}
                for m in self._messages
            ],
        }
