from __future__ import annotations

import os
import platform
import shutil
import sys
from typing import Any

from src.adapters.zis_video_workflow import ZisVideoWorkflowAdapter
from src.config import ProjectPaths
from src.models.base import ModelProvider
from src.models.provider import create_model_provider


def _os_name() -> str:
    return {"Darwin": "macOS", "Windows": "Windows", "Linux": "Linux"}.get(
        platform.system(), platform.system() or "unknown"
    )


def detect_capabilities(
    paths: ProjectPaths,
    execution_mode: str | None = None,
    provider: ModelProvider | None = None,
    content_model: str | None = None,
    review_model: str | None = None,
) -> dict[str, Any]:
    adapter = ZisVideoWorkflowAdapter(paths).probe()
    selected_provider = provider or create_model_provider()
    provider_capability = selected_provider.capability()
    selected_content_model = (
        content_model if content_model is not None else os.getenv("ZIS_CONTENT_MODEL", "")
    ).strip()
    selected_review_model = (
        review_model if review_model is not None else os.getenv("ZIS_REVIEW_MODEL", "")
    ).strip()
    selected_execution_mode = (
        execution_mode or os.getenv("ZIS_EXECUTION_MODE", "codex_native")
    ).strip().lower()
    if selected_execution_mode == "model":
        selected_execution_mode = "api"
    return {
        "os": _os_name(),
        "python": True,
        "python_version": platform.python_version(),
        "python_supported": sys.version_info >= (3, 9),
        "git": shutil.which("git") is not None,
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "zis_video_workflow": adapter.status == "available",
        "zis_video_workflow_detail": adapter.as_dict(),
        "execution_mode": selected_execution_mode,
        "codex_native_subagents_available": None,
        "codex_native": {
            "requires_codex_lead": True,
            "python_calls_subscription_or_api": False,
            "subagents_available": None,
            "detection": "The active Codex Lead must inspect its native collaboration tools",
        },
        "model_provider": selected_provider.name,
        "model_provider_available": provider_capability.available,
        "model_provider_detail": provider_capability.as_dict(),
        "content_model_configured": bool(selected_content_model),
        "review_model_configured": bool(selected_review_model),
        "model_agents_available": (
            selected_execution_mode == "api"
            and provider_capability.available
            and bool(selected_content_model)
            and bool(selected_review_model)
        ),
    }
