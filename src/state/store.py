from __future__ import annotations

import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import ProjectPaths
from src.io import read_json, utc_now, write_json


VALID_STATES = {
    "created",
    "analyzing",
    "content_processing",
    "awaiting_confirmation",
    "awaiting_video",
    "video_processing",
    "design_processing",
    "reviewing",
    "revision_required",
    "needs_human_review",
    "approved",
    "completed",
    "failed",
    "cancelled",
}

ALLOWED_TRANSITIONS = {
    "created": {"analyzing", "failed", "cancelled"},
    "analyzing": {
        "content_processing",
        "awaiting_confirmation",
        "awaiting_video",
        "video_processing",
        "needs_human_review",
        "failed",
        "cancelled",
    },
    "content_processing": {"reviewing", "awaiting_confirmation", "failed", "cancelled"},
    "awaiting_confirmation": {"content_processing", "video_processing", "cancelled"},
    "awaiting_video": {"video_processing", "reviewing", "cancelled"},
    "video_processing": {"reviewing", "needs_human_review", "failed", "cancelled"},
    "design_processing": {"reviewing", "needs_human_review", "failed", "cancelled"},
    "reviewing": {"approved", "revision_required", "needs_human_review", "failed"},
    "revision_required": {
        "content_processing",
        "video_processing",
        "design_processing",
        "needs_human_review",
        "cancelled",
    },
    "approved": {"awaiting_video", "completed", "design_processing", "reviewing"},
    "needs_human_review": {
        "content_processing",
        "video_processing",
        "design_processing",
        "approved",
        "cancelled",
    },
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
}


class TaskStore:
    def __init__(self, paths: ProjectPaths) -> None:
        self.paths = paths

    def create(
        self,
        request: str,
        workflow_id: str,
        platform: str,
        inputs: dict[str, Any],
        routing: dict[str, Any],
    ) -> tuple[str, Path]:
        now = datetime.now(timezone.utc)
        task_id = f"task_{now:%Y%m%d}_{now:%H%M%S}_{secrets.token_hex(3)}"
        task_dir = self.paths.task_dir(task_id)
        for name in ("inputs", "outputs", "handoffs", "reviews", "logs"):
            (task_dir / name).mkdir(parents=True, exist_ok=False)

        created_at = utc_now()
        task = {
            "task_id": task_id,
            "request": request,
            "workflow_id": workflow_id,
            "platform": platform,
            "created_at": created_at,
            "inputs": inputs,
            "routing": routing,
        }
        state = {
            "task_id": task_id,
            "status": "created",
            "current_stage": "intake",
            "revision_counts": {},
            "history": [
                {
                    "from": None,
                    "to": "created",
                    "stage": "intake",
                    "at": created_at,
                    "reason": "task created",
                }
            ],
            "updated_at": created_at,
            "last_summary": "Task accepted by Manager",
        }
        write_json(task_dir / "task.json", task)
        write_json(task_dir / "state.json", state)
        return task_id, task_dir

    def task(self, task_id: str) -> dict[str, Any]:
        return read_json(self.paths.task_dir(task_id) / "task.json")

    def state(self, task_id: str) -> dict[str, Any]:
        return read_json(self.paths.task_dir(task_id) / "state.json")

    def transition(
        self,
        task_id: str,
        new_status: str,
        stage: str,
        reason: str,
        summary: str | None = None,
    ) -> dict[str, Any]:
        if new_status not in VALID_STATES:
            raise ValueError(f"Unknown task state: {new_status}")
        state = self.state(task_id)
        current = state["status"]
        if new_status != current and new_status not in ALLOWED_TRANSITIONS[current]:
            raise ValueError(f"Invalid transition: {current} -> {new_status}")
        changed_at = utc_now()
        state["status"] = new_status
        state["current_stage"] = stage
        state["updated_at"] = changed_at
        if summary is not None:
            state["last_summary"] = summary
        state["history"].append(
            {
                "from": current,
                "to": new_status,
                "stage": stage,
                "at": changed_at,
                "reason": reason,
            }
        )
        write_json(self.paths.task_dir(task_id) / "state.json", state)
        return state

    def increment_revision(self, task_id: str, stage: str) -> int:
        state = self.state(task_id)
        counts = state.setdefault("revision_counts", {})
        counts[stage] = int(counts.get(stage, 0)) + 1
        state["updated_at"] = utc_now()
        write_json(self.paths.task_dir(task_id) / "state.json", state)
        return counts[stage]
