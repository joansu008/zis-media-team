from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.config import ProjectPaths
from src.io import read_json


@dataclass(frozen=True)
class AdapterProbe:
    status: str
    root_found: bool
    command_configured: bool
    path: str | None
    reason: str
    can_continue_without_video: bool
    required_action: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "root_found": self.root_found,
            "command_configured": self.command_configured,
            "path": self.path,
            "reason": self.reason,
            "can_continue_without_video": self.can_continue_without_video,
            "required_action": self.required_action,
        }


class ZisVideoWorkflowAdapter:
    def __init__(self, paths: ProjectPaths) -> None:
        self.paths = paths

    def configured_root(self) -> Path:
        raw = os.getenv("ZIS_VIDEO_WORKFLOW_PATH", "").strip()
        candidate = Path(raw) if raw else self.paths.root.parent / "zis-video-workflow"
        if not candidate.is_absolute():
            candidate = self.paths.root / candidate
        return candidate.resolve()

    def probe(self) -> AdapterProbe:
        root = self.configured_root()
        root_found = root.is_dir()
        command = os.getenv("ZIS_VIDEO_WORKFLOW_COMMAND", "").strip()
        configured = bool(command)
        if root_found and configured:
            return AdapterProbe(
                "available",
                True,
                True,
                str(root),
                "external root and explicit command are configured",
                True,
                "none",
            )
        missing = []
        if not root_found:
            missing.append("ZIS_VIDEO_WORKFLOW_PATH or sibling checkout")
        if not configured:
            missing.append("ZIS_VIDEO_WORKFLOW_COMMAND")
        return AdapterProbe(
            "capability_unavailable",
            root_found,
            configured,
            str(root) if root_found else None,
            f"missing: {', '.join(missing)}",
            True,
            "Configure the missing adapter values on a machine with zis-video-workflow, or continue content work without video production.",
        )

    def run(
        self,
        source: Path,
        task_dir: Path,
        handoff: Path,
        revision_request: Path | None = None,
    ) -> dict[str, Any]:
        probe = self.probe()
        if probe.status != "available":
            return probe.as_dict()
        command = os.environ["ZIS_VIDEO_WORKFLOW_COMMAND"]
        prefix = shlex.split(command, posix=os.name != "nt")
        arguments = prefix + [
                "--input",
                str(source.resolve()),
                "--task-dir",
                str(task_dir.resolve()),
                "--handoff",
                str(handoff.resolve()),
            ]
        if revision_request is not None:
            arguments += ["--revision-request", str(revision_request.resolve())]
        result = subprocess.run(
            arguments,
            cwd=self.configured_root(),
            capture_output=True,
            text=True,
            check=False,
        )
        manifest = task_dir / "outputs" / "video_manifest.json"
        if result.returncode != 0 or not manifest.is_file():
            return {
                "status": "failed",
                "returncode": result.returncode,
                "stdout_tail": result.stdout[-2000:],
                "stderr_tail": result.stderr[-2000:],
                "required_action": "Inspect the configured external CLI and adapter contract.",
            }
        value = read_json(manifest)
        value["status"] = "available"
        return value
