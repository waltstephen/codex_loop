from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .model_catalog import MODEL_PRESETS, get_preset
from .planner_modes import (
    PLANNER_MODE_AUTO,
    PLANNER_MODE_CHOICES,
    planner_mode_description,
    planner_mode_label,
)
from .telegram_notifier import resolve_chat_id
from .token_lock import acquire_token_lock, default_token_lock_dir


DEFAULT_CODEX_AUTOLOOP_CMD = f"{sys.executable} -m codex_autoloop.cli"


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

    token = prompt_token()
    home_dir = Path(args.home_dir).resolve()
    bus_dir = home_dir / "bus"
    logs_dir = home_dir / "logs"
    home_dir.mkdir(parents=True, exist_ok=True)
    bus_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    if args.restart_existing:
        stop_existing_daemon(home_dir=home_dir, bus_dir=bus_dir)

    requested_chat_id = prompt_chat_id()
    check_cmd = prompt_input(
        "Default check command (optional, leave empty for none): ",
        default="",
    ).strip()
    preset_name = args.run_model_preset
    inherit_codex_defaults = False
    if preset_name is None and args.run_main_model is None and args.run_reviewer_model is None:
        preset_name = prompt_model_choice()
        if preset_name is None:
            inherit_codex_defaults = True
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
        if inherit_codex_defaults:
            main_model = None
            main_reasoning_effort = None
            reviewer_model = None
            reviewer_reasoning_effort = None
        elif args.run_main_model is not None or args.run_reviewer_model is not None:
            main_model = args.run_main_model
            main_reasoning_effort = args.run_main_reasoning_effort
            reviewer_model = args.run_reviewer_model
            reviewer_reasoning_effort = args.run_reviewer_reasoning_effort
        else:
            main_model = prompt_input("Main agent model (optional): ", default="").strip() or None
            main_reasoning_effort = prompt_reasoning_effort(
                "Main agent reasoning effort (low/medium/high/xhigh, optional): "
            )
            reviewer_model = prompt_input("Reviewer agent model (optional): ", default="").strip() or None
            reviewer_reasoning_effort = prompt_reasoning_effort(
                "Reviewer agent reasoning effort (low/medium/high/xhigh, optional): "
            )
    planner_mode = args.run_planner_mode
    if planner_mode is None:
        planner_mode = prompt_planner_mode_choice()

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

    chat_id = resolve_effective_chat_id(
        bot_token=token,
        requested_chat_id=requested_chat_id,
        timeout_seconds=120,
        home_dir=home_dir,
        token_lock_dir=args.token_lock_dir,
    )
    feishu_app_id = (getattr(args, "feishu_app_id", None) or "").strip() or None
    feishu_app_secret = (getattr(args, "feishu_app_secret", None) or "").strip() or None
    feishu_chat_id = (getattr(args, "feishu_chat_id", None) or "").strip() or None
    feishu_receive_id_type = str(getattr(args, "feishu_receive_id_type", "chat_id") or "chat_id").strip() or "chat_id"
    feishu_fields = [feishu_app_id, feishu_app_secret, feishu_chat_id]
    if any(feishu_fields) and not all(feishu_fields):
        print(
            "Feishu configuration is incomplete. Provide app id, app secret, and chat id together.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if not all(feishu_fields):
        feishu_enabled = prompt_yes_no("Enable Feishu bidirectional control?", default=False)
        if feishu_enabled:
            feishu_app_id = prompt_input("Feishu app id: ", default="").strip() or None
            feishu_app_secret = prompt_secret("Feishu app secret: ").strip() or None
            feishu_chat_id = prompt_input("Feishu chat id: ", default="").strip() or None
            if not (feishu_app_id and feishu_app_secret and feishu_chat_id):
                print("Feishu setup skipped because one or more required fields were empty.", file=sys.stderr)
                feishu_app_id = None
                feishu_app_secret = None
                feishu_chat_id = None

    config = {
        "telegram_bot_token": token,
        "telegram_chat_id": chat_id,
        "feishu_app_id": feishu_app_id,
        "feishu_app_secret": feishu_app_secret,
        "feishu_chat_id": feishu_chat_id,
        "feishu_receive_id_type": feishu_receive_id_type,
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
        "codex_autoloop_bin": DEFAULT_CODEX_AUTOLOOP_CMD,
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
        "--argusbot-bin",
        DEFAULT_CODEX_AUTOLOOP_CMD,
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
    if feishu_app_id and feishu_app_secret and feishu_chat_id:
        daemon_cmd.extend(
            [
                "--feishu-app-id",
                feishu_app_id,
                "--feishu-app-secret",
                feishu_app_secret,
                "--feishu-chat-id",
                feishu_chat_id,
                "--feishu-receive-id-type",
                feishu_receive_id_type,
            ]
        )
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
        print(f"Main model: {main_model or '<codex default>'} effort={main_reasoning_effort or '<default>'}")
        print(
            f"Reviewer model: {reviewer_model or '<codex default>'} "
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
    override = os.environ.get("CODEX_AUTOLOOP_DAEMON_BIN", "").strip()
    if override:
        return shlex.split(override)
    if _detect_local_repo_root(Path.cwd()) or _detect_local_repo_root(Path(__file__).resolve().parent):
        return [sys.executable, "-m", "codex_autoloop.telegram_daemon"]
    daemon_bin = shutil.which("argusbot-daemon")
    if daemon_bin:
        return [daemon_bin]
    return [sys.executable, "-m", "codex_autoloop.telegram_daemon"]


def resolve_daemon_ctl_hint() -> str:
    ctl_bin = shutil.which("argusbot-daemon-ctl")
    if ctl_bin:
        return ctl_bin
    return f"{sys.executable} -m codex_autoloop.daemon_ctl"


def resolve_effective_chat_id(
    *,
    bot_token: str,
    requested_chat_id: str,
    timeout_seconds: int,
    home_dir: Path | None = None,
    token_lock_dir: str | Path | None = None,
) -> str:
    raw = (requested_chat_id or "").strip()
    if raw.lower() not in {"", "auto", "none", "null"}:
        return raw
    errors: list[str] = []

    def _on_error(message: str) -> None:
        errors.append(message)
        print(f"[setup] {message}", file=sys.stderr)

    print("Resolving Telegram chat_id from recent updates. Send /start or a message to your bot now...", file=sys.stderr)
    resolved = resolve_chat_id(
        bot_token=bot_token,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=2,
        on_error=_on_error,
    )
    if not resolved:
        fallback_chat_id, fallback_source = resolve_local_chat_id_hint(
            bot_token=bot_token,
            home_dir=home_dir,
            token_lock_dir=token_lock_dir,
        )
        if fallback_chat_id:
            print(
                f"Reusing existing Telegram chat_id={fallback_chat_id} from {fallback_source}.",
                file=sys.stderr,
            )
            return fallback_chat_id
        if any(_is_getupdates_conflict_error(message) for message in errors):
            print(
                "Telegram getUpdates is already being polled by another instance for this bot token.",
                file=sys.stderr,
            )
    if not resolved:
        print("Unable to resolve Telegram chat_id automatically.", file=sys.stderr)
        raise SystemExit(2)
    print(f"Resolved Telegram chat_id={resolved}", file=sys.stderr)
    return resolved


def resolve_local_chat_id_hint(
    *,
    bot_token: str,
    home_dir: Path | None,
    token_lock_dir: str | Path | None,
) -> tuple[str | None, str | None]:
    if home_dir is not None:
        config_path = home_dir / "daemon_config.json"
        home_chat_id = _read_chat_id_from_json(path=config_path, key="telegram_chat_id")
        if home_chat_id:
            return home_chat_id, str(config_path)
    for lock_dir in _candidate_token_lock_dirs(token_lock_dir):
        meta_path = lock_dir / f"{_token_hash(bot_token)}.json"
        token_chat_id = _read_chat_id_from_json(path=meta_path, key="chat_id")
        if token_chat_id:
            return token_chat_id, str(meta_path)
    return None, None


def _read_chat_id_from_json(*, path: Path, key: str) -> str | None:
    payload = _read_json_object(path)
    if payload is None:
        return None
    value = str(payload.get(key, "")).strip()
    if not looks_like_chat_id(value):
        return None
    return value


def _read_json_object(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _candidate_token_lock_dirs(primary: str | Path | None) -> list[Path]:
    raw_candidates: list[Path] = []
    if primary:
        raw_candidates.append(Path(primary))
    try:
        raw_candidates.append(Path(default_token_lock_dir()))
    except Exception:
        pass
    raw_candidates.append(Path("/tmp/argusbot-token-locks"))

    candidates: list[Path] = []
    seen: set[str] = set()
    for candidate in raw_candidates:
        try:
            resolved = candidate.resolve()
        except Exception:
            resolved = candidate
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        candidates.append(resolved)
    return candidates


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]


def _is_getupdates_conflict_error(message: str) -> bool:
    lowered = message.lower()
    return "getupdates http 409" in lowered or "other getupdates request" in lowered


def _detect_local_repo_root(start: Path) -> Path | None:
    for parent in (start,) + tuple(start.parents):
        pyproject = parent / "pyproject.toml"
        if not pyproject.exists():
            continue
        try:
            text = pyproject.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if 'name = "ArgusBot"' in text or "name = 'ArgusBot'" in text:
            return parent
    return None


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

    ctl_bin = shutil.which("argusbot-daemon-ctl")
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
    cmd = ["kill", "-9", pid] if force else ["kill", pid]
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


def prompt_input(prompt: str, default: str) -> str:
    raw = input(prompt).strip()
    if not raw:
        return default
    return raw


def prompt_secret(prompt: str) -> str:
    return getpass.getpass(prompt).strip()


def prompt_yes_no(prompt: str, *, default: bool) -> bool:
    default_text = "Y/n" if default else "y/N"
    while True:
        raw = prompt_input(f"{prompt} [{default_text}]: ", default=("y" if default else "n")).strip().lower()
        if not raw:
            raw = "y" if default else "n"
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("Please answer y or n.", file=sys.stderr)


def prompt_token() -> str:
    while True:
        token = prompt_secret("Telegram bot token: ")
        if looks_like_token(token):
            return token
        print("Invalid token format. Expected <digits>:<secret>. Please try again.", file=sys.stderr)


def prompt_chat_id() -> str:
    while True:
        value = prompt_input("Telegram chat id (or 'auto'): ", default="auto").strip() or "auto"
        if value.lower() == "auto" or looks_like_chat_id(value):
            return value
        print("Invalid chat id. Use 'auto' or a numeric chat id like 123456 or -100123456.", file=sys.stderr)


def prompt_model_choice() -> str | None:
    print("Choose a model preset:")
    print("  0. inherit codex default (recommended)")
    for idx, preset in enumerate(MODEL_PRESETS, start=1):
        print(
            f"  {idx}. {preset.name}: "
            f"main={preset.main_model}/{preset.main_reasoning_effort}, "
            f"reviewer={preset.reviewer_model}/{preset.reviewer_reasoning_effort}"
        )
    print(f"  {len(MODEL_PRESETS) + 1}. custom")
    while True:
        raw = prompt_input("Preset number: ", default="0").strip()
        try:
            index = int(raw)
        except ValueError:
            print("Invalid selection. Enter a number from the list.", file=sys.stderr)
            continue
        if index == 0:
            return None
        if 1 <= index <= len(MODEL_PRESETS):
            return MODEL_PRESETS[index - 1].name
        if index == len(MODEL_PRESETS) + 1:
            return "custom"
        print("Selection out of range. Please choose one of the listed numbers.", file=sys.stderr)


def prompt_reasoning_effort(prompt: str) -> str | None:
    while True:
        value = prompt_input(prompt, default="").strip().lower()
        if not value:
            return None
        if value in {"low", "medium", "high", "xhigh"}:
            return value
        print("Invalid reasoning effort. Choose low, medium, high, xhigh, or leave blank.", file=sys.stderr)


def looks_like_token(token: str) -> bool:
    if ":" not in token:
        return False
    left, right = token.split(":", 1)
    return left.isdigit() and bool(right.strip())


def looks_like_chat_id(value: str) -> bool:
    if not value:
        return False
    if value.startswith("-"):
        return value[1:].isdigit()
    return value.isdigit()


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
        prog="argusbot-setup",
        description="Interactive ArgusBot setup: verify codex, collect Telegram token, and launch daemon in background.",
    )
    parser.add_argument(
        "--home-dir",
        default=".argusbot",
        help="Directory to store daemon config/log/pid/bus files.",
    )
    parser.add_argument(
        "--run-cd",
        default=".",
        help="Working directory for launched ArgusBot runs.",
    )
    parser.add_argument("--run-max-rounds", type=int, default=100, help="Default max rounds for daemon-launched runs.")
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
        default="/tmp/argusbot-token-locks",
        help="Global lock directory to enforce one daemon per Telegram token.",
    )
    parser.add_argument("--feishu-app-id", default=None, help="Optional Feishu app id.")
    parser.add_argument("--feishu-app-secret", default=None, help="Optional Feishu app secret.")
    parser.add_argument("--feishu-chat-id", default=None, help="Optional Feishu chat id.")
    parser.add_argument(
        "--feishu-receive-id-type",
        default="chat_id",
        help="Feishu receive_id_type used for outgoing messages.",
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
