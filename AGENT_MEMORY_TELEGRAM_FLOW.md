# Agent Memory, Telegram, and Execution Flow

This document summarizes the current `ArgusBot` implementation after the Plan Agent integration.

## 1. Current Agents and Their Memory

### Main Agent

Role:

- Executes the actual implementation work.
- Runs in the persistent Codex thread for the task.

Memory sources:

- **Primary memory:** the resumed Codex session thread via `session_id`.
- **Visible operator input:** `broadcast` messages only.
- **Planner input in `auto` mode:** current plan follow-up (`next_explore`, `main_instruction`).

What it does **not** see:

- `plan`-only user direction.
- `review`-only audit criteria.

Persistence:

- Continues through the same Codex thread across rounds.
- Its last summary is captured into round state and becomes input to review/plan.

### Review Agent

Role:

- Evaluates whether the task is `done`, `continue`, or `blocked`.
- Produces per-round review summaries.

Memory sources:

- **No persistent Codex thread memory.**
- Fresh `codex exec` each round.
- Receives:
  - objective
  - latest main summary
  - acceptance check results
  - `broadcast` operator messages
  - `review`-only messages
  - current planner review guidance

Persistence:

- Writes `round_summary_markdown` every round.
- Writes `completion_summary_markdown` when the task is complete.
- These are persisted to review summary markdown files.

### Plan Agent

Role:

- Maintains the task structure.
- Decides what to explore next.
- Writes the overall planning summary.
- Runs only after a completed implementation/review phase.

Modes:

- `off`: disabled.
- `auto`: planner produces follow-up instructions for main and review.
- `record`: planner writes structure/documentation only and does not drive automatic follow-up behavior into main prompts.

Memory sources:

- **No persistent Codex thread memory.**
- Fresh `codex exec` each planning pass.
- Receives:
  - objective
  - latest review completion summary markdown
  - previous persisted plan overview markdown
  - `broadcast` operator messages
  - `plan`-only messages

Persistence:

- Writes `plan_overview.md`.
- Stores:
  - `next_explore`
  - `main_instruction`
  - `review_instruction`
  - `overview_markdown`

## 2. Current Persistent Record Files

These are the current record/working-memory artifacts in `ArgusBot`:

- `operator_messages.md`
  - All recorded operator input.
  - Includes audience tagging: `broadcast`, `plan`, `review`.
- `plan_overview.md`
  - Current overall planner summary.
  - Includes runtime data table.
- `review_summaries/index.md`
  - Index of review rounds.
- `review_summaries/round-XXX.md`
  - Reviewer summary for each round.
- `review_summaries/completion.md`
  - Final review completion summary when available.
- `state_file` JSON, if configured
  - Machine-readable runtime state, rounds, latest plan, latest review, `session_id`, etc.

Important limitation:

- This is currently a **record/state system**, not a semantic memory system like OpenClaw’s `memory_search` + indexed retrieval.

## 3. Telegram Features Available Now

### Loop Control

Available during an active loop:

- `/inject <instruction>`
  - Broadcast interrupt/update for the main loop.
- `/mode <off|auto|record>`
  - Hot-switch the current plan mode for the active loop.
- `/btw <question>`
  - Sends a question to a separate read-only side-agent.
  - It answers simple current-project questions without modifying code or interrupting the main loop.
- `/status`
  - Current loop status.
- `/stop`
  - Stop the active loop.
- `/help`
  - Command summary.

Plain text:

- Treated as `inject` in child loop control by default.

Voice/audio:

- Transcribed through Whisper when enabled.

### Plan-Specific Commands

Available now:

- `/plan <direction>`
  - Sent only to the Plan Agent.
  - Used for extensions, direction shifts, or long-horizon steering.
- `/show-plan`
  - Returns the current planner markdown summary.
- `/show-plan-context`
  - Returns the current plan direction plus plan-only and broadcast inputs.
- `/plan-md`
  - Alias for `/show-plan`.

### Review-Specific Commands

Available now:

- `/review <criteria>`
  - Sent only to the Review Agent.
  - Used to tighten acceptance criteria or audit rules.
- `/criteria <criteria>`
  - Alias for `/review`.
- `/show-review`
  - Returns the review summary index markdown.
- `/show-review <round>`
  - Returns a specific round review markdown.
- `/show-review-context`
  - Returns the current review direction, configured checks, and review-only criteria.
- `/review-md`
  - Alias for `/show-review`.

### Daemon Commands

Available through the Telegram daemon when idle or active:

- `/run <objective>`
  - Start a new run when idle.
- `/inject <instruction>`
  - If active: forward to child loop.
  - If idle: starts a run.
- `/mode <off|auto|record>`
  - Updates daemon default mode for future runs.
  - If a child run is active, also forwards the mode switch to the active child.
- `/btw <question>`
  - Calls a separate read-only side-agent.
  - Its memory is limited to the current project and prior `/btw` turns.
- `/plan <direction>`
  - Forward to active child plan agent.
- `/review <criteria>`
  - Forward to active child review agent.
- `/show-plan`
  - Read latest plan overview markdown.
- `/show-plan-context`
  - Read current plan direction and inputs.
- `/show-review [round]`
  - Read latest review summary markdown.
- `/show-review-context`
  - Read current review direction, checks, and criteria.
- `/status`
  - Daemon + child status.
- `/stop`
  - Stop active child run.
- `/daemon-stop`
  - Stop the daemon process.

## 4. Current Execution Flow

### High-Level Flow

1. Start loop with objective.
2. Run main agent.
3. Run acceptance checks.
4. Run review agent.
5. Persist round state + review markdown artifacts.
6. If the phase is complete (`review=done` and checks pass), optionally run planner.
7. Depending on planner mode and planner output, stop or enter the next follow-up phase.

### Detailed Round Behavior

#### Planner Phase

If planner is enabled and the current phase has completed successfully:

1. Read:
   - plan-visible operator messages
   - latest review completion summary
   - previous plan overview
2. Produce:
   - `follow_up_required`
   - `next_explore`
   - `main_instruction`
   - `review_instruction`
   - `overview_markdown`
3. Persist plan overview markdown.

#### Main Phase

1. Main agent runs in the persistent Codex thread.
2. It sees:
   - objective
   - `broadcast` operator messages
   - planner follow-up only in `auto` mode, and only after a previous phase completed and planner requested another phase
3. If interrupted by operator inject/stop:
   - loop records interruption
   - next round prompt is rebuilt accordingly

#### Check Phase

1. All configured `--check` commands run.
2. Results are collected into round state.

#### Review Phase

1. Review agent runs as a fresh Codex call.
2. It sees:
   - objective
   - main summary
   - checks
   - broadcast + review-only messages
   - planner review guidance
3. It outputs:
   - `status`
   - `confidence`
   - `reason`
   - `next_action`
   - `round_summary_markdown`
   - `completion_summary_markdown`

#### Persist Phase

Every round the loop writes:

- review markdown files
- state JSON, if configured
- operator message markdown, if configured

When a phase completes successfully and planner runs, it additionally writes:

- plan markdown file

### Post-Success Planner Decision

When `review=done` and all checks pass:

1. `off`
   - stop immediately.
2. `record`
   - run planner once to update structure/TODO docs, then stop.
3. `auto`
   - run planner once.
   - if `follow_up_required=false`, stop.
   - if `follow_up_required=true`, start the next follow-up execution phase using the planner output.

### Stop Conditions

The loop stops when one of these is true:

1. Reviewer returns `blocked`.
2. Repeated no-progress rounds exceed threshold.
3. `max_rounds` is reached.
4. Operator explicitly stops the run.
5. Reviewer returns `done` and all checks pass, and either:
   - plan mode is `off`, or
   - plan mode is `record`, or
   - plan mode is `auto` and planner says no automatic follow-up is required.

## 5. Important Reality Check

Current `ArgusBot` memory is best described as:

- **persistent execution state**
- **persistent summaries**
- **role-targeted operator context**
- **main-thread resume continuity**

It is **not yet**:

- semantic retrieval memory
- vector search memory
- cross-run knowledge base
- automatic durable-memory indexing like OpenClaw’s `memory_search`

So today:

- `main` has the strongest continuity because of `session_id` resume.
- `review` and `plan` rely on persisted summaries and role-scoped inputs, not their own resumed threads.
