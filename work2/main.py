"""Content Creation Workflow MVP — main entry point."""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_config(config_path: str = "config.yaml") -> dict:
    defaults = {
        "llm": {"model": "", "base_url": "", "api_key": "",
                "temperature": 0.7, "max_tokens": 2000, "timeout": 60},
        "workflow": {"topic": "人工智能如何改变软件开发",
                      "max_review_rounds": 2, "log_enabled": True},
    }
    try:
        import yaml
    except ImportError:
        return defaults
    if not os.path.exists(config_path):
        return defaults
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    for section, vals in defaults.items():
        cfg.setdefault(section, vals)
        if isinstance(vals, dict):
            for k, v in vals.items():
                cfg[section].setdefault(k, v)
    return cfg


def build_workflow(config: dict):
    from llm.client import LLMClient
    from workflow.engine import WorkflowEngine
    from agents.planner_agent import PlannerAgent
    from agents.writer_agent import WriterAgent
    from agents.reviewer_agent import ReviewerAgent

    llm = LLMClient(config["llm"])

    engine = WorkflowEngine(name="内容创作Workflow")
    engine.add_agent(
        PlannerAgent(name="规划Agent", description="根据主题生成文章大纲", llm_client=llm),
        role="planner",
    )
    engine.add_agent(
        WriterAgent(name="写作Agent", description="根据大纲撰写正文", llm_client=llm),
        role="writer",
    )
    engine.add_agent(
        ReviewerAgent(name="审校Agent", description="审查内容质量并提出修改建议", llm_client=llm),
        role="reviewer",
    )
    return engine


def main():
    parser = argparse.ArgumentParser(description="内容创作 Workflow MVP — 3 Agent 协作")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--topic", default=None)
    parser.add_argument("--model", default=None, help="覆盖模型名,如 qwen-plus / qwen-turbo")
    parser.add_argument("--api-key", default=None, help="覆盖通义千问 API Key")
    parser.add_argument("--serve", action="store_true", help="启动 Web 前端(等价于 python web/server.py)")
    parser.add_argument("--max-rounds", type=int, default=None)
    parser.add_argument("--output", "-o", default=None)
    parser.add_argument("--log", default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if args.serve:
        from web.server import serve
        serve()
        return

    config = load_config(args.config)
    if args.topic:
        config["workflow"]["topic"] = args.topic
    if args.model:
        config["llm"]["model"] = args.model
    if args.api_key:
        config["llm"]["api_key"] = args.api_key
    if args.max_rounds is not None:
        config["workflow"]["max_review_rounds"] = args.max_rounds

    topic = config["workflow"]["topic"]
    max_rounds = config["workflow"].get("max_review_rounds", 2)

    engine = build_workflow(config)
    if not args.quiet:
        print("=" * 60)
        print("  内容创作 Workflow MVP")
        print("  规划Agent → 写作Agent → 审校Agent")
        print("=" * 60)
        print(f"  主题: {topic}")
        print("  大模型: 通义千问 " + (config["llm"].get("model") or "qwen-plus"))
        print(f"  最大审校轮次: {max_rounds}")
        print("=" * 60)

    log_lines: list[str] = []
    def logger(msg: str):
        log_lines.append(msg)
        if not args.quiet:
            print(msg)

    engine.set_logger(logger)
    summary = engine.run(initial_data={"topic": topic}, max_review_rounds=max_rounds)

    if not args.quiet:
        print("\n" + "=" * 60)
        print("  Workflow 完成 — 最终成果")
        print("=" * 60)

    final_article = engine.state.get("draft", "")
    review = engine.state.get("review", "")

    if not args.quiet and final_article:
        print("\n--- 最终文章 ---\n")
        print(final_article)
    if not args.quiet and review:
        print("\n--- 审校报告 ---\n")
        print(review)

    if args.output and final_article:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(f"# {topic}\n\n{final_article}\n")
        print(f"\n✓ 文章已保存到: {args.output}")

    if args.log:
        with open(args.log, "w", encoding="utf-8") as f:
            for line in log_lines:
                f.write(line + "\n")
        print(f"✓ 日志已保存到: {args.log}")

    if not args.quiet:
        print("\n" + "=" * 60)
        print("  状态摘要")
        print("=" * 60)
        print(f"  执行步数: {summary['current_step']}")
        print(f"  审校轮次: {summary['round']}")
        print(f"  共享数据键: {summary['data_keys']}")
        print(f"  消息总数: {summary['message_count']}")
        for msg in summary["messages"]:
            print(f"    • {msg['sender']} → {msg['receiver']} [{msg['type']}]: {msg['preview']}...")
        print("=" * 60)


if __name__ == "__main__":
    main()
