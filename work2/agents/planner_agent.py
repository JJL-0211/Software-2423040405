"""规划Agent —— 调用通义千问,根据主题生成结构化文章大纲。

产出写入共享状态:
- outline       : Markdown 大纲(供展示,并传递给写作Agent)
- outline_struct: 解析出的章节结构(供展示)

完成后向下游「写作Agent」发送一条 outline 消息。
"""
from __future__ import annotations

import re

from workflow.base_agent import BaseAgent
from workflow.state import WorkflowState

SYSTEM_PROMPT = (
    "你是一名资深的内容策划。请为主题设计结构清晰的中文文章大纲,"
    "严格按要求输出 Markdown,不要添加任何额外说明。"
)


def _parse_outline_md(md: str) -> list[tuple[str, list[str]]]:
    """从 Markdown 大纲解析出 [(章节标题, [要点])]。"""
    sections: list[tuple[str, list[str]]] = []
    title, points = None, []
    for line in md.splitlines():
        s = line.strip()
        if s.startswith("## "):
            if title:
                sections.append((title, points))
            title = re.sub(r"^[一二三四五六七八九十\d]+[、.．)]\s*", "", s[3:].strip()).strip()
            points = []
        elif s.startswith(("- ", "* ", "+ ")):
            if title:
                points.append(s[2:].strip())
    if title:
        sections.append((title, points))
    return sections


class PlannerAgent(BaseAgent):
    """规划Agent:调用千问生成大纲 → 写入共享状态 → 消息传递给写作Agent。"""

    def _build_prompt(self, topic: str) -> str:
        return (
            f"主题:{topic}\n\n"
            "请为该主题设计一篇文章大纲,要求:\n"
            "1. 包含 5 个章节,标题简洁(如 引言/现状分析/核心挑战/未来展望/总结);\n"
            "2. 每个章节下给出 3 个具体要点,每行一个;\n"
            "3. 严格使用如下 Markdown 格式,不要输出任何其他内容:\n\n"
            f"# {topic}\n\n## 一、章节标题\n- 要点1\n- 要点2\n- 要点3\n\n(其余章节以此类推)"
        )

    def run(self, state: WorkflowState) -> dict:
        topic = state.get("topic", "未指定主题")
        outline_md = self.chat(SYSTEM_PROMPT, self._build_prompt(topic))
        sections = _parse_outline_md(outline_md)

        state.set("outline", outline_md)
        state.set("outline_struct", {
            "topic": topic,
            "sections": [{"title": t, "points": p} for t, p in sections],
        })

        self.handoff(
            state,
            receiver="写作Agent",
            content={"outline_md": outline_md, "sections": len(sections)},
            msg_type="outline",
        )
        return {"outline": outline_md, "sections_count": len(sections)}