"""Web 后端 —— 提供前端页面 + SSE 流式执行接口。

启动:
    python web/server.py          # 或  python main.py --serve
然后浏览器打开 http://127.0.0.1:8000
"""
from __future__ import annotations

import json
import os
import queue
import sys
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from main import build_workflow, load_config  # noqa: E402

CONFIG_PATH = os.path.join(ROOT, "config.yaml")
INDEX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

app = FastAPI(title="内容创作 Workflow MVP")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


class RunRequest(BaseModel):
    topic: str = "人工智能如何改变软件开发"
    api_key: str = ""
    model: str = ""
    base_url: str = ""
    max_review_rounds: int = 2


@app.get("/")
def index():
    return FileResponse(INDEX_PATH, headers={"Cache-Control": "no-store, must-revalidate"})


@app.get("/api/config")
def get_config():
    cfg = load_config(CONFIG_PATH)
    return {
        "default_topic": cfg["workflow"]["topic"],
        "default_max_rounds": cfg["workflow"]["max_review_rounds"],
        "model": cfg["llm"].get("model") or "qwen-plus",
        "has_key": bool(cfg["llm"].get("api_key") or os.environ.get("DASHSCOPE_API_KEY")),
    }


def _config_from_request(req: RunRequest) -> dict:
    cfg = load_config(CONFIG_PATH)
    if req.api_key:
        cfg["llm"]["api_key"] = req.api_key
    if req.model:
        cfg["llm"]["model"] = req.model
    if req.base_url:
        cfg["llm"]["base_url"] = req.base_url
    cfg["workflow"]["topic"] = req.topic
    return cfg


@app.post("/api/run")
def run(req: RunRequest):
    """执行 Workflow,以 SSE 流式返回执行事件与最终成果。"""
    events: "queue.Queue" = queue.Queue()

    def worker():
        try:
            cfg = _config_from_request(req)
            engine = build_workflow(cfg)
            engine.set_event_logger(events.put)
            summary = engine.run(
                initial_data={"topic": req.topic},
                max_review_rounds=max(0, req.max_review_rounds),
            )
            events.put({
                "type": "result",
                "outline": engine.state.get("outline", ""),
                "article": engine.state.get("draft", ""),
                "review": engine.state.get("review", ""),
                "verdict": engine.state.get("review_verdict", ""),
                "summary": summary,
            })
        except Exception as exc:  # 错误处理:把异常回传前端
            events.put({"type": "error", "message": f"{type(exc).__name__}: {exc}"})
        finally:
            events.put(None)

    threading.Thread(target=worker, daemon=True).start()

    def event_stream():
        while True:
            item = events.get()
            if item is None:
                break
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def serve(host: str = "127.0.0.1", port: int = 8000):
    import uvicorn
    print("=" * 56)
    print("  内容创作 Workflow MVP — Web 前端")
    print(f"  请在浏览器打开: http://{host}:{port}")
    print("=" * 56)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    serve()