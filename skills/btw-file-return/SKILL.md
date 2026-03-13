---
name: btw-file-return
description: Detect when a BTW question is asking for project files, screenshots, or effect images, then return the most relevant local file paths quickly.
---

# BTW File Return

This skill is used by the BTW side-agent.

Purpose:

- Recognize file/image requests in BTW conversations.
- Search only inside the current project.
- Prefer quick attachment return over a long language-model answer.

Behavior:

1. Read-only only.
2. Never modify files.
3. Prefer explicit filename matches first.
4. For image-oriented requests, prefer image extensions and preview/output-like directories.
5. For general file requests, allow docs, config files, code files, and artifacts.

Rules and scoring preferences are stored in `config.json`.
