from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .daemon_bus import BusCommand, JsonlCommandBus, read_status


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    bus_dir = Path(args.bus_dir).resolve()
    bus_dir.mkdir(parents=True, exist_ok=True)
    command_bus = JsonlCommandBus(bus_dir / "daemon_commands.jsonl")
    status_path = bus_dir / "daemon_status.json"

    if args.subcommand == "status":
        payload = read_status(status_path)
        if payload is None:
            print("No daemon status found.")
            raise SystemExit(1)
        print(json.dumps(payload, ensure_ascii=True, indent=2))
        raise SystemExit(0)

    if args.subcommand == "help":
        publish(command_bus, "help", "", source="terminal")
        print("Sent: help")
        raise SystemExit(0)

    if args.subcommand == "run":
        publish(command_bus, "run", args.text, source="terminal")
        print("Sent: run")
        raise SystemExit(0)

    if args.subcommand == "inject":
        publish(command_bus, "inject", args.text, source="terminal")
        print("Sent: inject")
        raise SystemExit(0)

    if args.subcommand == "stop":
        publish(command_bus, "stop", "", source="terminal")
        print("Sent: stop")
        raise SystemExit(0)

    if args.subcommand == "daemon-stop":
        publish(command_bus, "daemon-stop", "", source="terminal")
        print("Sent: daemon-stop")
        raise SystemExit(0)

    parser.error(f"Unknown command: {args.subcommand}")


def publish(bus: JsonlCommandBus, kind: str, text: str, source: str) -> None:
    bus.publish(BusCommand(kind=kind, text=text, source=source, ts=time.time()))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex-autoloop-daemon-ctl",
        description="Send terminal commands to codex-autoloop telegram daemon.",
    )
    parser.add_argument(
        "--bus-dir",
        default=".codex_daemon/bus",
        help="Daemon bus directory.",
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)
    run = sub.add_parser("run", help="Start a run objective.")
    run.add_argument("text", help="Objective text.")
    inject = sub.add_parser("inject", help="Inject instruction to active run.")
    inject.add_argument("text", help="Instruction text.")
    sub.add_parser("stop", help="Stop active run.")
    sub.add_parser("status", help="Read daemon status file.")
    sub.add_parser("help", help="Ask daemon to print help.")
    sub.add_parser("daemon-stop", help="Stop daemon process.")
    return parser


if __name__ == "__main__":
    main()
