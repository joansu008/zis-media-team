from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.manager.runtime import ManagerRuntime


def _print(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zis-media-team")
    parser.add_argument(
        "--workspace", type=Path, help="Optional local workspace override"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("capabilities", help="Detect local capabilities")

    start = commands.add_parser("start", help="Create and run a task")
    start.add_argument("request")
    start.add_argument("--input", dest="input_path")
    start.add_argument("--platform", default="unspecified")

    status = commands.add_parser("status", help="Read task state")
    status.add_argument("task_id")

    review = commands.add_parser("review", help="Independently re-review a task")
    review.add_argument("task_id")

    rework = commands.add_parser("rework", help="Run the assigned revision and re-review")
    rework.add_argument("task_id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runtime = ManagerRuntime(workspace=args.workspace)
    try:
        if args.command == "capabilities":
            _print(runtime.capabilities())
        elif args.command == "start":
            _print(runtime.start(args.request, args.input_path, args.platform))
        elif args.command == "status":
            _print(runtime.summary(args.task_id))
        elif args.command == "review":
            _print(runtime.review_task(args.task_id))
        elif args.command == "rework":
            _print(runtime.rework(args.task_id))
        return 0
    except (FileNotFoundError, ValueError, KeyError, NotImplementedError) as error:
        _print({"status": "failed", "error": str(error)})
        return 1


if __name__ == "__main__":
    sys.exit(main())

