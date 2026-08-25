from __future__ import annotations

from pathlib import Path
from typing import Any

from src.io import utc_now, write_json


def write_handoff(
    task_dir: Path,
    filename: str,
    task_id: str,
    source_agent: str,
    target_agent: str,
    artifact_type: str,
    payload: dict[str, Any],
) -> tuple[Path, dict[str, Any]]:
    if Path(filename).name != filename or not filename.endswith(".json"):
        raise ValueError("Handoff filename must be a plain .json filename")
    handoff = {
        "task_id": task_id,
        "source_agent": source_agent,
        "target_agent": target_agent,
        "artifact_type": artifact_type,
        "created_at": utc_now(),
        "payload": payload,
    }
    path = task_dir / "handoffs" / filename
    write_json(path, handoff)
    return path, handoff

