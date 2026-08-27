from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from src.models.base import (
    ModelProvider,
    ModelRequest,
    ModelRequestFailed,
    ModelResponse,
    ProviderCapability,
    ProviderUnavailable,
)


class OpenAIProvider(ModelProvider):
    name = "openai"

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.responses_url = f"{base}/responses"
        self.timeout_seconds = float(os.getenv("ZIS_MODEL_TIMEOUT_SECONDS", "60"))

    def capability(self) -> ProviderCapability:
        if not self.api_key:
            return ProviderCapability(
                False, "OPENAI_API_KEY is not configured", ["OPENAI_API_KEY"]
            )
        return ProviderCapability(True, "OpenAI credential is configured")

    def generate(self, request: ModelRequest, model: str) -> ModelResponse:
        capability = self.capability()
        if not capability.available:
            raise ProviderUnavailable(
                capability.reason,
                {"provider": self.name, "required_environment": capability.required_environment},
            )
        if not model.strip():
            raise ProviderUnavailable(
                "Model name is not configured", {"provider": self.name}
            )

        payload = {
            "model": model,
            "instructions": request.instructions,
            "input": request.input_text,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": request.schema_name,
                    "strict": True,
                    "schema": _schema_for_api(request.schema),
                }
            },
            "max_output_tokens": request.max_output_tokens,
            "store": False,
        }
        http_request = urllib.request.Request(
            self.responses_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(
                http_request, timeout=self.timeout_seconds
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            raise ModelRequestFailed(
                f"OpenAI request failed with HTTP {error.code}",
                {"provider": self.name, "http_status": error.code},
            ) from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise ModelRequestFailed(
                f"OpenAI request failed: {error}", {"provider": self.name}
            ) from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ModelRequestFailed(
                "OpenAI returned an unreadable response", {"provider": self.name}
            ) from error

        latency_ms = int((time.monotonic() - started) * 1000)
        output_text = _extract_output_text(body)
        if output_text is None:
            raise ModelRequestFailed(
                "OpenAI response did not contain output text",
                {"provider": self.name, "response_id": body.get("id")},
            )
        usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
        return ModelResponse(
            output_text=output_text,
            provider=self.name,
            model=str(body.get("model") or model),
            latency_ms=latency_ms,
            usage=usage,
            response_id=body.get("id"),
        )


def _extract_output_text(body: dict[str, Any]) -> str | None:
    direct = body.get("output_text")
    if isinstance(direct, str):
        return direct
    for item in body.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str):
                    return text
    return None


def _schema_for_api(value: Any) -> Any:
    """Keep the broadly supported Structured Outputs subset; validate full rules locally."""
    if isinstance(value, dict):
        return {
            key: _schema_for_api(item)
            for key, item in value.items()
            if key
            not in {
                "$schema",
                "$id",
                "minLength",
                "maxLength",
                "minimum",
                "maximum",
                "multipleOf",
                "minItems",
                "maxItems",
                "pattern",
                "format",
            }
        }
    if isinstance(value, list):
        return [_schema_for_api(item) for item in value]
    return value
