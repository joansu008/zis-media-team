from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from src.models.base import (
    ModelExecutionError,
    ModelOutputInvalid,
    ModelProvider,
    ModelRequest,
    ModelRequestFailed,
    ProviderUnavailable,
)
from src.models.logging import log_model_call
from src.validation import SchemaValidationError, validate_json_schema


class StructuredModelRunner:
    def __init__(
        self,
        provider: ModelProvider,
        model: str,
        agent_id: str,
        max_retries: int = 1,
    ) -> None:
        self.provider = provider
        self.model = model
        self.agent_id = agent_id
        self.max_retries = max(0, max_retries)

    def run(
        self,
        *,
        task_id: str,
        task_dir: Path,
        instructions: str,
        input_text: str,
        schema_name: str,
        schema: dict[str, Any],
        max_output_tokens: int,
    ) -> dict[str, Any]:
        request = ModelRequest(
            instructions=instructions,
            input_text=input_text,
            schema_name=schema_name,
            schema=schema,
            max_output_tokens=max_output_tokens,
        )
        capability = self.provider.capability()
        if not capability.available or not self.model.strip():
            reason = capability.reason if not capability.available else "Model name is not configured"
            required_environment = list(capability.required_environment)
            if not self.model.strip():
                model_variable = (
                    "ZIS_CONTENT_MODEL"
                    if self.agent_id == "content_agent"
                    else "ZIS_REVIEW_MODEL"
                )
                if model_variable not in required_environment:
                    required_environment.append(model_variable)
            error = ProviderUnavailable(
                reason,
                {
                    "provider": self.provider.name,
                    "model": self.model,
                    "required_environment": required_environment,
                },
            )
            log_model_call(
                task_dir,
                task_id=task_id,
                agent_id=self.agent_id,
                provider=self.provider.name,
                model=self.model,
                execution_mode="api",
                success=False,
                latency_ms=0,
                token_usage={},
                retry_count=0,
                error_code=error.code,
            )
            raise error

        last_error: ModelExecutionError | None = None
        for attempt in range(self.max_retries + 1):
            started = time.monotonic()
            response = None
            try:
                response = self.provider.generate(request, self.model)
                try:
                    parsed = json.loads(response.output_text)
                except json.JSONDecodeError as error:
                    raise ModelOutputInvalid(
                        "Model output is not valid JSON",
                        {"parse_error": str(error), "attempt": attempt + 1},
                    ) from error
                if not isinstance(parsed, dict):
                    raise ModelOutputInvalid(
                        "Model output must be a JSON object", {"attempt": attempt + 1}
                    )
                try:
                    validate_json_schema(parsed, schema)
                except SchemaValidationError as error:
                    raise ModelOutputInvalid(
                        "Model output failed schema validation",
                        {"validation_errors": error.errors, "attempt": attempt + 1},
                    ) from error
                log_model_call(
                    task_dir,
                    task_id=task_id,
                    agent_id=self.agent_id,
                    provider=response.provider,
                    model=response.model,
                    execution_mode="api",
                    success=True,
                    latency_ms=response.latency_ms,
                    token_usage=response.usage,
                    retry_count=attempt,
                )
                return parsed
            except (ProviderUnavailable, ModelRequestFailed, ModelOutputInvalid) as error:
                last_error = error
                latency_ms = int((time.monotonic() - started) * 1000)
                log_model_call(
                    task_dir,
                    task_id=task_id,
                    agent_id=self.agent_id,
                    provider=response.provider if response is not None else self.provider.name,
                    model=response.model if response is not None else self.model,
                    execution_mode="api",
                    success=False,
                    latency_ms=response.latency_ms if response is not None else latency_ms,
                    token_usage=response.usage if response is not None else {},
                    retry_count=attempt,
                    error_code=error.code,
                )
                if isinstance(error, ProviderUnavailable):
                    break
        assert last_error is not None
        raise last_error
