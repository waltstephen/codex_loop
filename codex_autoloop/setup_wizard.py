from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .apps.shell_utils import looks_like_bot_token
from .daemon_bus import read_status
from .model_catalog import MODEL_PRESETS, ModelPreset, get_preset
from .telegram_notifier import resolve_chat_id
from .token_lock import acquire_token_lock, default_token_lock_dir

VALID_REASONING_EFFORTS = {"low", "medium", "high", "xhigh"}


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

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
    if not looks_like_bot_token(token):
        print("Token format looks invalid. Expected <digits>:<secret>.", file=sys.stderr)
        raise SystemExit(2)
    requested_chat_id = prompt_input("Telegram chat id (or 'auto'): ", default="auto").strip() or "auto"
    chat_id = resolve_effective_chat_id(
        bot_token=token,
        requested_chat_id=requested_chat_id,
        timeout_seconds=120,
    )
    check_cmd = prompt_input(
        "Default check command (optional, leave empty for none): ",
        default="",
    ).strip()
    preset_name = args.run_model_preset
    if (
        preset_name is None
        and args.run_main_model is None
        and args.run_reviewer_model is None
        and args.run_plan_model is None
    ):
        preset_name = prompt_model_choice()
    resolved_preset = get_preset(preset_name) if preset_name and preset_name.lower() != "custom" else None
    if preset_name and preset_name.lower() != "custom" and resolved_preset is None:
        print(f"Unknown model preset: {preset_name}", file=sys.stderr)
        raise SystemExit(2)
    if resolved_preset is not None or _has_explicit_run_model_override(args):
        (
            main_model,
            main_reasoning_effort,
            reviewer_model,
            reviewer_reasoning_effort,
            plan_model,
            plan_reasoning_effort,
        ) = resolve_run_model_settings(args=args, preset=resolved_preset)
    else:
        try:
            main_model = prompt_input("Main agent model (optional): ", default="").strip() or None
            main_reasoning_effort = normalize_reasoning_effort(
                prompt_input("Main agent reasoning effort (low/medium/high/xhigh, optional): ", default=""),
                field_name="Main agent reasoning effort",
            )
            reviewer_model = prompt_input("Reviewer agent model (optional): ", default="").strip() or None
            reviewer_reasoning_effort = normalize_reasoning_effort(
                prompt_input(
                    "Reviewer agent reasoning effort (low/medium/high/xhigh, optional): ",
                    default="",
                ),
                field_name="Reviewer agent reasoning effort",
            )
            plan_model = prompt_input("Plan agent model (optional): ", default="").strip() or None
            plan_reasoning_effort = normalize_reasoning_effort(
                prompt_input(
                    "Plan agent reasoning effort (low/medium/high/xhigh, optional): ",
                    default="",
                ),
                field_name="Plan agent reasoning effort",
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(2)

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
        "run_plan_mode": args.run_plan_mode,
        "run_main_reasoning_effort": main_reasoning_effort,
        "run_reviewer_reasoning_effort": reviewer_reasoning_effort,
        "run_plan_reasoning_effort": plan_reasoning_effort,
        "run_main_model": main_model,
        "run_reviewer_model": reviewer_model,
        "run_plan_model": plan_model,
        "run_model_preset": (resolved_preset.name if resolved_preset else (preset_name or None)),
        "codex_autoloop_bin": None,
        "bus_dir": str(bus_dir),
        "logs_dir": str(logs_dir),
    }
    config_path = home_dir / "daemon_config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=True, indent=2), encoding="utf-8")
    config_path.chmod(0o600)

    daemon_log = home_dir / "daemon.out"
    daemon_prefix = resolve_daemon_launch_prefix()
    codex_autoloop_bin = resolve_codex_autoloop_bin(home_dir)
    config["codex_autoloop_bin"] = codex_autoloop_bin
    config_path.write_text(json.dumps(config, ensure_ascii=True, indent=2), encoding="utf-8")
    daemon_cmd = [
        *daemon_prefix,
        "--telegram-bot-token",
        token,
        "--telegram-chat-id",
        chat_id,
        "--codex-autoloop-bin",
        codex_autoloop_bin,
        "--run-cd",
        str(Path(args.run_cd).resolve()),
        "--run-max-rounds",
        str(args.run_max_rounds),
        "--run-plan-mode",
        args.run_plan_mode,
        "--bus-dir",
        str(bus_dir),
        "--logs-dir",
        str(logs_dir),
        "--token-lock-dir",
        args.token_lock_dir,
    ]
    if check_cmd:
        daemon_cmd.extend(["--run-check", check_cmd])
    if resolved_preset is not None:
        daemon_cmd.extend(["--run-model-preset", resolved_preset.name])
    daemon_main_model = args.run_main_model if resolved_preset is not None else main_model
    daemon_main_reasoning_effort = args.run_main_reasoning_effort if resolved_preset is not None else main_reasoning_effort
    daemon_reviewer_model = args.run_reviewer_model if resolved_preset is not None else reviewer_model
    daemon_reviewer_reasoning_effort = (
        args.run_reviewer_reasoning_effort if resolved_preset is not None else reviewer_reasoning_effort
    )
    daemon_plan_model = args.run_plan_model if resolved_preset is not None else plan_model
    daemon_plan_reasoning_effort = (
        args.run_plan_reasoning_effort if resolved_preset is not None else plan_reasoning_effort
    )
    if daemon_main_model:
        daemon_cmd.extend(["--run-main-model", daemon_main_model])
    if daemon_main_reasoning_effort:
        daemon_cmd.extend(["--run-main-reasoning-effort", daemon_main_reasoning_effort])
    if daemon_reviewer_model:
        daemon_cmd.extend(["--run-reviewer-model", daemon_reviewer_model])
    if daemon_reviewer_reasoning_effort:
        daemon_cmd.extend(["--run-reviewer-reasoning-effort", daemon_reviewer_reasoning_effort])
    if daemon_plan_model:
        daemon_cmd.extend(["--run-plan-model", daemon_plan_model])
    if daemon_plan_reasoning_effort:
        daemon_cmd.extend(["--run-plan-reasoning-effort", daemon_plan_reasoning_effort])
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

    status_path = bus_dir / "daemon_status.json"
    status_path.unlink(missing_ok=True)
    launched_after = datetime.now(timezone.utc)
    with daemon_log.open("a", encoding="utf-8") as f:
        proc = subprocess.Popen(
            daemon_cmd,
            stdout=f,
            stderr=f,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    ready_status = wait_for_daemon_ready(
        status_path=status_path,
        process=proc,
        timeout_seconds=15,
        launched_after=launched_after,
    )
    if ready_status is None:
        _terminate_spawned_process(proc)
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
    print(f"Child runner: {codex_autoloop_bin}")
    if resolved_preset is not None:
        print(
            "Model preset: "
            f"{resolved_preset.name} "
            f"({resolved_preset.main_model}/{resolved_preset.main_reasoning_effort} "
            f"/ {resolved_preset.reviewer_model}/{resolved_preset.reviewer_reasoning_effort} "
            f"/ {resolved_preset.plan_model}/{resolved_preset.plan_reasoning_effort})"
        )
    else:
        print(f"Main model: {main_model or '<daemon default>'} effort={main_reasoning_effort or '<default>'}")
        print(
            f"Reviewer model: {reviewer_model or '<daemon default>'} "
            f"effort={reviewer_reasoning_effort or '<default>'}"
        )
        print(f"Plan model: {plan_model or '<daemon default>'} effort={plan_reasoning_effort or '<default>'}")
    print("")
    ctl_hint = resolve_daemon_ctl_hint()
    print("Terminal control examples:")
    print(f"  {ctl_hint} --bus-dir {bus_dir} run \"帮我在这个文件夹写一下pipeline\"")
    print(f"  {ctl_hint} --bus-dir {bus_dir} inject \"继续并优先修复测试\"")
    print(f"  {ctl_hint} --bus-dir {bus_dir} plan \"把后续方向转向记忆系统设计\"")
    print(f"  {ctl_hint} --bus-dir {bus_dir} review \"验收必须包含测试和运行结果\"")
    print(f"  {ctl_hint} --bus-dir {bus_dir} btw \"这个项目的 manager 和 consumer 是怎么配合的？\"")
    print(f"  {ctl_hint} --bus-dir {bus_dir} show-main-prompt")
    print(f"  {ctl_hint} --bus-dir {bus_dir} show-plan")
    print(f"  {ctl_hint} --bus-dir {bus_dir} show-plan-context")
    print(f"  {ctl_hint} --bus-dir {bus_dir} show-review")
    print(f"  {ctl_hint} --bus-dir {bus_dir} show-review-context")
    print(f"  {ctl_hint} --bus-dir {bus_dir} status")
    print(f"  {ctl_hint} --bus-dir {bus_dir} stop")
    print(f"  {ctl_hint} --bus-dir {bus_dir} daemon-stop")
    print("")
    print("Telegram control examples:")
    print("  /run <objective>")
    print("  /new")
    print("  /inject <instruction>")
    print("  /btw <question>")
    print("  /plan <direction>")
    print("  /review <criteria>")
    print("  /show-main-prompt")
    print("  /show-plan")
    print("  /show-plan-context")
    print("  /show-review [round]")
    print("  /show-review-context")
    print("  /status")
    print("  /stop")
    print("  /daemon-stop")
    print("  /help")


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


def resolve_effective_chat_id(*, bot_token: str, requested_chat_id: str, timeout_seconds: int) -> str:
    raw = (requested_chat_id or "").strip()
    if raw.lower() not in {"", "auto", "none", "null"}:
        return raw
    print("Resolving Telegram chat_id from recent updates. Send /start or a message to your bot now...", file=sys.stderr)
    resolved = resolve_chat_id(
        bot_token=bot_token,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=2,
        on_error=lambda msg: print(f"[setup] {msg}", file=sys.stderr),
    )
    if not resolved:
        print("Unable to resolve Telegram chat_id automatically.", file=sys.stderr)
        raise SystemExit(2)
    print(f"Resolved Telegram chat_id={resolved}", file=sys.stderr)
    return resolved


def resolve_codex_autoloop_bin(home_dir: Path) -> str:
    direct = shutil.which("codex-autoloop")
    if direct:
        return direct
    return materialize_codex_autoloop_shim(home_dir)


def materialize_codex_autoloop_shim(home_dir: Path) -> str:
    home_dir.mkdir(parents=True, exist_ok=True)
    repo_root = Path(__file__).resolve().parent.parent
    python_exe = sys.executable
    if os.name == "nt":
        shim_path = home_dir / "codex-autoloop-shim.cmd"
        lines = [
            "@echo off",
            f'set "PYTHONPATH={repo_root};%PYTHONPATH%"',
            f'"{python_exe}" -m codex_autoloop.cli %*',
            "",
        ]
        shim_path.write_text("\r\n".join(lines), encoding="utf-8")
        return str(shim_path)
    shim_path = home_dir / "codex-autoloop-shim.sh"
    lines = [
        "#!/usr/bin/env bash",
        f'export PYTHONPATH="{repo_root}:$PYTHONPATH"',
        f'"{python_exe}" -m codex_autoloop.cli "$@"',
        "",
    ]
    shim_path.write_text("\n".join(lines), encoding="utf-8")
    shim_path.chmod(0o755)
    return str(shim_path)


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
            daemon_running = _is_pid_running(existing_pid)
    if not daemon_running:
        return

    ctl_bin = shutil.which("codex-autoloop-daemon-ctl")
    if ctl_bin:
        _run_quiet(
            [ctl_bin, "--bus-dir", str(bus_dir), "daemon-stop"],
            timeout=10,
        )
    else:
        _run_quiet(
            [sys.executable, "-m", "codex_autoloop.daemon_ctl", "--bus-dir", str(bus_dir), "daemon-stop"],
            timeout=10,
        )

    if existing_pid and existing_pid.isdigit():
        time.sleep(1.0)
        still_running = _is_pid_running(existing_pid)
        if still_running:
            _terminate_pid(existing_pid, force=False)
            time.sleep(1.0)
            still_running = _is_pid_running(existing_pid)
            if still_running:
                _terminate_pid(existing_pid, force=True)

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


def _is_pid_running(pid: str) -> bool:
    if os.name == "nt":
        completed = _run_quiet(
            ["tasklist", "/FI", f"PID eq {pid}"],
            timeout=10,
        )
        if completed is None:
            # On timeout, prefer assuming the PID may still exist so setup can
            # continue with best-effort shutdown instead of crashing.
            return True
        if completed.returncode != 0:
            return False
        return pid in (completed.stdout or "")
    completed = _run_quiet(
        ["kill", "-0", pid],
        timeout=10,
    )
    if completed is None:
        return True
    return completed.returncode == 0


def _terminate_pid(pid: str, *, force: bool) -> None:
    if os.name == "nt":
        cmd = ["taskkill", "/PID", pid]
        if force:
            cmd.append("/F")
        _run_quiet(cmd, timeout=10)
        return
    cmd = ["kill", "-9" if force else pid]
    if force:
        cmd = ["kill", "-9", pid]
    else:
        cmd = ["kill", pid]
    _run_quiet(cmd, timeout=10)


def _run_quiet(args: list[str], *, timeout: int):
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None


def wait_for_daemon_ready(
    *,
    status_path: Path,
    process: subprocess.Popen[str],
    timeout_seconds: int,
    launched_after: datetime,
) -> dict | None:
    deadline = time.monotonic() + max(1, timeout_seconds)
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return None
        status = read_status(status_path)
        if _is_matching_daemon_status(status, expected_pid=process.pid, launched_after=launched_after):
            return status
        time.sleep(0.25)
    return None


def _terminate_spawned_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=5)
    except Exception:
        try:
            process.kill()
        except Exception:
            return


def _is_matching_daemon_status(
    status: dict | None,
    *,
    expected_pid: int,
    launched_after: datetime,
) -> bool:
    if not isinstance(status, dict):
        return False
    if status.get("daemon_running") is not True:
        return False
    if status.get("daemon_pid") != expected_pid:
        return False
    updated_at = _parse_status_timestamp(status.get("updated_at"))
    if updated_at is None:
        return False
    return updated_at >= launched_after


def _parse_status_timestamp(raw: object) -> datetime | None:
    if not isinstance(raw, str):
        return None
    normalized = raw.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def prompt_input(prompt: str, default: str) -> str:
    raw = input(prompt).strip()
    if not raw:
        return default
    return raw


def prompt_secret(prompt: str) -> str:
    return getpass.getpass(prompt).strip()


def normalize_reasoning_effort(raw: str | None, *, field_name: str) -> str | None:
    value = (raw or "").strip().lower()
    if not value:
        return None
    if value not in VALID_REASONING_EFFORTS:
        allowed = ", ".join(sorted(VALID_REASONING_EFFORTS))
        raise ValueError(f"{field_name} must be one of: {allowed}")
    return value


def prompt_model_choice() -> str:
    print("Choose a model preset:")
    for idx, preset in enumerate(MODEL_PRESETS, start=1):
        print(
            f"  {idx}. {preset.name}: "
            f"main={preset.main_model}/{preset.main_reasoning_effort}, "
            f"reviewer={preset.reviewer_model}/{preset.reviewer_reasoning_effort}, "
            f"plan={preset.plan_model}/{preset.plan_reasoning_effort}"
        )
    print(f"  {len(MODEL_PRESETS) + 1}. custom")
    raw = prompt_input("Preset number: ", default=str(_default_preset_index())).strip()
    try:
        index = int(raw)
    except ValueError:
        return _default_preset_name()
    if 1 <= index <= len(MODEL_PRESETS):
        return MODEL_PRESETS[index - 1].name
    return "custom"


def resolve_run_model_settings(
    *,
    args: argparse.Namespace,
    preset: ModelPreset | None,
) -> tuple[str | None, str | None, str | None, str | None, str | None, str | None]:
    return (
        args.run_main_model or (preset.main_model if preset is not None else None),
        args.run_main_reasoning_effort or (preset.main_reasoning_effort if preset is not None else None),
        args.run_reviewer_model or (preset.reviewer_model if preset is not None else None),
        args.run_reviewer_reasoning_effort or (
            preset.reviewer_reasoning_effort if preset is not None else None
        ),
        args.run_plan_model or (preset.plan_model if preset is not None else None),
        args.run_plan_reasoning_effort or (preset.plan_reasoning_effort if preset is not None else None),
    )


def _has_explicit_run_model_override(args: argparse.Namespace) -> bool:
    return any(
        getattr(args, field, None) is not None
        for field in (
            "run_main_model",
            "run_main_reasoning_effort",
            "run_reviewer_model",
            "run_reviewer_reasoning_effort",
            "run_plan_model",
            "run_plan_reasoning_effort",
        )
    )


def _default_preset_name() -> str:
    if any(item.name == "cheap" for item in MODEL_PRESETS):
        return "cheap"
    return MODEL_PRESETS[0].name if MODEL_PRESETS else "cheap"


def _default_preset_index() -> int:
    target = _default_preset_name()
    for idx, preset in enumerate(MODEL_PRESETS, start=1):
        if preset.name == target:
            return idx
    return 1


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
        "--run-plan-mode",
        default="auto",
        choices=["off", "auto", "record"],
        help="Default plan mode for daemon-launched runs.",
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
        "--run-plan-model",
        default=None,
        help="Override plan agent model for daemon-launched runs.",
    )
    parser.add_argument(
        "--run-plan-reasoning-effort",
        default=None,
        choices=["low", "medium", "high", "xhigh"],
        help="Override plan agent reasoning effort for daemon-launched runs.",
    )
    parser.add_argument(
        "--token-lock-dir",
        default=default_token_lock_dir(),
        help="Global lock directory to enforce one daemon per Telegram token.",
    )
    parser.add_argument(
        "--restart-existing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Stop an existing daemon under the same home-dir before starting a new one.",
    )
    return parser


if __name__ == "__main__":
    main()
