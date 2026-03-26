# Recent Updates

Docs: [Main README](README.md) | [Quick Start](QUICKSTART.md) | [Contributing](CONTRIBUTING.md)

This file is the dated changelog for user-visible ArgusBot updates.

Update `Unreleased` in every user-visible feature merge, then roll those notes into a dated section when shipping a release or update batch.

Scope decision: include all user-visible changes, but group related minor items into concise user-facing update entries.

## Naming

- Use `Recent Updates` as the navigation label in `README.md`.
- Keep this file title aligned with that label.

## Update Policy

- Use dated sections as the primary grouping for this repo.
- Fill `Version` when a shipped release has a meaningful version number; otherwise keep `none`.
- Record every user-visible change in `Unreleased`, not only major releases.
- Skip internal-only refactors, test-only changes, and cleanup with no behavior change.
- Group related small changes by user-facing outcome instead of mirroring commit history.
- When shipping a release or update batch, move completed items into a dated section.

## Template

Use this shape for new dated entries:

```md
## YYYY-MM-DD
Version: vX.Y.Z / none

### Added

- New user-visible capability.

### Changed

- Existing behavior, workflow, or docs changed in a meaningful way.

### Fixed

- Bug fix with user-visible impact.
```

## Maintenance

- Follow the `Pull Request Checklist` and `Recent Updates Entry` sections in [CONTRIBUTING.md](CONTRIBUTING.md) when adding new notes here.
- Keep the live draft in `Unreleased`, then roll it into a dated entry when shipping a release or update batch.

## Unreleased

Version: none

### Added

- Added automatic final task report generation after reviewer `done`, with the report written to a Markdown file for final delivery.
- Added `--final-report-file` so runs can write the final handoff report to an explicit path.
- Added notifier delivery for the final task report when the file is ready.

### Changed

- Standardized the final handoff flow so the main agent is asked to write only the final report file during the final-report phase.
- Changed session planning semantics so auto planning/follow-up stays locked until `/plan <session goal>` confirms the overall goal for the current session.
- Changed the default daemon planner behavior to `execute-only`: planner updates and next-session suggestions still work, but follow-up does not auto-run until the session goal is explicitly confirmed.
- Improved `/run` conflict message: when `/run` is sent while another run is already active, the daemon now explains the command was treated as `/inject` and gives clear instructions for starting a fresh run (`/stop` → wait for confirmation → `/run` again).

### Fixed

- Fixed planner silently falling back to a generic snapshot when the model outputs common status aliases (`completed`, `in-progress`). Planner now normalizes these to the canonical values (`done`, `in_progress`) before validation.
- Fixed planner accepting `name` as a fallback key for `area` in workstreams, preventing valid model output from being rejected.
- Fixed planner context gap: planner now receives the main agent's actual last message so it can make informed follow-up decisions instead of relying solely on the reviewer's high-level summary.
- Added a local fallback final report writer when the main-agent final-report write step fails or leaves the target file unchanged.
- Stopped stale live-update backlog chunks from being delivered after a run has already completed or the final report is ready.
- Prevented `/btw` from misclassifying normal questions as file requests and returning unrelated README/files instead of the intended answer.
- Fixed a daemon recovery bug where an orphaned old run could keep rewriting prior log/report files and keep sending stale live updates after the current session was already done.

## 2026-03-18

Version: none

### Added

- Added multi-backend runner support for both `Codex CLI` and `Claude Code CLI`.
- Added `--runner-backend` and `--runner-bin` as the normalized runner selection interface.
- Added GitHub Copilot integration through local `copilot-proxy` support for Codex-based runs.
- Added BTW attachment confirmation commands: `/confirm-send` and `/cancel-send`.
- Added richer BTW attachment return support for Telegram and Feishu media/file uploads.
- Added stronger README coverage for dashboard exposure risk and remote-control credential safety.

### Changed

- Updated `argusbot init` setup flow to include backend choice during onboarding.
- Kept the same `/run`, `/inject`, `/btw`, planner, reviewer, and daemon operator flow across both backends.
- Improved Feishu documentation and operator-facing usage guidance in the main docs.
- Refreshed the community section and README structure to surface newer workflows more clearly.

### Fixed

- Fixed runner wiring to use `runner_bin` instead of the older Codex-specific parameter in the CLI path.
- Fixed the public entrypoint naming cleanup around `argusbot`.
- Fixed packaging metadata so subpackages are included correctly.
- Fixed Python 3.10 UTC compatibility issues.
- Fixed Claude live terminal display issues.

## 2026-03-17

Version: none

### Fixed

- Fixed Chinese character encoding issues in CLI terminal output.
- Updated contributor and project metadata documentation.

## Baseline

- Project package version in [pyproject.toml](pyproject.toml): `0.1.0`
- Current main docs entry point: [README.md](README.md)
- Quick start reference: [QUICKSTART.md](QUICKSTART.md)

## Related Docs

- Main overview: [README.md](README.md)
- Quick start: [QUICKSTART.md](QUICKSTART.md)
- Contribution guide: [CONTRIBUTING.md](CONTRIBUTING.md)
