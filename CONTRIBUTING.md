# Contributing

Thanks for your interest in improving `ArgusBot`.

## How to Contribute

1. Open an issue for bugs, regressions, or feature requests.
2. Create a focused branch for your change.
3. Keep pull requests small and testable.
4. Run relevant tests before submitting.
5. Include clear context in commit messages and PR descriptions.

## Pull Request Checklist

1. Code and docs are updated together when behavior changes.
2. Update [Recent Updates](WHATS_NEW.md) in the same PR for every user-visible change; skip it for internal-only refactors, test-only changes, or no-behavior cleanup.
3. Keep new `Recent Updates` notes in `Unreleased`, then roll them into a dated entry when shipping a release or update batch.
4. Reuse the entry shape documented in the `Template` section of [WHATS_NEW.md](WHATS_NEW.md) so updates stay consistent.
5. New behavior is covered by tests, or rationale is explained.
6. Existing tests pass locally.
7. No secrets or private tokens are included.

## Recent Updates Entry

- Scope: add every user-visible change to `Unreleased`, but group related small items into concise user-facing notes.
- Primary grouping: use dated sections when shipping a release or update batch; keep `Version: none` unless a meaningful shipped version exists.

Sample entry:

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

## Project Contributors

- **Yijia Fan**: Original Contributor and original migration source for ArgusBot ([waltstephen](https://github.com/waltstephen)).
- **Zimo Wen**: Co-Original Contributor ([nssmd](https://github.com/nssmd)).
- **Boxiu Li**: Teams bot, Co-Original Contributor, and provider of API support during development ([lbx154](https://github.com/lbx154)).
- **Kaitong Cai**: Lead for the Feishu integration ([CaiKaitong](https://github.com/CaiKaitong)).
- **Zikai Zhou**: Improved Telegram image reply performance ([Klayand](https://github.com/Klayand)).
- **Lifeng Zhuo**: Added support for Qwen models ([zhuolifeng](https://github.com/zhuolifeng)).
- **ReinerBRO**: Successfully enabled support for the ClaudeCode CIL backend ([ReinerBRO](https://github.com/ReinerBRO)).
- **Mowenhao**: Claudecode adaptation and cil optimization ([Mowenhao13](https://github.com/Mowenhao13)).

## Acknowledgements

Special thanks to Microsoft Research Asia for supporting this project.
