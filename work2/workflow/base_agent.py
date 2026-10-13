"""Base agent class — contract all agents follow."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod

from workflow.state import WorkflowState


class BaseAgent(ABC):
    """Abstract base class for all workflow agents."""

    def __init__(self, name: str, description: str, llm_client):
        self.name = name
        self.description = description
        self.llm = llm_client
        self._last_duration: float = 0.0

    @abstractmethod
    def run(self, state: WorkflowState) -> dict:
        """Execute the agent's task. Returns dict of outputs written to state."""
        ...

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        start = time.time()
        result = self.llm.chat(system_prompt, user_prompt)
        self._last_duration = time.time() - start
        return result

    def handoff(self, state: WorkflowState, receiver: str, content: any, msg_type: str = "data") -> None:
        state.send_message(sender=self.name, receiver=receiver, content=content, msg_type=msg_type)

    def __repr__(self) -> str:
        return f"<Agent {self.name}: {self.description}>"
