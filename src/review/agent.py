from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config import ProjectPaths
from src.io import read_json
from src.models.base import ModelProvider
from src.models.runner import StructuredModelRunner


class AIReviewAgent:
    PASS_SCORE = 80

    def __init__(
        self,
        paths: ProjectPaths,
        provider: ModelProvider,
        model: str,
        max_retries: int = 1,
    ) -> None:
        self.schema = read_json(paths.root / "schemas" / "ai-review.schema.json")
        self.role = (paths.root / "agents" / "review.md").read_text(encoding="utf-8")
        self.rules = (paths.root / "rules" / "review.md").read_text(encoding="utf-8")
        self.runner = StructuredModelRunner(
            provider, model, "review_agent", max_retries=max_retries
        )

    def review_content(
        self,
        task: dict[str, Any],
        artifact: dict[str, Any],
        *,
        task_dir: Path,
    ) -> dict[str, Any]:
        instructions = (
            f"{self.role}\n\n{self.rules}\n\n"
            "Act as an independent editor. You have no access to the producer's hidden "
            "reasoning and must not trust self-evaluation in the artifact. Judge topic "
            "clarity, hook strength, specificity, information density, logical flow, true "
            "title-content fit, actionable handles, empty clichés, goal fit, and whether "
            "this is worth producing as video. PASS requires score >= 80, no high-severity "
            "issue, and a clear production-worthy script. Every issue needs evidence and a "
            "specific fix. Return only schema-valid JSON."
        )
        input_payload = {
            "original_task": {
                "request": task["request"],
                "platform": task["platform"],
                "workflow_id": task["workflow_id"],
            },
            "content_artifact": artifact,
        }
        return self.runner.run(
            task_id=task["task_id"],
            task_dir=task_dir,
            instructions=instructions,
            input_text=json.dumps(input_payload, ensure_ascii=False),
            schema_name="ai_content_review",
            schema=self.schema,
            max_output_tokens=2200,
        )
