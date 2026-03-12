from __future__ import annotations

import argparse
import getpass
import json
import os
import select
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .daemon_bus import BusCommand, JsonlCommandBus, read_status
from .model_catalog import DEFAULT_MODEL_PRESET

DEFAULT_HOME_DIR = ".codex_daemon"
DEFAULT_TOKEN_LOCK_DIR = "/tmp/codex-autoloop-token-locks"
DEFAULT_MAX_ROUNDS = 500


@dataclass
class TerminalCommand:
    kind: str
    text: str = ""


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    home_dir = Path(args.home_dir).resolve()
    home_dir.mkdir(parents=True, exist_ok=True)

    if shutil.which("codex") is None:
        parser.error("codex CLI not found in PATH. Install/configure codex first.")

    config_path = home_dir / "daemon_config.json"
    config = load_config(config_path)
    if args.reconfigure or config is None or not is_config_usable(config):
        config = run_interactive_config(home_dir=home_dir, run_cd=Path(args.run_cd))
        save_config(config_path, config)
        print(f"Saved config: {config_path}")

    if args.subcommand is None:
        ensure_daemon_running(config=config, home_dir=home_dir, token_lock_dir=args.token_lock_dir)
        run_monitor_console(
            config=config,
            home_dir=home_dir,
            token_lock_dir=args.token_lock_dir,
            tail_lines=max(1, int(args.tail_lines)),
        )
        return

    bus_dir = resolve_bus_dir(config, home_dir)
    if args.subcommand == "status":
        payload = read_status(bus_dir / "daemon_status.json")
        if payload is None:
            print("No daemon status found.")
            raise SystemExit(1)
        print(json.dumps(payload, ensure_ascii=True, indent=2))
        return

    if args.subcommand in {"run", "inject"}:
        ensure_daemon_running(config=config, home_dir=home_dir, token_lock_dir=args.token_lock_dir)

    text = " ".join(args.text).strip() if hasattr(args, "text") else ""
    publish_command(bus_dir=bus_dir, kind=args.subcommand, text=text, source="terminal")
    print(f"Sent: {args.subcommand}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codexloop",
        description=(
            "Single-word entrypoint for codex-autoloop daemon. "
            "First run configures + starts daemon, later runs attach and monitor."
        ),
    )
    parser.add_argument(
        "--home-dir",
        default=DEFAULT_HOME_DIR,
        help="Daemon home directory (stores config/pid/logs/bus).",
    )
    parser.add_argument(
        "--run-cd",
        default=".",
        help="Default working directory for daemon-launched runs (first-time setup).",
    )
    parser.add_argument(
        "--token-lock-dir",
        default=DEFAULT_TOKEN_LOCK_DIR,
        help="Global lock directory to enforce one daemon per Telegram token.",
    )
    parser.add_argument(
        "--tail-lines",
        type=int,
        default=20,
        help="Initial number of lines to show for each followed log file.",
    )
    parser.add_argument(
        "--reconfigure",
        action="store_true",
        help="Re-run interactive setup and overwrite daemon config.",
    )

    sub = parser.add_subparsers(dest="subcommand")
    sub.add_parser("status", help="Show daemon status JSON.")
    run = sub.add_parser("run", help="Start a run objective.")
    run.add_argument("text", nargs="+", help="Objective text.")
    inject = sub.add_parser("inject", help="Inject instruction into active run.")
    inject.add_argument("text", nargs="+", help="Instruction text.")
    sub.add_parser("stop", help="Stop active run.")
    sub.add_parser("daemon-stop", help="Stop daemon process.")
    return parser


def load_config(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def save_config(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    path.chmod(0o600)


def run_interactive_config(*, home_dir: Path, run_cd: Path) -> dict[str, Any]:
    run_cd = run_cd.resolve()
    print("codexloop first-time setup")
    token = prompt_token()
    chat_id = prompt_chat_id()
    run_cd_value = prompt_run_cd(default=run_cd)
    check_cmd = prompt_input("Default check command (optional): ", default="").strip()
    return {
        "telegram_bot_token": token,
        "telegram_chat_id": chat_id,
        "run_cd": str(run_cd_value),
        "run_check": (check_cmd if check_cmd else None),
        "run_max_rounds": DEFAULT_MAX_ROUNDS,
        "run_skip_git_repo_check": False,
        "run_full_auto": False,
        "run_yolo": True,
        "run_resume_last_session": True,
        "run_main_reasoning_effort": None,
        "run_reviewer_reasoning_effort": None,
        "run_main_model": None,
        "run_reviewer_model": None,
        "run_model_preset": DEFAULT_MODEL_PRESET,
        "bus_dir": str((home_dir / "bus").resolve()),
        "logs_dir": str((home_dir / "logs").resolve()),
    }


def is_config_usable(config: dict[str, Any]) -> bool:
    token = str(config.get("telegram_bot_token") or "").strip()
    run_cd = str(config.get("run_cd") or "").strip()
    return looks_like_token(token) and bool(run_cd)


def prompt_run_cd(*, default: Path) -> Path:
    while True:
        raw = prompt_input(f"Run working directory [{default}]: ", default=str(default)).strip()
        candidate = Path(raw).expanduser().resolve()
        if candidate.exists() and candidate.is_dir():
            return candidate
        print("Directory not found. Please input an existing directory.", file=sys.stderr)


def prompt_input(prompt: str, default: str) -> str:
    raw = input(prompt).strip()
    if not raw:
        return default
    return raw


def prompt_secret(prompt: str) -> str:
    return getpass.getpass(prompt).strip()


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
        print("Invalid chat id. Use 'auto' or numeric id like 123456 or -100123456.", file=sys.stderr)


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


def resolve_daemon_launch_prefix() -> list[str]:
    daemon_bin = shutil.which("codex-autoloop-telegram-daemon")
    if daemon_bin:
        return [daemon_bin]
    return [sys.executable, "-m", "codex_autoloop.telegram_daemon"]


def resolve_bus_dir(config: dict[str, Any], home_dir: Path) -> Path:
    raw = str(config.get("bus_dir") or (home_dir / "bus"))
    return Path(raw).expanduser().resolve()


def resolve_logs_dir(config: dict[str, Any], home_dir: Path) -> Path:
    raw = str(config.get("logs_dir") or (home_dir / "logs"))
    return Path(raw).expanduser().resolve()


def read_pid(pid_path: Path) -> int | None:
    if not pid_path.exists():
        return None
    try:
        raw = pid_path.read_text(encoding="utf-8").strip()
        pid = int(raw)
    except Exception:
        return None
    return pid if pid > 0 else None


def is_process_running(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def ensure_daemon_running(*, config: dict[str, Any], home_dir: Path, token_lock_dir: str) -> int:
    pid_path = home_dir / "daemon.pid"
    existing_pid = read_pid(pid_path)
    if is_process_running(existing_pid):
        assert existing_pid is not None
        return existing_pid

    bus_dir = resolve_bus_dir(config, home_dir)
    logs_dir = resolve_logs_dir(config, home_dir)
    bus_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    daemon_log = home_dir / "daemon.out"
    cmd = build_daemon_command(
        config=config,
        home_dir=home_dir,
        token_lock_dir=token_lock_dir,
    )
    with daemon_log.open("a", encoding="utf-8") as stream:
        proc = subprocess.Popen(
            cmd,
            stdout=stream,
            stderr=stream,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    time.sleep(1.0)
    if proc.poll() is not None:
        print("Daemon failed to start. Recent daemon.out:", file=sys.stderr)
        print(read_log_tail(daemon_log, max_lines=30), file=sys.stderr)
        raise SystemExit(2)
    pid_path.write_text(str(proc.pid), encoding="utf-8")
    pid_path.chmod(0o600)
    print(f"Daemon started. pid={proc.pid}")
    return proc.pid


def build_daemon_command(*, config: dict[str, Any], home_dir: Path, token_lock_dir: str) -> list[str]:
    token = str(config.get("telegram_bot_token") or "").strip()
    if not token:
        raise SystemExit("Missing telegram_bot_token in daemon config.")
    run_cd = str(config.get("run_cd") or ".")
    chat_id = str(config.get("telegram_chat_id") or "auto")
    bus_dir = resolve_bus_dir(config, home_dir)
    logs_dir = resolve_logs_dir(config, home_dir)
    cmd = [
        *resolve_daemon_launch_prefix(),
        "--telegram-bot-token",
        token,
        "--telegram-chat-id",
        chat_id,
        "--run-cd",
        str(Path(run_cd).expanduser().resolve()),
        "--run-max-rounds",
        str(int(config.get("run_max_rounds", DEFAULT_MAX_ROUNDS))),
        "--bus-dir",
        str(bus_dir),
        "--logs-dir",
        str(logs_dir),
        "--run-state-file",
        str((home_dir / "last_state.json").resolve()),
        "--token-lock-dir",
        token_lock_dir,
    ]
    run_check = config.get("run_check")
    if isinstance(run_check, str) and run_check.strip():
        cmd.extend(["--run-check", run_check.strip()])
    elif isinstance(run_check, list):
        for item in run_check:
            value = str(item).strip()
            if value:
                cmd.extend(["--run-check", value])
    run_model_preset = str(config.get("run_model_preset") or "").strip()
    if run_model_preset:
        cmd.extend(["--run-model-preset", run_model_preset])
    run_main_model = str(config.get("run_main_model") or "").strip()
    if run_main_model:
        cmd.extend(["--run-main-model", run_main_model])
    run_main_effort = str(config.get("run_main_reasoning_effort") or "").strip()
    if run_main_effort:
        cmd.extend(["--run-main-reasoning-effort", run_main_effort])
    run_reviewer_model = str(config.get("run_reviewer_model") or "").strip()
    if run_reviewer_model:
        cmd.extend(["--run-reviewer-model", run_reviewer_model])
    run_reviewer_effort = str(config.get("run_reviewer_reasoning_effort") or "").strip()
    if run_reviewer_effort:
        cmd.extend(["--run-reviewer-reasoning-effort", run_reviewer_effort])
    if bool(config.get("run_skip_git_repo_check")):
        cmd.append("--run-skip-git-repo-check")
    if bool(config.get("run_full_auto")):
        cmd.append("--run-full-auto")
    if bool(config.get("run_yolo", True)):
        cmd.append("--run-yolo")
    else:
        cmd.append("--no-run-yolo")
    if bool(config.get("run_resume_last_session", True)):
        cmd.append("--run-resume-last-session")
    else:
        cmd.append("--no-run-resume-last-session")
    return cmd


def read_log_tail(path: Path, *, max_lines: int) -> str:
    if not path.exists():
        return "<log file not found>"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return "<unable to read log>"
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[-max_lines:])


def publish_command(*, bus_dir: Path, kind: str, text: str, source: str) -> None:
    bus_dir.mkdir(parents=True, exist_ok=True)
    bus = JsonlCommandBus(bus_dir / "daemon_commands.jsonl")
    bus.publish(BusCommand(kind=kind, text=text, source=source, ts=time.time()))


def run_monitor_console(
    *,
    config: dict[str, Any],
    home_dir: Path,
    token_lock_dir: str,
    tail_lines: int,
) -> None:
    bus_dir = resolve_bus_dir(config, home_dir)
    logs_dir = resolve_logs_dir(config, home_dir)
    daemon_out = home_dir / "daemon.out"
    events_log = logs_dir / "daemon-events.jsonl"
    status_path = bus_dir / "daemon_status.json"

    print("Attached to codexloop daemon.")
    print(
        "Commands: /status /run <objective> /inject <instruction> /stop /daemon-stop /exit"
    )
    print("Plain text: running -> inject, idle -> run")
    print("")

    tracked_offsets: dict[Path, int] = {}
    file_labels: dict[Path, str] = {}

    def ensure_tracked(path: Path, label: str) -> None:
        if path in tracked_offsets:
            return
        if path.exists():
            for line in tail_file(path, max_lines=tail_lines):
                print(f"[{label}] {line}")
            tracked_offsets[path] = path.stat().st_size
        else:
            tracked_offsets[path] = 0
        file_labels[path] = label

    ensure_tracked(daemon_out, "daemon")
    ensure_tracked(events_log, "events")

    last_child_log: Path | None = None
    while True:
        status_payload = read_status(status_path) or {}
        child_log_raw = status_payload.get("child_log_path")
        child_log_path = Path(child_log_raw).resolve() if isinstance(child_log_raw, str) and child_log_raw else None
        if child_log_path is not None and child_log_path != last_child_log:
            print(f"[monitor] child log switched to: {child_log_path}")
            ensure_tracked(child_log_path, "child")
            last_child_log = child_log_path

        for path, offset in list(tracked_offsets.items()):
            lines, next_offset = read_new_lines(path, offset)
            tracked_offsets[path] = next_offset
            label = file_labels.get(path, "log")
            for line in lines:
                print(f"[{label}] {line}")

        line = read_input_line(timeout_seconds=0.5)
        if line is None:
            continue
        if line == "__EOF__":
            print("Input closed. Exiting monitor.")
            return

        running = bool((read_status(status_path) or {}).get("running"))
        parsed = parse_terminal_command(line, running=running)
        if parsed is None:
            continue
        if parsed.kind == "exit":
            print("Leaving monitor.")
            return
        if parsed.kind == "help":
            print(
                "Commands: /status /run <objective> /inject <instruction> /stop /daemon-stop /exit\n"
                "Plain text routes to inject when running, else run."
            )
            continue
        if parsed.kind == "status":
            payload = read_status(status_path)
            if payload is None:
                print("No daemon status found.")
            else:
                print(json.dumps(payload, ensure_ascii=True, indent=2))
            continue
        if parsed.kind in {"run", "inject"}:
            ensure_daemon_running(config=config, home_dir=home_dir, token_lock_dir=token_lock_dir)
        publish_command(bus_dir=bus_dir, kind=parsed.kind, text=parsed.text, source="terminal-console")
        print(f"Sent: {parsed.kind}")


def tail_file(path: Path, *, max_lines: int) -> list[str]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    if len(lines) <= max_lines:
        return lines
    return lines[-max_lines:]


def read_new_lines(path: Path, offset: int) -> tuple[list[str], int]:
    if not path.exists():
        return [], offset
    size = path.stat().st_size
    if size < offset:
        offset = 0
    if size == offset:
        return [], offset
    try:
        with path.open("r", encoding="utf-8") as stream:
            stream.seek(offset)
            chunk = stream.read()
            next_offset = stream.tell()
    except Exception:
        return [], offset
    if not chunk:
        return [], next_offset
    return chunk.splitlines(), next_offset


def read_input_line(*, timeout_seconds: float) -> str | None:
    try:
        ready, _, _ = select.select([sys.stdin], [], [], timeout_seconds)
    except Exception:
        time.sleep(timeout_seconds)
        return None
    if not ready:
        return None
    line = sys.stdin.readline()
    if line == "":
        return "__EOF__"
    return line.rstrip("\n")


def parse_terminal_command(raw: str, *, running: bool) -> TerminalCommand | None:
    text = raw.strip()
    if not text:
        return None
    if text in {"/exit", "/quit", "exit", "quit"}:
        return TerminalCommand(kind="exit")
    if text in {"/help", "help"}:
        return TerminalCommand(kind="help")
    if text in {"/status", "status"}:
        return TerminalCommand(kind="status")
    if text in {"/stop", "stop"}:
        return TerminalCommand(kind="stop")
    if text in {"/daemon-stop", "daemon-stop"}:
        return TerminalCommand(kind="daemon-stop")
    if text.startswith("/run "):
        objective = text[len("/run ") :].strip()
        if not objective:
            return None
        return TerminalCommand(kind="run", text=objective)
    if text == "/run":
        return None
    if text.startswith("/inject "):
        instruction = text[len("/inject ") :].strip()
        if not instruction:
            return None
        return TerminalCommand(kind="inject", text=instruction)
    if text == "/inject":
        return None
    if text.startswith("/"):
        return None
    return TerminalCommand(kind="inject" if running else "run", text=text)


if __name__ == "__main__":
    main()
