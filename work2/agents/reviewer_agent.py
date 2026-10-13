"""审校Agent —— 调用通义千问审校草稿,给出结论(APPROVE / REVISIONS)。

关键协作点:
- 读取共享状态中的 outline(规划Agent产出)与 draft(写作Agent产出)
- 把结论写入 review_verdict,供 WorkflowEngine 决定是否回退给写作Agent修订
"""
from __future__ import annotations

import re

from workflow.base_agent import BaseAgent
from workflow.state import WorkflowState

SYSTEM_PROMPT = (
    "你是一名严格、专业的中文内容审校专家。你需要判断草稿是否达到大纲要求,"
    "指出具体问题并给出明确的修改建议。"
)

# 结论 → 估算的覆盖率(用于前端展示)
_VERDICT_COVERAGE = {
    "APPROVE": 1.0,
    "APPROVE_WITH_MINOR_REVISIONS": 0.85,
    "REQUEST_MAJOR_REVISIONS": 0.5,
}


class ReviewerAgent(BaseAgent):
    """审校Agent:调用千问审校草稿 → 给出 verdict → 广播给所有 Agent。"""

    def _build_prompt(self, topic: str, outline_md: str, draft: str) -> str:
        return (
            f"主题:{topic}\n\n文章大纲:\n{outline_md}\n\n待审校的草稿:\n{draft}\n\n"
            "请审校草稿:是否覆盖大纲要点、结构是否完整、表达是否清晰。\n"
            "输出中文审校报告(Markdown,包含总体评价/具体问题/修改建议),"
            "并在最后单独一行给出结论,格式必须为下列之一:\n"
            "VERDICT: APPROVE\n"
            "VERDICT: APPROVE_WITH_MINOR_REVISIONS\n"
            "VERDICT: REQUEST_MAJOR_REVISIONS"
        )

    def run(self, state: WorkflowState) -> dict:
        topic = state.get("topic", "未指定主题")
        outline_md = state.get("outline", "")
        draft = state.get("draft", "")

        report = self.chat(SYSTEM_PROMPT, self._build_prompt(topic, outline_md, draft))

        m = re.search(r"VERDICT\s*[:：]\s*([A-Za-z_]+)", report)
        if m:
            verdict = m.group(1).upper()
        else:  # 模型未按格式输出时按关键词兜底
            up = report.upper()
            verdict = "REQUEST_MAJOR_REVISIONS" if ("MAJOR" in up or "REVISION" in up) else "APPROVE"

        # 展示用的报告去掉 VERDICT 行
        report_display = re.sub(r"(?im)^\s*VERDICT\s*[:：].*$", "", report).strip()
        coverage = _VERDICT_COVERAGE.get(verdict, 0.5)

        state.set("review", report_display)
        state.set("review_verdict", verdict)

        self.handoff(
            state,
            receiver="ALL",
            content={"verdict": verdict, "coverage": f"{coverage * 100:.0f}%"},
            msg_type="review",
        )
        return {"review": report_display, "verdict": verdict, "coverage": coverage}