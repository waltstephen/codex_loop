# ArgusBot - CLAUDE.md

## 环境配置
- python 版本： 3.12.3

## 项目概述

ArgusBot 是一个 Python supervisor 插件，用于 Codex CLI 的自动循环执行器。它解决了"agent 过早停止并请求下一步指令"的问题。

**核心机制：**
- **Main Agent**: 执行实际任务 (`codex exec` 或 `codex exec resume`)
- **Reviewer Sub-agent**: 评估完成情况 (`done` / `continue` / `blocked`)
- **Planner Sub-agent**: 维护实时计划视图并提出下一 session 目标
- **循环机制**: 只有当 reviewer 说 `done` 且所有验收检查通过时才停止

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      ArgusBot                                │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   Main       │───▶│  Reviewer    │───▶│   Planner    │   │
│  │   Agent      │    │  (done?)     │    │  (next?)     │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│         │                   │                   │            │
│         ▼                   ▼                   ▼            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              LoopEngine / Orchestrator               │   │
│  └──────────────────────────────────────────────────────┘   │
│         │                   │                   │            │
│         ▼                   ▼                   ▼            │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │  CodexRunner │    │  Checks      │    │  State Store │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  Control Channels: Telegram | Feishu | Terminal (CLI)       │
└─────────────────────────────────────────────────────────────┘
```

## 核心组件

### 核心引擎

| 文件 | 职责 |
|------|------|
| `codex_autoloop/core/engine.py` | **LoopEngine** - 核心循环引擎：管理主 agent→检查→reviewer→planner 循环 |
| `codex_autoloop/orchestrator.py` | **AutoLoopOrchestrator** - 编排器：协调 runner、reviewer、planner 的执行流程 |
| `codex_autoloop/codexloop.py` | **主循环入口** - 单字命令 `argusbot` 的实现 |
| `codex_autoloop/core/ports.py` | 事件端口接口定义 |
| `codex_autoloop/core/state_store.py` | 状态存储和事件处理 |

### Agent 组件

| 文件 | 职责 |
|------|------|
| `codex_autoloop/reviewer.py` | **Reviewer** - 评审器：评估任务是否完成，返回 done/continue/blocked |
| `codex_autoloop/planner.py` | **Planner** - 规划器：维护工作流视图，提出后续目标 |
| `codex_autoloop/stall_subagent.py` | **停滞检测** - 检测 agent 停滞并自动诊断/重启 |
| `codex_autoloop/btw_agent.py` | **BTW 侧边代理** - 只读项目问答代理 |

### 执行器

| 文件 | 职责 |
|------|------|
| `codex_autoloop/codex_runner.py` | **CodexRunner** - Codex CLI 执行器：调用 `codex exec` |
| `codex_autoloop/checks.py` | **验收检查** - 运行并验证检查命令 |

### 控制通道

| 文件 | 职责 |
|------|------|
| `codex_autoloop/telegram_control.py` | **Telegram 控制** - Telegram  inbound 控制通道 |
| `codex_autoloop/telegram_notifier.py` | **Telegram 通知** - Telegram 事件推送 |
| `codex_autoloop/telegram_daemon.py` | **Telegram 守护进程** - 24/7 后台运行 |
| `codex_autoloop/feishu_adapter.py` | **飞书适配** - 飞书通知和控制通道 |
| `codex_autoloop/daemon_bus.py` | **命令总线** - JSONL 格式的守护进程命令通道 |
| `codex_autoloop/daemon_ctl.py` | **守护进程控制** - 终端控制台命令 |
| `codex_autoloop/local_control.py` | **本地终端控制** - 本地终端交互 |

### 数据模型

| 文件 | 职责 |
|------|------|
| `codex_autoloop/models.py` | **核心数据结构** - ReviewDecision, PlanDecision, PlanSnapshot, RoundSummary |
| `codex_autoloop/planner_modes.py` | **Planner 模式** - off/auto/record 模式定义 |

### 工具和辅助

| 文件 | 职责 |
|------|------|
| `codex_autoloop/model_catalog.py` | **模型目录** - 常用模型预设查询 |
| `codex_autoloop/setup_wizard.py` | **安装向导** - 交互式首次配置 |
| `codex_autoloop/token_lock.py` | **Token 独占锁** - 一 Telegram token 一守护进程 |
| `codex_autoloop/copilot_proxy.py` | **Copilot 代理** - GitHub Copilot 本地代理 |
| `codex_autoloop/dashboard.py` | **本地 Web 仪表板** - 实时运行状态可视化 |
| `codex_autoloop/live_updates.py` | **实时更新推送** - 实时 agent 消息推送 |
| `codex_autoloop/attachment_policy.py` | **附件策略** - BTW 附件上传策略 |

## 入口点命令 (pyproject.toml)

```
argusbot              - 单字入口 (自动附加监控)
argusbot-run          - 运行循环
argusbot-daemon       - Telegram/Feishu 守护进程
argusbot-daemon-ctl   - 守护进程控制
argusbot-setup        - 交互式安装向导
argusbot-models       - 模型目录查询
```

## 数据模型

### ReviewDecision (models.py:41-48)
```python
status: Literal["done", "continue", "blocked"]
confidence: float
reason: str
next_action: str
round_summary_markdown: str
completion_summary_markdown: str
```

### PlanDecision (models.py:51-57)
```python
follow_up_required: bool
next_explore: str
main_instruction: str
review_instruction: str
overview_markdown: str
```

### PlanSnapshot (models.py:68-82)
```python
plan_id: str
generated_at: str
trigger: str
terminal: bool
summary: str
workstreams: list[PlanWorkstream]
done_items: list[str]
remaining_items: list[str]
risks: list[str]
next_steps: list[str]
exploration_items: list[str]
suggested_next_objective: str
should_propose_follow_up: bool
report_markdown: str
```

## 控制通道

### Telegram
- Bot token 和 chat_id 配置
- 命令：`/run`, `/inject`, `/status`, `/stop`, `/plan`, `/review`, `/btw`
- 支持语音/音频转录 (Whisper)
- 支持附件上传 (图片/视频/文件)

### Feishu (飞书)
- App ID / App Secret / Chat ID 配置
- 适合中国网络环境
- 群聊命令支持 (@bot /command)

### 本地终端
- `argusbot` - 附加监控控制台
- `argusbot-daemon-ctl --bus-dir <dir> <command>` - 直接控制守护进程

## 开发指南

### 测试
```bash
pytest tests/
```

测试文件覆盖：
- `tests/test_codexloop.py` - 主循环测试
- `tests/test_orchestrator.py` - 编排器测试
- `tests/test_reviewer.py` - Reviewer 测试
- `tests/test_planner.py` - Planner 测试
- `tests/test_engine.py` - LoopEngine 测试
- 各组件单元测试...

### 调试

**查看详细事件流：**
```bash
argusbot-run --verbose-events "objective"
```

**日志文件位置：**
- 守护进程日志：`.argusbot/daemon.out`
- 事件流：`.argusbot/logs/daemon-events.jsonl`
- 运行存档：`.argusbot/logs/argusbot-run-archive.jsonl`

### 扩展

**添加新的控制通道：**
1. 在 `codex_autoloop/adapters/` 下创建新的适配器
2. 实现 `EventSink` 接口 (`core/ports.py`)
3. 在 `setup_wizard.py` 中添加配置选项

**添加新的 agent 类型：**
1. 参考 `reviewer.py` 或 `planner.py` 的实现模式
2. 使用 `CodexRunner` 执行子代理调用
3. 定义结构化输出 schema (JSON)


### 关键文件引用

**核心引擎:**
- `codex_autoloop/core/engine.py` - LoopEngine
- `codex_autoloop/orchestrator.py` - AutoLoopOrchestrator
- `codex_autoloop/codexloop.py` - 主循环入口

**Agent 组件:**
- `codex_autoloop/reviewer.py` - Reviewer 评审器
- `codex_autoloop/planner.py` - Planner 规划器
- `codex_autoloop/stall_subagent.py` - 停滞检测

### 测试检查（cli）

source .venv/bin/activate
在claude_test目录下执行测试检查

#### 1. 简单任务 - 创建文件
claude-autoloop-run "创建一个 README.md 文件，包含项目介绍" --yolo --max-rounds 2 --skip-git-repo-check

#### 2. 数学计算任务
claude-autoloop-run "计算 1 到 100 的和，将结果写入 result.txt" --yolo --max-rounds 2 --skip-git-repo-check

#### 3. 代码修改任务
claude-autoloop-run "在当前目录创建一个 Python 计算器模块，支持加减乘除" --yolo --max-rounds 3 --skip-git-repo-check

Reviewer 和 Planner 测试

source .venv/bin/activate

#### 4. 测试 planner 自动模式（默认）
claude-autoloop-run "分析当前目录结构，创建一个项目分析报告" \
  --yolo --max-rounds 3 --skip-git-repo-check \
  --planner

#### 5. 关闭 planner 测试
claude-autoloop-run "打印 Hello World" \
  --yolo --max-rounds 2 --skip-git-repo-check \
  --no-planner

#### 6. 测试 reviewer 决策
claude-autoloop-run "创建一个空的 package.json 文件" \
  --yolo --max-rounds 2 --skip-git-repo-check

验收检查测试

source .venv/bin/activate

#### 7. 带验收检查的任务
claude-autoloop-run "创建一个 greet.py 脚本，接受名字参数并打印问候语" \
  --yolo --max-rounds 3 --skip-git-repo-check \
  --check "python3 greet.py World | grep -q 'Hello World'" \
  --check "test -f greet.py"

#### 8. 多检查项测试
claude-autoloop-run "创建一个包含 main 函数的 Python 模块" \
  --yolo --max-rounds 3 --skip-git-repo-check \
  --check "python3 -m py_compile module.py" \
  --check "grep -q 'if __name__' module.py"

模型和配置测试

source .venv/bin/activate

#### 9. 指定模型
claude-autoloop-run "简单任务" \
  --yolo --max-rounds 2 --skip-git-repo-check \
  --main-model qwen3.5-plus

#### 10. 指定 reasoning effort
claude-autoloop-run "分析这个文件的代码结构" \
  --yolo --max-rounds 2 --skip-git-repo-check \
  --main-reasoning-effort high \
  --reviewer-reasoning-effort medium

#### 11. 不同 agent 使用不同模型
claude-autoloop-run "复杂任务" \
  --yolo --max-rounds 3 --skip-git-repo-check \
  --main-model qwen3.5-plus \
  --reviewer-model qwen3.5-plus \
  --plan-model qwen3.5-plus

状态和输出文件测试

source .venv/bin/activate

#### 12. 输出状态文件
claude-autoloop-run "创建测试文件" \
  --yolo --max-rounds 2 --skip-git-repo-check \
  --state-file /tmp/test-state.json

#### 13. 输出操作员消息文件
claude-autoloop-run "多轮对话任务" \
  --yolo --max-rounds 3 --skip-git-repo-check \
  --operator-messages-file /tmp/operator.md \
  --plan-overview-file /tmp/plan.md

#### 14. 完整输出文件测试
claude-autoloop-run "完整项目任务" \
  --yolo --max-rounds 3 --skip-git-repo-check \
  --state-file /tmp/state.json \
  --operator-messages-file /tmp/messages.md \
  --plan-overview-file /tmp/plan.md \
  --plan-todo-file /tmp/todo.md \
  --review-summaries-dir /tmp/reviews

停滞检测测试

source .venv/bin/activate

#### 15. 短停滞检测（快速测试）
claude-autoloop-run "长时间任务" \
  --yolo --max-rounds 2 --skip-git-repo-check \
  --stall-soft-idle-seconds 60 \
  --stall-hard-idle-seconds 120

#### 16. 禁用停滞检测
claude-autoloop-run "任务" \
  --yolo --max-rounds 2 --skip-git-repo-check \
  --stall-soft-idle-seconds 0 \
  --stall-hard-idle-seconds 0

控制通道测试

source .venv/bin/activate

#### 17. 本地控制文件
claude-autoloop-run "长时间运行的任务" \
  --yolo --max-rounds 5 --skip-git-repo-check \
  --control-file /tmp/control.jsonl \
  --control-poll-interval-seconds 1

后台注入控制命令示例：
echo '{"type": "inject", "message": "请改为打印 10 次 Hello"}' >> /tmp/control.jsonl
echo '{"type": "stop"}' >> /tmp/control.jsonl
echo '{"type": "status"}' >> /tmp/control.jsonl

详细日志测试

source .venv/bin/activate

#### 18. 详细事件输出
claude-autoloop-run "调试任务" \
  --yolo --max-rounds 2 --skip-git-repo-check \
  --verbose-events

#### 19. 禁用实时终端输出
claude-autoloop-run "安静模式任务" \
  --yolo --max-rounds 2 --skip-git-repo-check \
  --no-live-terminal

Copilot Proxy 测试（如果配置了）

source .venv/bin/activate

#### 20. 使用 Copilot Proxy
claude-autoloop-run "任务" \
  --copilot-proxy \
  --copilot-proxy-port 18080 \
  --yolo --max-rounds 2 --skip-git-repo-check

压力/边界测试

source .venv/bin/activate

#### 21. 最大轮次限制测试
claude-autoloop-run "不可能完成的任务" \
  --yolo --max-rounds 1 --skip-git-repo-check

#### 22. 无进展检测测试
claude-autoloop-run "重复性任务" \
  --yolo --max-rounds 5 --max-no-progress-rounds 2 --skip-git-repo-check

#### 23. 空目标测试（应该报错）
claude-autoloop-run "" --yolo --max-rounds 1 --skip-git-repo-check

组合测试

source .venv/bin/activate

#### 24. 完整功能测试
claude-autoloop-run "创建一个完整的 Python 项目，包含 setup.py、README.md 和示例模块" \
  --yolo --max-rounds 5 --skip-git-repo-check \
  --main-model qwen3.5-plus \
  --reviewer-model qwen3.5-plus \
  --plan-model qwen3.5-plus \
  --state-file /tmp/full-state.json \
  --operator-messages-file /tmp/messages.md \
  --plan-overview-file /tmp/plan.md \
  --review-summaries-dir /tmp/reviews \
  --check "test -f setup.py" \
  --check "test -f README.md" \
  --verbose-events

#### 25. 额外目录访问 (--add-dir)
claude-autoloop-run "在 /tmp 目录创建文件" \
  --yolo --max-rounds 2 --skip-git-repo-check \
  --add-dir /tmp

#### 26. 插件目录 (--plugin-dir)
claude-autoloop-run "使用自定义插件" \
  --yolo --max-rounds 2 --skip-git-repo-check \
  --plugin-dir /path/to/plugins

#### 27. 文件资源下载 (--file)
claude-autoloop-run "使用下载的文件资源" \
  --yolo --max-rounds 2 --skip-git-repo-check \
  --file "file_abc:doc.txt"

#### 28. Git Worktree (--worktree)
claude-autoloop-run "在隔离的 worktree 中开发" \
  --yolo --max-rounds 3 --skip-git-repo-check \
  --worktree feature-branch

快速验证命令

#### 查看生成的文件
cat /tmp/state.json | python3 -m json.tool
cat /tmp/plan.md
ls -la /tmp/reviews/

---

## 附录：Claude Code CLI 结构化输出参考

### 命令行参数

| 参数 | 说明 |
|------|------|
| `--json-schema <schema>` | JSON Schema 用于结构化输出验证（内联 JSON 字符串） |
| `--output-format <format>` | 输出格式：`text`（默认）/ `json` / `stream-json` |
| `--print` | 非交互模式（管道友好），使用结构化输出时必需 |
| `--add-dir <dir>` | 允许工具访问的额外目录（可重复） |
| `--plugin-dir <dir>` | 从指定目录加载插件（可重复） |
| `--file <spec>` | 下载文件资源，格式：`file_id:relative_path`（可重复） |
| `--worktree [name]` | 创建 git worktree 会话，可选名称 |

### 基础示例

```bash
# 简单对象
claude --print --json-schema '{"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}' "创建一个用户"

# 复杂对象
claude --print --json-schema '{
  "type":"object",
  "properties":{
    "name":{"type":"string"},
    "age":{"type":"number"},
    "city":{"type":"string"}
  },
  "required":["name","age","city"]
}' "创建一个用户，名字叫张三，25 岁，来自北京"

# 纯 JSON 输出（无额外文本）
claude --print --output-format json --json-schema '{"type":"object","properties":{"result":{"type":"string"}},"required":["result"]}' "说 hello"
```

### Reviewer Schema 测试示例

```bash
claude --print --json-schema '{
  "type":"object",
  "required":["status","confidence","reason","next_action"],
  "properties":{
    "status":{"type":"string","enum":["done","continue","blocked"]},
    "confidence":{"type":"number","minimum":0,"maximum":1},
    "reason":{"type":"string"},
    "next_action":{"type":"string"}
  }
}' "评估这个任务是否完成：已经创建了 README.md 文件"
```

### Planner Schema 测试示例

```bash
claude --print --json-schema '{
  "type":"object",
  "required":["summary","workstreams","next_steps"],
  "properties":{
    "summary":{"type":"string"},
    "workstreams":{
      "type":"array",
      "items":{
        "type":"object",
        "required":["area","status"],
        "properties":{
          "area":{"type":"string"},
          "status":{"type":"string","enum":["done","in_progress","todo"]}
        }
      }
    },
    "next_steps":{"type":"array","items":{"type":"string"}}
  }
}' "规划一个 Python 项目开发计划"
```

### 与 Codex CLI 对比

| 特性 | Codex CLI | Claude Code CLI |
|------|-----------|-----------------|
| Schema 参数 | `--output-schema <file>` | `--json-schema <schema>` |
| JSON 事件流 | `--json` | `--output-format stream-json` |
| 非交互模式 | 默认 | `--print` |
| Schema 来源 | 仅文件路径 | 内联 JSON 字符串 或 文件 |





feishu robot webhook address: https://open.feishu.cn/open-apis/bot/v2/hook/4d2b8fc7-e50f-4174-b953-427761e74295



## feishu 启动命令
```bash
argusbot-daemon \
    --run-cd /Users/halllo/projects/local/ArgusBot \
    --run-max-rounds 500 \
    --bus-dir /Users/halllo/projects/local/ArgusBot/.argusbot/bus \
    --logs-dir /Users/halllo/projects/local/ArgusBot/.argusbot/logs \
    --run-planner-mode auto \
    --run-plan-mode fully-plan \
    --feishu-app-id cli_a93393044b395cb5 \
    --feishu-app-secret MdzD11wewnU7wD4ncuPrVfSYiSmE2tex \
    --feishu-chat-id oc_8517d59f85936c21772d9e2cd8e2e0e1 \
    --feishu-receive-id-type chat_id \
    --run-runner-backend claude \
    --run-runner-bin /opt/homebrew/bin/claude \
    --run-yolo \
    --run-resume-last-session
```

## 服务器启动命令
```bash
argusbot-daemon \
    --run-cd /home/ubuntu/projects/OmniSafeBench-MM \
    --run-max-rounds 500 \
    --bus-dir /home/ubuntu/projects/OmniSafeBench-MM/.argusbot/bus \
    --logs-dir /home/ubuntu/projects/OmniSafeBench-MM/.argusbot/logs \
    --run-planner-mode auto \
    --run-plan-mode fully-plan \
    --feishu-app-id cli_a933f2899df89cc4 \
    --feishu-app-secret 9MYP6nf3h5hLYrkmzgvUifuYkx7YtA7g \
    --feishu-chat-id oc_b8e9226c1a47753eee14291c627dc109 \
    --feishu-receive-id-type chat_id \
    --run-runner-backend claude \
    --run-runner-bin /home/ubuntu/node-v24.14.0-linux-x64/bin/claude \
    --run-yolo \
```