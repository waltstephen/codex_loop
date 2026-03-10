---
name: autonomous-research-loop
description: Operate Codex as a high-autonomy repository executor for implementation, debugging, and long-running research loops. Use when work requires strict git discipline (init, pull, commit, optional push), repeated continuation until the objective is fully complete, and strong runtime validation such as smoke runs (at least 100 steps), checkpoint integrity checks, and basic inference verification before stopping.
---

# Autonomous Research Loop

## Overview

Run autonomous engineering and experiment loops with strict acceptance gates.
Treat partial completion as unfinished work and continue until completion criteria are met.

## Operating Contract

Apply these rules for every run:

1. Initialize git context at start.
2. Keep repository synchronized if remote exists.
3. Continue execution until objective is completed or a hard blocker is proven.
4. Validate behavior with runnable checks, not only static edits.
5. Commit every meaningful fix.
6. Push when remote is configured and credentials allow push.

## Step 0: Bootstrap Git Safely

Execute at task start:

```bash
git init
```

Then detect repo and remote status:

```bash
git rev-parse --is-inside-work-tree
git remote -v
```

If a remote and tracked branch exist, try to sync before edits:

```bash
git pull --rebase --autostash
```

If pull fails, continue local work and record reason in status updates.

## Step 1: Define Completion Gates Up Front

Before coding, derive explicit objective gates:

1. Code/functionality gate: requested behavior is implemented.
2. Validation gate: tests or runnable checks pass.
3. Runtime gate for training/experiments: smoke run reaches at least 100 steps.
4. Artifact gate: at least one usable checkpoint is produced and readable.
5. Inference gate: perform a minimal inference/load check from produced checkpoint.

Do not stop at planning text. Execute commands to satisfy gates.

## Step 2: Execute in Persistent Loop

Use an iterative loop until gates are all green:

1. Inspect code and logs.
2. Implement next concrete fix.
3. Run targeted checks.
4. Re-evaluate all gates.
5. Continue immediately if any gate is red.

Never stop solely because one attempt failed. Try alternatives first.

## Step 3: Mandatory Smoke + Checkpoint + Inference

For experiment/training tasks, enforce:

1. Run smoke experiment to at least 100 steps.
2. Confirm checkpoint directory/file exists and is non-empty.
3. Confirm checkpoint can be loaded for at least one inference/eval call.

Use project-native entrypoints when available (train script, launcher, make target, etc.).
If multiple step flags exist, prefer `--max_steps 100` or equivalent.

Minimum evidence to report:

1. Exact command used.
2. Final step reached (>=100).
3. Checkpoint path and file size.
4. Inference/load command and success signal.

## Step 4: Commit Discipline

After each meaningful fix or validation milestone:

```bash
git add -A
git commit -m "<type>: <what changed and why>"
```

Commit frequently instead of batching unrelated changes.

Suggested commit pattern:

1. `fix:` for bug or runtime correction
2. `feat:` for new behavior
3. `chore:` for pipeline/tooling updates
4. `test:` for test-only changes

## Step 5: Push Policy

If branch has upstream and auth is available, push:

```bash
git push
```

If push fails (permission/network/protection), keep local commits and report exact reason.
Never delete commits to hide push failures.

## Step 6: Long-Running Monitoring Mode (24h style)

When asked to monitor long experiments:

1. Keep process alive and poll logs/status periodically.
2. Emit heartbeat updates at fixed interval (for example every 30 minutes).
3. Detect stalled runs (no log progress for a defined window).
4. Attempt one safe restart/recovery path if known.
5. Re-validate checkpoint and inference after recovery.

Treat monitoring tasks as unfinished until requested monitoring window and health checks are complete.

## Stop Conditions

Stop only when one of these is true:

1. All completion gates are green and evidence is recorded.
2. A hard blocker requires user-only input (credentials, missing private data, external approval).

When stopping, always provide:

1. What is done.
2. What was validated (with commands).
3. Latest commit hash(es).
4. Push status.
5. Remaining blockers, if any.

## Self-Optimization Rules

Use autonomous improvement behavior by default:

1. If a test/run fails, inspect logs and patch immediately.
2. If the same failure repeats, change approach (config, seed, batch size, dependency, launch args).
3. Prefer smallest-change fix that unblocks progress.
4. Preserve reproducibility: record commands, env assumptions, and outputs.
5. Do not require user micro-instructions for obvious next debugging step.
