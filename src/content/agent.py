from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config import ProjectPaths
from src.io import read_json
from src.models.base import ModelProvider
from src.models.runner import StructuredModelRunner


class ModelBackedContentAgent:
    def __init__(
        self,
        paths: ProjectPaths,
        provider: ModelProvider,
        model: str,
        max_retries: int = 1,
    ) -> None:
        self.paths = paths
        self.schema = read_json(paths.root / "schemas" / "content-artifact.schema.json")
        self.role = (paths.root / "agents" / "content.md").read_text(encoding="utf-8")
        self.rules = (paths.root / "rules" / "content.md").read_text(encoding="utf-8")
        self.runner = StructuredModelRunner(
            provider, model, "content_agent", max_retries=max_retries
        )

    def topic_to_script(
        self,
        request: str,
        platform: str,
        *,
        task_id: str,
        task_dir: Path,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        instructions = (
            f"{self.role}\n\n{self.rules}\n\n"
            "Create an original, topic-specific Chinese short-video content package. "
            "Do not reuse a generic Multi-Agent template. The hook, central claim, "
            "structure, examples, script and title must follow the actual topic. "
            "For an initial artifact set revision_attempt to 0 and addressed_issues to []. "
            "Set execution_mode to api. "
            "Return only the JSON object required by the supplied schema."
        )
        input_payload = {
            "goal": request,
            "platform": platform,
            "necessary_context": context or {},
        }
        artifact = self.runner.run(
            task_id=task_id,
            task_dir=task_dir,
            instructions=instructions,
            input_text=json.dumps(input_payload, ensure_ascii=False),
            schema_name="content_artifact",
            schema=self.schema,
            max_output_tokens=3500,
        )
        artifact["goal"] = request
        artifact["platform"] = platform
        artifact["revision_attempt"] = 0
        artifact["addressed_issues"] = []
        artifact["execution_mode"] = "api"
        return artifact

    def revise(
        self,
        request: str,
        platform: str,
        previous: dict[str, Any],
        issues: list[dict[str, Any]],
        required_action: str,
        revision_attempt: int,
        *,
        task_id: str,
        task_dir: Path,
    ) -> dict[str, Any]:
        instructions = (
            f"{self.role}\n\n{self.rules}\n\n"
            "Revise the previous artifact only to resolve the supplied independent review "
            "issues. Preserve strong material that is unrelated to those issues. Do not "
            "replace the work with a generic template. Return a complete artifact, not a "
            "patch. Set revision_attempt to the supplied attempt and list the issue codes "
            "you addressed in addressed_issues. Set execution_mode to api. Return only schema-valid JSON."
        )
        input_payload = {
            "original_goal": request,
            "platform": platform,
            "previous_artifact": previous,
            "review_issues": issues,
            "required_action": required_action,
            "revision_attempt": revision_attempt,
        }
        artifact = self.runner.run(
            task_id=task_id,
            task_dir=task_dir,
            instructions=instructions,
            input_text=json.dumps(input_payload, ensure_ascii=False),
            schema_name="content_revision",
            schema=self.schema,
            max_output_tokens=3500,
        )
        artifact["goal"] = request
        artifact["platform"] = platform
        artifact["revision_attempt"] = revision_attempt
        artifact["execution_mode"] = "api"
        return artifact
