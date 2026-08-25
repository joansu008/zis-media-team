from __future__ import annotations

from pathlib import Path
from typing import Any

from src.io import read_json


class Registry:
    """Loads JSON-compatible YAML registries with only the standard library."""

    def __init__(self, agents_path: Path, skills_path: Path) -> None:
        self._agents = read_json(agents_path)
        self._skills = read_json(skills_path)

    def agent(self, agent_id: str) -> dict[str, Any]:
        for item in self._agents["agents"]:
            if item["agent_id"] == agent_id:
                return item
        raise KeyError(f"Unknown agent: {agent_id}")

    def skill(self, skill_id: str) -> dict[str, Any]:
        for item in self._skills["skills"]:
            if item["id"] == skill_id:
                return item
        raise KeyError(f"Unknown skill: {skill_id}")

    def workflow(self, path: Path) -> dict[str, Any]:
        return read_json(path)

