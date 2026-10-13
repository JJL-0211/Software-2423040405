"""写作Agent —— 调用通义千问,根据大纲撰写正文(有审校意见时据此修订)。

关键协作点:
- 从共享状态 outline 读取规划Agent的产出
- 若存在审校报告 review,则视为修订轮,据此改写后重新输出
"""
from __future__ import annotations

from workflow.base_agent import BaseAgent
from workflow.state import WorkflowState

SYSTEM_PROMPT = (
    "你是一名专业的中文内容创作者。请根据大纲撰写完整、连贯、有信息量的文章正文,"
    "使用 Markdown 格式,只输出文章本身。"
)


class WriterAgent(BaseAgent):
    """写作Agent:读取大纲 → 调用千问撰写正文 → 交给审校Agent。"""

    def _build_prompt(self, topic: str, outline_md: str, review_md: str) -> str:
        prompt = (
            f"主题:{topic}\n\n文章大纲:\n{outline_md}\n\n"
            "请据此撰写一篇完整的文章正文,要求:\n"
            "1. 使用 Markdown,章节标题用 ## 开头,与大纲保持一致;\n"
            "2. 每个章节写成连贯的段落(不要只罗列要点),内容具体、有论据;\n"
            "3. 全中文,篇幅约 800-1200 字。"
        )
        if review_md:
            prompt += f"\n\n上一轮审校意见,请针对性修订后重新输出完整文章:\n{review_md}"
        return prompt

    def run(self, state: WorkflowState) -> dict:
        topic = state.get("topic", "未指定主题")
        outline_md = state.get("outline", "")
        review_md = state.get("review", "")
        is_revision = bool(review_md)

        draft = self.chat(SYSTEM_PROMPT, self._build_prompt(topic, outline_md, review_md))

        state.set("draft", draft)
        self.handoff(
            state,
            receiver="审校Agent",
            content={"draft_length": len(draft), "revision": is_revision},
            msg_type="draft",
        )
        return {"draft": draft, "chars": len(draft)}