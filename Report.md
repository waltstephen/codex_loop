# ArgusBot 项目结构分析报告

**生成日期:** 2026-03-17

---

## 1. 项目概述

ArgusBot 是一个 Python supervisor 插件，用于 Codex CLI 和 Claude Code CLI 的自动循环执行器。它通过多 agent 协作机制解决了"agent 过早停止并请求下一步指令"的问题。

**核心机制:**
- **Main Agent**: 执行实际任务
- **Reviewer Sub-agent**: 评估完成情况 (`done` / `continue` / `blocked`)
- **Planner Sub-agent**: 维护实时计划视图并提出下一 session 目标

---

## 2. 目录结构总览

```
ArgusBot/
├── codex_autoloop/       # 核心源代码目录 (39 个子目录，68 个 Python 文件)
├── claude_autoloop/      # Claude Code CLI 适配层
├── tests/                # 测试目录 (29 个测试文件)
├── scripts/              # 工具脚本 (9 个子目录)
├── skills/               # 技能模块 (5 个子目录)
├── Feishu_readme/        # 飞书文档资源
├── .github/workflows/    # GitHub Actions CI/CD
├── .argusbot/            # 运行时配置和日志
├── .venv/                # Python 虚拟环境
└── claude_test/          # Claude 测试目录
```

---

## 3. 核心源代码结构 (`codex_autoloop/`)

### 3.1 核心引擎层 (`core/`)
| 文件 | 职责 |
|------|------|
| `engine.py` | LoopEngine - 核心循环引擎 |
| `ports.py` | 事件端口接口定义 |
| `state_store.py` | 状态存储和事件处理 |

### 3.2 适配器层 (`adapters/`)
| 文件 | 职责 |
|------|------|
| `control_channels.py` | 控制通道适配 |
| `event_sinks.py` | 事件输出适配 |

### 3.3 应用层 (`apps/`)
| 文件 | 职责 |
|------|------|
| `shell_utils.py` | Shell 工具函数 |

### 3.4 主要组件模块
| 文件 | 代码行数 | 职责 |
|------|----------|------|
| `codexloop.py` | 主循环入口 | 单字命令 `argusbot` 实现 |
| `orchestrator.py` | 编排器 | 协调执行流程 |
| `reviewer.py` | 评审器 | 任务完成度评估 |
| `planner.py` | 规划器 | 工作计划维护 |
| `codex_runner.py` | 执行器 | Codex CLI 调用 |
| `checks.py` | 验收检查 | 验证检查命令 |
| `models.py` | 数据模型 | 核心数据结构定义 |
| `stall_subagent.py` | 停滞检测 | agent 停滞诊断 |

### 3.5 控制通道模块
| 文件 | 职责 |
|------|------|
| `telegram_control.py` | Telegram 控制通道 |
| `telegram_notifier.py` | Telegram 通知推送 |
| `telegram_daemon.py` | Telegram 守护进程 |
| `feishu_adapter.py` | 飞书适配器 |
| `daemon_bus.py` | JSONL 命令总线 |
| `daemon_ctl.py` | 守护进程控制 |
| `local_control.py` | 本地终端控制 |

### 3.6 工具和辅助模块
| 文件 | 职责 |
|------|------|
| `model_catalog.py` | 模型目录查询 |
| `setup_wizard.py` | 交互式安装向导 |
| `token_lock.py` | Token 独占锁 |
| `copilot_proxy.py` | GitHub Copilot 代理 |
| `dashboard.py` | Web 仪表板 |
| `live_updates.py` | 实时更新推送 |
| `attachment_policy.py` | 附件上传策略 |

---

## 4. 测试结构 (`tests/`)

测试文件覆盖所有核心组件：

| 测试文件 | 被测组件 |
|----------|----------|
| `test_codexloop.py` | 主循环 |
| `test_orchestrator.py` | 编排器 |
| `test_reviewer.py` | Reviewer |
| `test_planner.py` | Planner |
| `test_engine.py` | LoopEngine |
| `test_codex_runner.py` | Codex 执行器 |
| `test_telegram_*.py` | Telegram 组件 |
| `test_feishu_adapter.py` | 飞书适配器 |
| `test_dashboard.py` | 仪表板 |
| `test_stall_subagent.py` | 停滞检测 |
| `test_attachment_policy.py` | 附件策略 |
| `test_token_lock.py` | Token 锁 |
| `test_model_catalog.py` | 模型目录 |
| `test_setup_wizard.py` | 安装向导 |

**测试资源:** `tests/assets/` - 测试数据文件

---

## 5. 入口点命令 (pyproject.toml)

```
argusbot              - 单字入口 (自动附加监控)
argusbot-run          - 运行循环
argusbot-daemon       - Telegram/Feishu 守护进程
argusbot-daemon-ctl   - 守护进程控制
argusbot-setup        - 交互式安装向导
argusbot-models       - 模型目录查询
```

---

## 6. 数据模型 (models.py)

### ReviewDecision
```python
status: Literal["done", "continue", "blocked"]
confidence: float
reason: str
next_action: str
round_summary_markdown: str
completion_summary_markdown: str
```

### PlanDecision
```python
follow_up_required: bool
next_explore: str
main_instruction: str
review_instruction: str
overview_markdown: str
```

### PlanSnapshot
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

---

## 7. 项目统计

| 指标 | 数量 |
|------|------|
| Python 源文件 (不含.venv) | 68 个 |
| 源代码总行数 | ~14,506 行 |
| 测试文件 | 29 个 |
| 核心子目录 | 3 个 (core, adapters, apps) |
| 控制通道 | 3 个 (Telegram, Feishu, Terminal) |
| 文档文件 | 8 个 (README, ARCHITECTURE, CLAUDE.md 等) |

---

## 8. 架构层次

```
┌─────────────────────────────────────────────────────────────┐
│                      ArgusBot                                │
├─────────────────────────────────────────────────────────────┤
│  Apps Layer (应用层)                                         │
│  - cli_app, daemon_app, shell_utils                         │
├─────────────────────────────────────────────────────────────┤
│  Adapters Layer (适配器层)                                   │
│  - control_channels, event_sinks                            │
├─────────────────────────────────────────────────────────────┤
│  Core Layer (核心层)                                         │
│  - engine, state_store, ports                               │
├─────────────────────────────────────────────────────────────┤
│  Control Channels: Telegram | Feishu | Terminal (CLI)       │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. 关键设计特点

1. **三层架构**: core (纯循环运行时) / adapters (集成层) / apps (可执行 shell)
2. **多控制通道**: 支持 Telegram、飞书、本地终端三种控制方式
3. **持久化状态**: JSONL 事件流、Markdown 状态文件、运行存档
4. **安全机制**: Token 独占锁、停滞检测、最大轮次限制
5. **可扩展性**: 适配器模式便于添加新的控制通道和输出表面

---

## 10. 配置文件

| 文件 | 用途 |
|------|------|
| `pyproject.toml` | Python 项目配置和入口点定义 |
| `CLAUDE.md` | Claude Code 项目指令和远程 SSH 配置 |
| `.argusbot/` | 运行时配置、状态和日志目录 |

---

*报告生成完成*


python -m codex_autoloop.cli "访问本地~/projects/目录 列出里面的内容" \
      --runner-backend claude \
      --yolo \
      --max-rounds 1 \
      --skip-git-repo-check \
      --live-terminal

python -m codex_autoloop.cli "访问本地~/projects/目录 列出里面的内容" \
      --runner-backend claude \
      --yolo \
      --max-rounds 2 \
      --skip-git-repo-check \
      --dashboard \
      --dashboard-host 127.0.0.1 \
      --dashboard-port 8787

argusbot-run "访问本地~/projects/local/目录 列出里面的内容" \
      --runner-backend claude \
      --yolo \
      --max-rounds 2 \
      --skip-git-repo-check \
      --verbose-events