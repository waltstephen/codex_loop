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

## Unreleased

Version: none

### Added

- Added automatic final task report generation after reviewer `done`, with the report written to a Markdown file for final delivery.
- Added `--final-report-file` so runs can write the final handoff report to an explicit path.
- Added notifier delivery for the final task report when the file is ready.

### Changed

- Standardized the final handoff flow so the main agent is asked to write only the final report file during the final-report phase.

### Fixed

- Added a local fallback final report writer when the main-agent final-report write step fails or leaves the target file unchanged.

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
