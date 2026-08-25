from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


_ENV_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _load_local_env(path: Path) -> None:
    """Load a small, dependency-free .env subset without overriding shell values."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not _ENV_KEY.fullmatch(key):
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    workspace: Path

    @classmethod
    def discover(
        cls, root: Path | None = None, workspace: Path | None = None
    ) -> "ProjectPaths":
        project_root = (root or Path(__file__).resolve().parents[1]).resolve()
        _load_local_env(project_root / ".env")
        configured = workspace or Path(os.getenv("ZIS_MEDIA_WORKSPACE", "workspace"))
        workspace_root = configured if configured.is_absolute() else project_root / configured
        return cls(root=project_root, workspace=workspace_root.resolve())

    @property
    def agents_registry(self) -> Path:
        return self.root / "registry" / "agents.yaml"

    @property
    def skills_registry(self) -> Path:
        return self.root / "registry" / "skills.yaml"

    def workflow(self, workflow_id: str) -> Path:
        return self.root / "workflows" / f"{workflow_id}.yaml"

    def task_dir(self, task_id: str) -> Path:
        if not task_id.startswith("task_") or Path(task_id).name != task_id:
            raise ValueError(f"Invalid task id: {task_id}")
        return self.workspace / task_id
