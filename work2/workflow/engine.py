"""Workflow engine — orchestrates agents in a sequential pipeline with review loop."""
from __future__ import annotations

import time
from typing import Callable

from workflow.state import WorkflowState


class WorkflowEngine:
    """Sequential engine with optional Reviewer → Writer revision loop."""

    def __init__(self, name: str = "Workflow"):
        self.name = name
        self.agents: list = []
        self.state = WorkflowState()
        self.log: list[dict] = []
        self._logger: Callable[[str], None] | None = None
        self._event_logger: Callable[[dict], None] | None = None

    def add_agent(self, agent, role: str = "worker") -> "WorkflowEngine":
        self.agents.append((agent, role))
        return self

    def set_logger(self, logger: Callable[[str], None]) -> None:
        self._logger = logger

    def set_event_logger(self, logger: Callable[[dict], None]) -> None:
        """注册结构化事件回调(供 Web 前端实时展示)。"""
        self._event_logger = logger

    def _emit(self, event_type: str, **payload) -> None:
        if self._event_logger:
            self._event_logger({"type": event_type, "step": self.state.current_step,
                                "round": self.state.round, **payload})

    def _log(self, message: str) -> None:
        self.log.append({"step": self.state.current_step, "round": self.state.round,
                         "timestamp": time.time(), "message": message})
        if self._logger:
            self._logger(message)
        self._emit("log", message=message)

    def run(self, initial_data: dict | None = None, max_review_rounds: int = 0) -> dict:
        if initial_data:
            self.state.update(initial_data)

        self._log(f"▶ Workflow '{self.name}' started")
        self._log(f"  Agents: {', '.join(a.name for a, _ in self.agents)}")
        self._log(f"  Max review rounds: {max_review_rounds}")
        self._emit("workflow_start", name=self.name,
                   agents=[{"name": a.name, "role": r} for a, r in self.agents])

        pre_review = [(a, r) for a, r in self.agents if r in ("planner", "writer")]
        reviewer = next((a for a, r in self.agents if r == "reviewer"), None)
        writer = next((a for a, r in self.agents if r == "writer"), None)

        for agent, role in pre_review:
            self._run_agent(agent, role)

        if reviewer is not None:
            for round_idx in range(max_review_rounds + 1):
                if round_idx > 0:
                    self._log(f"\n♻ Review round {round_idx}/{max_review_rounds}")
                    self.state.increment_round()
                self._run_agent(reviewer, "reviewer")
                verdict = self.state.get("review_verdict", "")
                if "APPROVE" in verdict.upper() and "REVISION" not in verdict.upper():
                    self._log("✓ Reviewer approved — stopping revision loop")
                    break
                if round_idx < max_review_rounds and writer is not None:
                    self._log("→ Reviewer requested revisions, re-running writer")
                    self._run_agent(writer, "writer")
                else:
                    self._log("→ Max review rounds reached, finishing")
                    break

        self._log(f"✔ Workflow '{self.name}' completed")
        self._emit("workflow_done")
        return self.state.summary()

    def _run_agent(self, agent, role: str = "worker") -> None:
        self.state.advance_step()
        self._log(f"\n━━━ [{agent.name}] starting ━━━")
        self._emit("agent_start", agent=agent.name, role=role)
        start = time.time()
        try:
            outputs = agent.run(self.state)
            duration = time.time() - start
            self._log(f"  {agent.name} finished in {duration:.2f}s")
            self._log(f"  outputs: {list(outputs.keys()) if outputs else 'none'}")
            self._emit("agent_end", agent=agent.name, role=role,
                       duration=round(duration, 2),
                       outputs=list(outputs.keys()) if outputs else [])
        except Exception as exc:
            duration = time.time() - start
            self._log(f"  ✗ {agent.name} FAILED after {duration:.2f}s: {exc}")
            self.state.set("last_error", {"agent": agent.name, "error": str(exc)})
            self._emit("agent_error", agent=agent.name, role=role, message=str(exc))
            raise
