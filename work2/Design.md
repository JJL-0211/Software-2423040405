# Design.md — 设计文档

## 1. 架构

```
                        ┌───────────────────────────┐
   浏览器页面  ──SSE──► │   FastAPI (web/server.py)  │
   web/index.html       │   执行 + 事件流式推送        │
                        └────────────┬──────────────┘
                                     │ 调用
                        ┌────────────▼──────────────┐
                        │      WorkflowEngine        │
                        │  顺序 + 审校循环 + 事件回调  │
                        └────────────┬──────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                            ▼
  ┌──────────┐                 ┌──────────┐                 ┌──────────┐
  │ Planner  │                 │  Writer  │                 │ Reviewer │
  └────┬─────┘                 └────┬─────┘                 └────┬─────┘
       │                            │                            │
       └────────────────────────────┼────────────────────────────┘
                                    ▼
                         ┌────────────────────┐
                         │   WorkflowState     │
                         │ （黑板：数据+消息）  │
                         └─────────┬──────────┘
                                   ▼
                         ┌────────────────────┐
                         │      LLMClient      │
                         │ 通义千问 (Qwen API) │
                         └────────────────────┘
```

## 2. 核心组件

| 组件 | 职责 | 对应作业要求 |
|------|------|-------------|
| WorkflowState | 共享数据 + 消息日志 | 状态管理 + Agent 间通信 |
| BaseAgent | 抽象基类，`run()` 契约 | — |
| WorkflowEngine | 顺序执行 + 审校循环 + 事件回调 | 流程控制（顺序 + 条件分支/循环） |
| LLMClient | 通义千问客户端（阿里云百炼 OpenAI 兼容） | 接入通义千问大模型 |
| web/server.py | FastAPI 后端，SSE 流式执行 | 可视化界面 / 执行日志与状态追踪 |
| web/index.html | 前端页面（流程可视化 + 实时日志 + 成果展示） | 可视化 Workflow 编排界面 |

## 3. 大模型接入

三个 Agent 均通过 `LLMClient` 调用 **通义千问**（阿里云百炼 OpenAI 兼容接口），不存在本地兜底逻辑：

- **规划Agent**：主题 → 结构化大纲
- **写作Agent**：大纲（+ 审校意见时按意见修订）→ 正文
- **审校Agent**：草稿 → 审校报告与结论（`APPROVE` / `REQUEST_MAJOR_REVISIONS`）

默认模型 `qwen-plus`，可通过 `config.yaml` 的 `llm.model` 或页面上的「模型」输入框切换（如 `qwen-turbo` / `qwen-max`）。
API Key 可写在 `config.yaml`、环境变量 `DASHSCOPE_API_KEY`，或在页面直接填写。

## 4. 流程控制细节

1. **顺序执行**：`planner`、`writer` 按注册顺序执行。
2. **条件分支 + 循环**：`reviewer` 输出 `review_verdict`；
   - 判定为 `APPROVE` 且不含 `REVISION` → 结束循环；
   - 否则回退给 `writer` 重新修订，最多循环 `max_review_rounds + 1` 轮。
3. **错误处理**：任一 Agent 抛错时，引擎记录 `last_error` 并通过事件流把错误推送到前端。
4. **可观测性**：引擎通过 `set_event_logger` 推送结构化事件
   （`workflow_start` / `agent_start` / `agent_end` / `agent_error` / `log` / `result`），前端据此实时渲染节点状态与日志。

## 5. 满足作业要求

**必须实现：**
- ✅ 3 个 Agent 协作（≥2）：规划 + 写作 + 审校
- ✅ Agent 间消息传递（`outline` / `draft` / `review` 定向消息）+ 状态共享（`WorkflowState` 黑板）
- ✅ 顺序执行流程控制
- ✅ 端到端可运行：三个 Agent 全部调用通义千问完成创作

**推荐实现：**
- ✅ 条件分支 + 循环（审校循环）
- ✅ 可视化 Workflow 编排/展示界面（Web 前端）
- ✅ 执行日志 + 状态追踪（实时日志 + 状态摘要）
- ✅ 错误处理与提示

## 6. 可扩展性

- **新增 Agent**：继承 `BaseAgent` 实现 `run()` → 在 `main.build_workflow()` 中 `engine.add_agent(agent, role="...")` 注册即可，无需改动现有 Agent。
- **调整流程**：在 `WorkflowEngine.run()` 中调整编排顺序与循环条件。
- **切换模型**：修改 `config.yaml` 的 `llm.model`，或在页面上直接填写模型名。