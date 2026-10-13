"""LLM 客户端 —— 通义千问(阿里云百炼 OpenAI 兼容接口)。

本项目所有 Agent 都通过 :meth:`chat` 调用通义千问,
完成「大纲生成 / 正文写作 / 审校」三项任务。
"""
from __future__ import annotations

import os

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen-plus"
API_KEY_ENV = "DASHSCOPE_API_KEY"


class LLMClient:
    """通义千问客户端(OpenAI 兼容协议)。"""

    def __init__(self, config: dict):
        self.config = dict(config or {})

    @property
    def model(self) -> str:
        return self.config.get("model") or DEFAULT_MODEL

    @property
    def base_url(self) -> str:
        return self.config.get("base_url") or DEFAULT_BASE_URL

    @property
    def api_key(self) -> str:
        return self.config.get("api_key") or os.environ.get(API_KEY_ENV, "")

    def describe(self) -> str:
        return f"通义千问 {self.model}"

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """发送一次对话请求,返回模型文本输出。"""
        from openai import OpenAI

        if not self.api_key:
            raise RuntimeError(
                "缺少 API Key —— 请在 config.yaml 的 llm.api_key 填写,"
                f"或设置环境变量 {API_KEY_ENV}。"
            )

        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.config.get("timeout", 60),
        )
        resp = client.chat.completions.create(
            model=self.model,
            temperature=self.config.get("temperature", 0.7),
            max_tokens=self.config.get("max_tokens", 2000),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return (resp.choices[0].message.content or "").strip()