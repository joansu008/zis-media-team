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
    parser.add_argument(
        "--execution-mode",
        choices=("codex_native", "api", "deterministic", "model"),
        help="Codex-native delegation (default), provider API, or offline baseline",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("capabilities", help="Detect local capabilities")

    start = commands.add_parser("start", help="Create and run a task")
    start.add_argument("request")
    start.add_argument("--input", dest="input_path")
    start.add_argument("--platform", default="unspecified")

    status = commands.add_parser("status", help="Read task state")
    status.add_argument("task_id")

    next_command = commands.add_parser(
        "next", help="Read the state-authorized next native delegation"
    )
    next_command.add_argument("task_id")

    submit_content = commands.add_parser(
        "submit-content", help="Validate and persist a native Content result"
    )
    submit_content.add_argument("task_id")
    submit_content.add_argument("--artifact", type=Path, required=True)
    submit_content.add_argument("--subagent-id", required=True)
    submit_content.add_argument("--started-at", required=True)
    submit_content.add_argument("--completed-at")

    submit_review = commands.add_parser(
        "submit-review", help="Validate and fuse a native Review result"
    )
    submit_review.add_argument("task_id")
    submit_review.add_argument("--artifact", type=Path, required=True)
    submit_review.add_argument("--subagent-id", required=True)
    submit_review.add_argument("--started-at", required=True)
    submit_review.add_argument("--completed-at")

    native_failure = commands.add_parser(
        "record-native-failure", help="Record a failed native delegation"
    )
    native_failure.add_argument("task_id")
    native_failure.add_argument("--agent-id", required=True)
    native_failure.add_argument("--subagent-id", required=True)
    native_failure.add_argument("--started-at", required=True)
    native_failure.add_argument("--completed-at")
    native_failure.add_argument("--error-code", required=True)

    review = commands.add_parser("review", help="Independently re-review a task")
    review.add_argument("task_id")

    rework = commands.add_parser("rework", help="Run the assigned revision and re-review")
    rework.add_argument("task_id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runtime = ManagerRuntime(
        workspace=args.workspace, execution_mode=args.execution_mode
    )
    try:
        if args.command == "capabilities":
            _print(runtime.capabilities())
        elif args.command == "start":
            _print(runtime.start(args.request, args.input_path, args.platform))
        elif args.command == "status":
            _print(runtime.summary(args.task_id))
        elif args.command == "next":
            _print(runtime.next_action(args.task_id))
        elif args.command == "submit-content":
            _print(
                runtime.submit_native_content(
                    args.task_id,
                    args.artifact,
                    subagent_id=args.subagent_id,
                    started_at=args.started_at,
                    completed_at=args.completed_at,
                )
            )
        elif args.command == "submit-review":
            _print(
                runtime.submit_native_review(
                    args.task_id,
                    args.artifact,
                    subagent_id=args.subagent_id,
                    started_at=args.started_at,
                    completed_at=args.completed_at,
                )
            )
        elif args.command == "record-native-failure":
            _print(
                runtime.record_native_failure(
                    args.task_id,
                    agent_id=args.agent_id,
                    subagent_id=args.subagent_id,
                    started_at=args.started_at,
                    completed_at=args.completed_at,
                    error_code=args.error_code,
                )
            )
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
