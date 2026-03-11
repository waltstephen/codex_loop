from __future__ import annotations

import argparse
import getpass
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .model_catalog import MODEL_PRESETS, get_preset
from .planner_modes import (
    PLANNER_MODE_AUTO,
    PLANNER_MODE_CHOICES,
    planner_mode_description,
    planner_mode_label,
)
from .token_lock import acquire_token_lock


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.follow_up_auto_execute_seconds < 0:
        parser.error("--follow-up-auto-execute-seconds must be >= 0")

    codex_bin = shutil.which("codex")
    if not codex_bin:
        print("codex CLI not found in PATH. Install/configure codex first.", file=sys.stderr)
        raise SystemExit(2)

    if not check_codex_binary(codex_bin):
        print("codex CLI executable check failed.", file=sys.stderr)
        raise SystemExit(2)

    auth_ok = check_codex_auth(codex_bin=codex_bin, cwd=Path(args.run_cd).resolve(), timeout_seconds=45)
    if not auth_ok:
        print("Could not verify Codex auth by probe request.", file=sys.stderr)
        choice = prompt_input("Continue anyway? [y/N]: ", default="n").lower()
        if choice not in {"y", "yes"}:
            raise SystemExit(2)

    token = prompt_secret("Telegram bot token: ")
    if ":" not in token:
        print("Token format looks invalid. Expected <digits>:<secret>.", file=sys.stderr)
        raise SystemExit(2)
    chat_id = prompt_input("Telegram chat id (or 'auto'): ", default="auto").strip() or "auto"
    check_cmd = prompt_input(
        "Default check command (optional, leave empty for none): ",
        default="",
    ).strip()
    preset_names = ", ".join(p.name for p in MODEL_PRESETS)
    preset_name = args.run_model_preset
    if preset_name is None and args.run_main_model is None and args.run_reviewer_model is None:
        preset_name = prompt_model_choice()
    resolved_preset = get_preset(preset_name) if preset_name and preset_name.lower() != "custom" else None
    if preset_name and preset_name.lower() != "custom" and resolved_preset is None:
        print(f"Unknown model preset: {preset_name}", file=sys.stderr)
        raise SystemExit(2)
    if resolved_preset is not None:
        main_model = resolved_preset.main_model
        main_reasoning_effort = resolved_preset.main_reasoning_effort
        reviewer_model = resolved_preset.reviewer_model
        reviewer_reasoning_effort = resolved_preset.reviewer_reasoning_effort
    else:
        if args.run_main_model is not None or args.run_reviewer_model is not None:
            main_model = args.run_main_model
            main_reasoning_effort = args.run_main_reasoning_effort
            reviewer_model = args.run_reviewer_model
            reviewer_reasoning_effort = args.run_reviewer_reasoning_effort
        else:
            main_model = prompt_input("Main agent model (optional): ", default="").strip() or None
            main_reasoning_effort = (
                prompt_input("Main agent reasoning effort (low/medium/high/xhigh, optional): ", default="").strip()
                or None
            )
            reviewer_model = prompt_input("Reviewer agent model (optional): ", default="").strip() or None
            reviewer_reasoning_effort = (
                prompt_input(
                    "Reviewer agent reasoning effort (low/medium/high/xhigh, optional): ",
                    default="",
                ).strip()
                or None
            )
    planner_mode = args.run_planner_mode
    if planner_mode is None:
        planner_mode = prompt_planner_mode_choice()

    home_dir = Path(args.home_dir).resolve()
    bus_dir = home_dir / "bus"
    logs_dir = home_dir / "logs"
    home_dir.mkdir(parents=True, exist_ok=True)
    bus_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    if args.restart_existing:
        stop_existing_daemon(home_dir=home_dir, bus_dir=bus_dir)

    try:
        probe_lock = acquire_token_lock(
            token=token,
            owner_info={"pid": "setup-probe", "run_cd": str(Path(args.run_cd).resolve())},
            lock_dir=args.token_lock_dir,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
    else:
        probe_lock.release()

    config = {
        "telegram_bot_token": token,
        "telegram_chat_id": chat_id,
        "run_cd": str(Path(args.run_cd).resolve()),
        "run_check": (check_cmd if check_cmd else None),
        "run_max_rounds": args.run_max_rounds,
        "run_skip_git_repo_check": args.run_skip_git_repo_check,
        "run_full_auto": args.run_full_auto,
        "run_yolo": args.run_yolo,
        "run_resume_last_session": args.run_resume_last_session,
        "run_main_reasoning_effort": main_reasoning_effort,
        "run_reviewer_reasoning_effort": reviewer_reasoning_effort,
        "run_main_model": main_model,
        "run_reviewer_model": reviewer_model,
        "run_model_preset": (resolved_preset.name if resolved_preset else (preset_name or None)),
        "run_planner_mode": planner_mode,
        "follow_up_auto_execute_seconds": args.follow_up_auto_execute_seconds,
        "bus_dir": str(bus_dir),
        "logs_dir": str(logs_dir),
    }
    config_path = home_dir / "daemon_config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=True, indent=2), encoding="utf-8")
    config_path.chmod(0o600)

    daemon_log = home_dir / "daemon.out"
    daemon_prefix = resolve_daemon_launch_prefix()
    daemon_cmd = [
        *daemon_prefix,
        "--telegram-bot-token",
        token,
        "--telegram-chat-id",
        chat_id,
        "--run-cd",
        str(Path(args.run_cd).resolve()),
        "--run-max-rounds",
        str(args.run_max_rounds),
        "--bus-dir",
        str(bus_dir),
        "--logs-dir",
        str(logs_dir),
        "--token-lock-dir",
        args.token_lock_dir,
        "--run-planner-mode",
        planner_mode,
        "--follow-up-auto-execute-seconds",
        str(args.follow_up_auto_execute_seconds),
    ]
    if check_cmd:
        daemon_cmd.extend(["--run-check", check_cmd])
    if resolved_preset is not None:
        daemon_cmd.extend(["--run-model-preset", resolved_preset.name])
    else:
        if main_model:
            daemon_cmd.extend(["--run-main-model", main_model])
        if main_reasoning_effort:
            daemon_cmd.extend(["--run-main-reasoning-effort", main_reasoning_effort])
        if reviewer_model:
            daemon_cmd.extend(["--run-reviewer-model", reviewer_model])
        if reviewer_reasoning_effort:
            daemon_cmd.extend(["--run-reviewer-reasoning-effort", reviewer_reasoning_effort])
    if args.run_skip_git_repo_check:
        daemon_cmd.append("--run-skip-git-repo-check")
    if args.run_full_auto:
        daemon_cmd.append("--run-full-auto")
    if args.run_yolo:
        daemon_cmd.append("--run-yolo")
    else:
        daemon_cmd.append("--no-run-yolo")
    if args.run_resume_last_session:
        daemon_cmd.append("--run-resume-last-session")
    else:
        daemon_cmd.append("--no-run-resume-last-session")

    with daemon_log.open("a", encoding="utf-8") as f:
        proc = subprocess.Popen(
            daemon_cmd,
            stdout=f,
            stderr=f,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    time.sleep(1.0)
    if proc.poll() is not None:
        print("Daemon failed to start. Recent log:", file=sys.stderr)
        print(read_log_tail(daemon_log, max_lines=25), file=sys.stderr)
        raise SystemExit(2)

    pid_path = home_dir / "daemon.pid"
    pid_path.write_text(str(proc.pid), encoding="utf-8")
    pid_path.chmod(0o600)

    print("Setup completed.")
    print(f"Daemon started in background. pid={proc.pid}")
    print(f"Config: {config_path}")
    print(f"Log: {daemon_log}")
    print(f"Bus dir: {bus_dir}")
    print(f"Planner mode: {planner_mode} ({planner_mode_label(planner_mode)})")
    if planner_mode == PLANNER_MODE_AUTO:
        print(f"Follow-up auto execute: {args.follow_up_auto_execute_seconds}s")
    if resolved_preset is not None:
        print(
            "Model preset: "
            f"{resolved_preset.name} "
            f"({resolved_preset.main_model}/{resolved_preset.main_reasoning_effort} "
            f"/ {resolved_preset.reviewer_model}/{resolved_preset.reviewer_reasoning_effort})"
        )
    else:
        print(f"Main model: {main_model or '<daemon default>'} effort={main_reasoning_effort or '<default>'}")
        print(
            f"Reviewer model: {reviewer_model or '<daemon default>'} "
            f"effort={reviewer_reasoning_effort or '<default>'}"
        )
    print("")
    ctl_hint = resolve_daemon_ctl_hint()
    print("Terminal control examples:")
    print(f"  {ctl_hint} --bus-dir {bus_dir} run \"帮我在这个文件夹写一下pipeline\"")
    print(f"  {ctl_hint} --bus-dir {bus_dir} inject \"继续并优先修复测试\"")
    print(f"  {ctl_hint} --bus-dir {bus_dir} status")
    print(f"  {ctl_hint} --bus-dir {bus_dir} stop")
    print("")
    print("Telegram control examples:")
    print("  /run <objective>")
    print("  /inject <instruction>")
    print("  /status")
    print("  /stop")


def check_codex_binary(codex_bin: str) -> bool:
    try:
        completed = subprocess.run(
            [codex_bin, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception:
        return False
    return completed.returncode == 0


def check_codex_auth(*, codex_bin: str, cwd: Path, timeout_seconds: int) -> bool:
    try:
        completed = subprocess.run(
            [codex_bin, "exec", "--skip-git-repo-check", "--json", "Reply exactly: ok"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except Exception:
        return False
    text = (completed.stdout or "") + "\n" + (completed.stderr or "")
    lowered = text.lower()
    if "unauthorized" in lowered or "missing bearer" in lowered:
        return False
    return '"text":"ok"' in text or '"text": "ok"' in text


def resolve_daemon_launch_prefix() -> list[str]:
    daemon_bin = shutil.which("codex-autoloop-telegram-daemon")
    if daemon_bin:
        return [daemon_bin]
    return [sys.executable, "-m", "codex_autoloop.telegram_daemon"]


def resolve_daemon_ctl_hint() -> str:
    ctl_bin = shutil.which("codex-autoloop-daemon-ctl")
    if ctl_bin:
        return ctl_bin
    return f"{sys.executable} -m codex_autoloop.daemon_ctl"


def stop_existing_daemon(*, home_dir: Path, bus_dir: Path) -> None:
    pid_path = home_dir / "daemon.pid"
    daemon_running = False
    existing_pid = None
    if pid_path.exists():
        existing_pid = pid_path.read_text(encoding="utf-8").strip()
        if existing_pid and existing_pid.isdigit():
            daemon_running = subprocess.run(
                ["kill", "-0", existing_pid],
                capture_output=True,
                text=True,
            ).returncode == 0
    if not daemon_running:
        return

    ctl_bin = shutil.which("codex-autoloop-daemon-ctl")
    if ctl_bin:
        subprocess.run(
            [ctl_bin, "--bus-dir", str(bus_dir), "daemon-stop"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    else:
        subprocess.run(
            [sys.executable, "-m", "codex_autoloop.daemon_ctl", "--bus-dir", str(bus_dir), "daemon-stop"],
            capture_output=True,
            text=True,
            timeout=10,
        )

    if existing_pid and existing_pid.isdigit():
        time.sleep(1.0)
        still_running = subprocess.run(
            ["kill", "-0", existing_pid],
            capture_output=True,
            text=True,
        ).returncode == 0
        if still_running:
            subprocess.run(["kill", existing_pid], capture_output=True, text=True, timeout=5)
            time.sleep(1.0)
            still_running = subprocess.run(
                ["kill", "-0", existing_pid],
                capture_output=True,
                text=True,
            ).returncode == 0
            if still_running:
                subprocess.run(["kill", "-9", existing_pid], capture_output=True, text=True, timeout=5)

    try:
        pid_path.unlink(missing_ok=True)
    except Exception:
        pass


def read_log_tail(path: Path, max_lines: int) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return "<unable to read daemon log>"
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[-max_lines:])


def prompt_input(prompt: str, default: str) -> str:
    raw = input(prompt).strip()
    if not raw:
        return default
    return raw


def prompt_secret(prompt: str) -> str:
    return getpass.getpass(prompt).strip()


def prompt_model_choice() -> str:
    print("Choose a model preset:")
    for idx, preset in enumerate(MODEL_PRESETS, start=1):
        print(
            f"  {idx}. {preset.name}: "
            f"main={preset.main_model}/{preset.main_reasoning_effort}, "
            f"reviewer={preset.reviewer_model}/{preset.reviewer_reasoning_effort}"
        )
    print(f"  {len(MODEL_PRESETS) + 1}. custom")
    raw = prompt_input("Preset number: ", default="1").strip()
    try:
        index = int(raw)
    except ValueError:
        return "quality"
    if 1 <= index <= len(MODEL_PRESETS):
        return MODEL_PRESETS[index - 1].name
    return "custom"


def prompt_planner_mode_choice() -> str:
    print("Choose a planner mode:")
    for idx, mode in enumerate(PLANNER_MODE_CHOICES, start=1):
        print(f"  {idx}. {planner_mode_label(mode)} - {planner_mode_description(mode)}")
    raw = prompt_input("Planner mode number [2]: ", default="2").strip()
    try:
        index = int(raw)
    except ValueError:
        return PLANNER_MODE_AUTO
    if 1 <= index <= len(PLANNER_MODE_CHOICES):
        return PLANNER_MODE_CHOICES[index - 1]
    return PLANNER_MODE_AUTO


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex-autoloop-setup",
        description="Interactive setup: verify codex, collect Telegram token, and launch daemon in background.",
    )
    parser.add_argument(
        "--home-dir",
        default=".codex_daemon",
        help="Directory to store daemon config/log/pid/bus files.",
    )
    parser.add_argument(
        "--run-cd",
        default=".",
        help="Working directory for launched codex-autoloop runs.",
    )
    parser.add_argument("--run-max-rounds", type=int, default=50, help="Default max rounds for daemon-launched runs.")
    parser.add_argument(
        "--run-skip-git-repo-check",
        action="store_true",
        help="Pass --skip-git-repo-check for daemon-launched runs.",
    )
    parser.add_argument("--run-full-auto", action="store_true", help="Pass --full-auto for daemon-launched runs.")
    parser.add_argument(
        "--run-yolo",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable --yolo for daemon-launched runs (default: enabled).",
    )
    parser.add_argument(
        "--run-resume-last-session",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Resume from the last saved session_id when daemon receives a new run while idle.",
    )
    parser.add_argument(
        "--run-model-preset",
        default=None,
        help="Optional preset name for daemon-launched models. Interactive setup also prompts for this.",
    )
    parser.add_argument(
        "--run-planner-mode",
        default=None,
        choices=PLANNER_MODE_CHOICES,
        help="Planner mode for daemon-launched runs. Interactive setup prompts when omitted.",
    )
    parser.add_argument(
        "--run-main-model",
        default=None,
        help="Override main agent model for daemon-launched runs.",
    )
    parser.add_argument(
        "--run-main-reasoning-effort",
        default=None,
        choices=["low", "medium", "high", "xhigh"],
        help="Override main agent reasoning effort for daemon-launched runs.",
    )
    parser.add_argument(
        "--run-reviewer-model",
        default=None,
        help="Override reviewer agent model for daemon-launched runs.",
    )
    parser.add_argument(
        "--run-reviewer-reasoning-effort",
        default=None,
        choices=["low", "medium", "high", "xhigh"],
        help="Override reviewer agent reasoning effort for daemon-launched runs.",
    )
    parser.add_argument(
        "--token-lock-dir",
        default="/tmp/codex-autoloop-token-locks",
        help="Global lock directory to enforce one daemon per Telegram token.",
    )
    parser.add_argument(
        "--restart-existing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Stop an existing daemon under the same home-dir before starting a new one.",
    )
    parser.add_argument(
        "--follow-up-auto-execute-seconds",
        type=int,
        default=600,
        help="Auto execute planner follow-up after this many seconds in auto mode.",
    )
    return parser


if __name__ == "__main__":
    main()
