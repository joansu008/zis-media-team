from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProviderCapability:
    available: bool
    reason: str
    required_environment: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "reason": self.reason,
            "required_environment": self.required_environment,
        }


@dataclass(frozen=True)
class ModelRequest:
    instructions: str
    input_text: str
    schema_name: str
    schema: dict[str, Any]
    max_output_tokens: int = 3000


@dataclass(frozen=True)
class ModelResponse:
    output_text: str
    provider: str
    model: str
    latency_ms: int
    usage: dict[str, Any] = field(default_factory=dict)
    response_id: str | None = None


class ModelProvider(ABC):
    name: str

    @abstractmethod
    def capability(self) -> ProviderCapability:
        raise NotImplementedError

    @abstractmethod
    def generate(self, request: ModelRequest, model: str) -> ModelResponse:
        raise NotImplementedError


class ModelExecutionError(RuntimeError):
    code = "model_execution_failed"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.details = details or {}
        super().__init__(message)

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.code, "message": str(self), "details": self.details}


class ProviderUnavailable(ModelExecutionError):
    code = "model_capability_unavailable"


class ModelRequestFailed(ModelExecutionError):
    code = "model_request_failed"


class ModelOutputInvalid(ModelExecutionError):
    code = "model_output_invalid"
