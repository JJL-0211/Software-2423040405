# 内容创作 Workflow MVP

> 方向：内容创作流程（主题 → 大纲 → 内容 → 审校）
> 3 个 AI Agent 协作完成文章创作流水线，支持 **通义千问（Qwen）大模型** 与 **Web 前端页面**。

## 流程

```
规划Agent(Planner) ──outline──► 写作Agent(Writer) ──draft──► 审校Agent(Reviewer)
     │                              ▲                              │
     │                              │  review(未通过则回退修订)      │
     └──── WorkflowState（共享状态 + 消息传递/黑板） ────────────────┘
```

- **顺序执行**：规划 → 写作 → 审校。
- **条件分支 + 循环**：审校给出 verdict；未通过则回退给写作 Agent 修订，循环直到通过或达到最大轮次。
- **Agent 间通信**：所有产出写入共享状态 `WorkflowState`，并附带定向消息（`outline` / `draft` / `review`）。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动 Web 前端（推荐）

```bash
python web/server.py
# 或  python main.py --serve
```

浏览器打开 <http://127.0.0.1:8000>，即可在页面上：
- 输入文章主题（API Key 已在 config.yaml 配置好，页面上可留空；也可临时填写覆盖）；
- 实时查看流程节点状态与执行日志；
- 查看大纲 / 文章 / 审校报告 / 状态摘要。

### 3. 命令行运行

```bash
python main.py                                     # 使用 config.yaml 中的主题与 API Key
python main.py --topic "区块链在供应链的应用"          # 自定义主题
python main.py --api-key sk-xxxx                   # 临时指定 API Key
python main.py --model qwen-turbo                  # 指定模型
python main.py --output result.md --log run.log    # 保存成果与日志
```

## 使用通义千问（Qwen）

千问通过阿里云百炼的 **OpenAI 兼容接口** 接入：

- 默认 `base_url`：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- 默认模型：`qwen-plus`（可选 `qwen-turbo` / `qwen-max` 等）
- API Key 获取：阿里云百炼控制台创建后，任选一种方式配置：

  ```yaml
  # 方式一：config.yaml 中填写
  llm:
    api_key: "sk-xxxxxxxx"
  ```
  ```powershell
  # 方式二：环境变量（Windows PowerShell）
  $env:DASHSCOPE_API_KEY="sk-xxxxxxxx"
  ```

  Web 前端也可直接在页面上填写 API Key（不会写入任何文件）。

> 注意：若账号免费额度用尽，接口会返回 `403 Free quota exhausted`，需在阿里云百炼控制台关闭「仅使用免费额度」或充值后使用。

## 目录结构

```
homework2-workflow/
├── main.py                  # 命令行入口（--serve 可启动前端）
├── config.yaml              # 配置（千问参数 / 主题）
├── requirements.txt
├── llm/client.py            # LLM 客户端：通义千问（OpenAI 兼容）
├── workflow/
│   ├── state.py             # 共享状态 + Agent 间消息传递
│   ├── base_agent.py        # Agent 基类
│   └── engine.py            # 编排引擎（顺序 + 审校循环 + 事件回调）
├── agents/
│   ├── planner_agent.py     # 规划 Agent
│   ├── writer_agent.py      # 写作 Agent
│   └── reviewer_agent.py    # 审校 Agent
└── web/
    ├── server.py            # FastAPI 后端（SSE 流式执行）
    └── index.html           # 前端页面
```

详见 [Design.md](Design.md) 了解架构设计与作业要求对照。