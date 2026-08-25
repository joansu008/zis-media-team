from __future__ import annotations

import platform
import shutil
import sys
from typing import Any

from src.adapters.zis_video_workflow import ZisVideoWorkflowAdapter
from src.config import ProjectPaths


def _os_name() -> str:
    return {"Darwin": "macOS", "Windows": "Windows", "Linux": "Linux"}.get(
        platform.system(), platform.system() or "unknown"
    )


def detect_capabilities(paths: ProjectPaths) -> dict[str, Any]:
    adapter = ZisVideoWorkflowAdapter(paths).probe()
    return {
        "os": _os_name(),
        "python": True,
        "python_version": platform.python_version(),
        "python_supported": sys.version_info >= (3, 9),
        "git": shutil.which("git") is not None,
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "zis_video_workflow": adapter.status == "available",
        "zis_video_workflow_detail": adapter.as_dict(),
    }

