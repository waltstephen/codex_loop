# Agent 记忆、Telegram 功能与执行流程

这份文档总结当前 `ArgusBot` 在接入 Plan Agent 之后的实现状态。

## 1. 当前有哪些 Agent，以及它们的记忆来自哪里

### Main Agent

角色：

- 负责真正执行实现工作。
- 在同一个 Codex 线程里持续运行。

记忆来源：

- **最主要的记忆**：通过 `session_id` 续跑的 Codex 会话线程。
- **可见的用户输入**：只能看到 `broadcast` 类型的消息。
- **`auto` 模式下的 planner 输入**：当前 plan 生成的 follow-up 指令，包括 `next_explore` 和 `main_instruction`。

它看不到：

- `plan` 专属方向输入。
- `review` 专属审核标准。

持久化方式：

- 跨轮复用同一个 Codex thread。
- 它本轮的最后总结会进入 round state，并作为 review / plan 的输入。

### Review Agent

角色：

- 判断当前任务应该是 `done`、`continue` 还是 `blocked`。
- 负责产出每轮 review 总结。

记忆来源：

- **没有持久线程记忆。**
- 每一轮都是一次新的 `codex exec`。
- 它收到的上下文包括：
  - objective
  - 最新 main summary
  - acceptance checks 结果
  - `broadcast` 用户消息
  - `review` 专属消息
  - planner 给它的 review 指导

持久化方式：

- 每轮写 `round_summary_markdown`。
- 完成时写 `completion_summary_markdown`。
- 这些内容会被写入 review summary markdown 文件。

### Plan Agent

角色：

- 维护整体任务结构。
- 决定下一步该探索什么。
- 写总体的规划总结。
- 只在一个实现 / review phase 成功收尾之后运行。

模式：

- `off`：关闭。
- `auto`：planner 会给 main 和 review 生成 follow-up 指令。
- `record`：planner 只维护结构和文档，不把 follow-up 自动注入 main 的执行链路。

记忆来源：

- **没有持久线程记忆。**
- 每次都是新的 `codex exec`。
- 它收到的上下文包括：
  - objective
  - 最新 review completion summary markdown
  - 上一次持久化下来的 `plan_overview.md`
  - `broadcast` 用户消息
  - `plan` 专属消息

持久化方式：

- 写 `plan_overview.md`。
- 持久化内容包括：
  - `next_explore`
  - `main_instruction`
  - `review_instruction`
  - `overview_markdown`

## 2. 当前有哪些持久化记录文件

现在 `ArgusBot` 里已经实现的记录/工作记忆文件包括：

- `operator_messages.md`
  - 记录所有 operator 输入。
  - 现在带受众标签：`broadcast`、`plan`、`review`。
- `plan_overview.md`
  - Plan Agent 的整体总结。
  - 带运行时数据表。
- `review_summaries/index.md`
  - Review 各轮的索引。
- `review_summaries/round-XXX.md`
  - 每一轮 reviewer 的总结。
- `review_summaries/completion.md`
  - 最终完成时的 reviewer 总结。
- `state_file` JSON（如果配置了）
  - 机器可读的运行状态，包括 rounds、latest plan、latest review、`session_id` 等。

重要限制：

- 这套东西目前是一个**记录 / 状态系统**，还不是像 OpenClaw 那样带语义检索能力的完整记忆系统。

## 3. 当前 Telegram 能用的功能

### Loop 控制

在 active loop 运行时可用：

- `/inject <instruction>`
  - 广播式中断 / 更新，作用于主循环。
- `/mode <off|auto|record>`
  - 对当前 active loop 进行 plan mode 热切换。
- `/btw <question>`
  - 发给一个独立的只读 side-agent。
  - 只用于回答当前项目里的简单问题，不改代码，也不打断主 loop。
- `/status`
  - 查看当前 loop 状态。
- `/stop`
  - 停掉当前 loop。
- `/help`
  - 查看命令说明。

纯文本消息：

- 默认会被当作 `inject`。

语音 / 音频：

- 如果启用了 Whisper，会先转写再当文本命令处理。

### Plan 相关命令

当前已支持：

- `/plan <direction>`
  - 只发给 Plan Agent。
  - 用于扩展方向、任务重心调整、长期规划输入。
- `/show-plan`
  - 返回当前 planner 写出的 markdown 总结。
- `/show-plan-context`
  - 返回当前 plan 方向和 plan-only / broadcast 输入。
- `/plan-md`
  - `/show-plan` 的别名。

### Review 相关命令

当前已支持：

- `/review <criteria>`
  - 只发给 Review Agent。
  - 用于补充验收标准或审核规则。
- `/criteria <criteria>`
  - `/review` 的别名。
- `/show-review`
  - 返回 review summary 的索引 markdown。
- `/show-review <round>`
  - 返回指定轮次的 review markdown。
- `/show-review-context`
  - 返回当前 review 方向、acceptance checks 和 review-only criteria。
- `/review-md`
  - `/show-review` 的别名。

### Daemon 命令

在 Telegram daemon 模式下，空闲或运行中都可用：

- `/run <objective>`
  - 空闲时启动一个新 run。
- `/inject <instruction>`
  - 如果当前有 child run：转发给 child loop。
  - 如果当前空闲：直接启动一个 run。
- `/mode <off|auto|record>`
  - 更新 daemon 未来 run 的默认 mode。
  - 如果当前 child 正在运行，也会同时转发给 active child。
- `/btw <question>`
  - 调用一个独立的只读 side-agent。
  - 这个 agent 的记忆只包含当前项目和 `/btw` 对话，不会打断主执行链。
- `/plan <direction>`
  - 转发给当前 child 的 Plan Agent。
- `/review <criteria>`
  - 转发给当前 child 的 Review Agent。
- `/show-plan`
  - 读取最新的 plan overview markdown。
- `/show-plan-context`
  - 读取当前 plan 方向和输入。
- `/show-review [round]`
  - 读取最新的 review summary markdown。
- `/show-review-context`
  - 读取当前 review 方向、checks 和 criteria。
- `/status`
  - 查看 daemon + child 状态。
- `/stop`
  - 停掉当前 child run。
- `/daemon-stop`
  - 停掉 daemon 进程。

## 4. 当前执行流程

### 高层流程

1. 用 objective 启动 loop。
2. 跑 main agent。
3. 跑 acceptance checks。
4. 跑 review agent。
5. 持久化 round state 和 review markdown。
6. 如果这个 phase 成功结束（`review=done` 且 checks 通过），再决定是否跑 planner。
7. 根据 planner 模式和 planner 输出，决定停止还是进入下一条 follow-up 执行链。

### 每轮更细的行为

#### Planner 阶段

如果 planner 启用，而且当前 phase 已经成功完成：

1. 读取：
   - plan 可见的 operator 消息
   - 最新 review completion summary
   - 上一版 plan overview
2. 产出：
   - `follow_up_required`
   - `next_explore`
   - `main_instruction`
   - `review_instruction`
   - `overview_markdown`
3. 持久化 plan overview markdown。

#### Main 阶段

1. Main Agent 在持久 Codex thread 中执行。
2. 它会看到：
   - objective
   - `broadcast` 类型 operator 消息
   - 只有在 `auto` 模式下、且前一个 phase 完成后 planner 明确要求 follow-up 时，才会看到 planner 的 follow-up
3. 如果被 operator inject / stop：
   - loop 会记录这次中断
   - 下一轮 prompt 会按新状态重建

#### Check 阶段

1. 运行所有配置的 `--check` 命令。
2. 收集结果并写入 round state。

#### Review 阶段

1. Review Agent 以一次新的 Codex 调用运行。
2. 它会看到：
   - objective
   - main summary
   - checks
   - `broadcast + review-only` 消息
   - planner 给它的 review 指导
3. 它会输出：
   - `status`
   - `confidence`
   - `reason`
   - `next_action`
   - `round_summary_markdown`
   - `completion_summary_markdown`

#### Persist 阶段

每一轮 loop 会写出：

- review markdown 文件
- state JSON（如果配置了）
- operator message markdown（如果配置了）

如果 phase 成功完成且 planner 被触发，还会额外写出：

- plan markdown 文件

### 成功收尾后的 Planner 决策

当 `review=done` 且所有 checks 都通过时：

1. `off`
   - 直接结束。
2. `record`
   - planner 跑一次，只更新结构 / TODO 文档，然后结束。
3. `auto`
   - planner 跑一次。
   - 如果 `follow_up_required=false`，结束。
   - 如果 `follow_up_required=true`，基于 planner 输出进入下一条 follow-up 执行链。

### 停止条件

出现以下任一条件时停止：

1. Reviewer 返回 `blocked`。
2. 连续无进展轮数超过阈值。
3. 到达 `max_rounds`。
4. Operator 显式停止。
5. Reviewer 返回 `done` 且 checks 全通过，并且满足以下任一条件：
   - plan mode 是 `off`
   - plan mode 是 `record`
   - plan mode 是 `auto`，但 planner 判定不需要自动 follow-up

## 5. 当前实现的现实边界

现在 `ArgusBot` 的记忆更准确地说是：

- **持久化执行状态**
- **持久化总结文档**
- **按角色分流的 operator 上下文**
- **main thread 的续跑连续性**

它**还不是**：

- 语义检索记忆
- 向量搜索记忆
- 跨 run 的知识库
- 像 OpenClaw `memory_search` 那样的自动 durable-memory 索引系统

所以当前状态是：

- `main` 的连续性最强，因为它依赖 `session_id` resume。
- `review` 和 `plan` 依赖的是持久化总结和角色定向输入，不是它们自己的续跑线程。
