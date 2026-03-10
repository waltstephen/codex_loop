from argparse import Namespace

from codex_autoloop.telegram_daemon import build_child_command


def test_build_child_command_includes_core_args() -> None:
    args = Namespace(
        codex_autoloop_bin="codex-autoloop",
        run_max_rounds=8,
        telegram_bot_token="123:abc",
        run_skip_git_repo_check=True,
        run_full_auto=False,
        run_yolo=True,
        run_check=["pytest -q", "python -m compileall ."],
        run_stall_soft_idle_seconds=1200,
        run_stall_hard_idle_seconds=10800,
        run_state_file=".codex_daemon/last_state.json",
        run_no_dashboard=True,
    )
    cmd = build_child_command(args=args, objective="do work", chat_id="42")
    assert cmd[0] == "codex-autoloop"
    assert "--telegram-bot-token" in cmd
    assert "--telegram-chat-id" in cmd
    assert "--check" in cmd
    assert "--yolo" in cmd
    assert "--skip-git-repo-check" in cmd
    assert "--no-dashboard" in cmd
    assert cmd[-1] == "do work"
