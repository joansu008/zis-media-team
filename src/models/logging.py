from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

from src.io import utc_now, write_json


def log_model_call(
    task_dir: Path,
    *,
    task_id: str,
    agent_id: str,
    provider: str,
    model: str,
    execution_mode: str,
    success: bool,
    latency_ms: int,
    token_usage: dict[str, Any] | None,
    retry_count: int,
    error_code: str = "",
) -> Path:
    timestamp = utc_now()
    filename_time = timestamp.replace(":", "").replace("+", "_")
    path = (
        task_dir
        / "logs"
        / f"model_call_{filename_time}_{agent_id}_{secrets.token_hex(2)}.json"
    )
    write_json(
        path,
        {
            "task_id": task_id,
            "agent_id": agent_id,
            "provider": provider,
            "model": model,
            "execution_mode": execution_mode,
            "timestamp": timestamp,
            "success": success,
            "latency_ms": latency_ms,
            "token_usage": token_usage or {},
            "retry_count": retry_count,
            "error_code": error_code,
        },
    )
    return path


def log_native_subagent(
    task_dir: Path,
    *,
    task_id: str,
    agent_id: str,
    subagent_id: str,
    started_at: str,
    completed_at: str,
    success: bool,
    revision_attempt: int,
    error_code: str = "",
    token_usage: dict[str, Any] | None = None,
) -> Path:
    """Record a Codex-native delegation without inventing unavailable usage data."""
    filename_time = completed_at.replace(":", "").replace("+", "_")
    path = (
        task_dir
        / "logs"
        / f"native_agent_{filename_time}_{agent_id}_{secrets.token_hex(2)}.json"
    )
    record: dict[str, Any] = {
        "task_id": task_id,
        "agent_id": agent_id,
        "execution_mode": "codex_native",
        "subagent_id": subagent_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "success": success,
        "revision_attempt": revision_attempt,
        "error_code": error_code,
    }
    if token_usage is not None:
        record["token_usage"] = token_usage
    write_json(path, record)
    return path
