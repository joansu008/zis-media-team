from __future__ import annotations

import os

from src.models.base import (
    ModelProvider,
    ModelRequest,
    ModelResponse,
    ProviderCapability,
    ProviderUnavailable,
)
from src.models.openai_provider import OpenAIProvider


class UnavailableProvider(ModelProvider):
    def __init__(self, provider_name: str, reason: str) -> None:
        self.name = provider_name or "unconfigured"
        self.reason = reason

    def capability(self) -> ProviderCapability:
        return ProviderCapability(
            False,
            self.reason,
            ["ZIS_MODEL_PROVIDER", "ZIS_CONTENT_MODEL", "ZIS_REVIEW_MODEL"],
        )

    def generate(self, request: ModelRequest, model: str) -> ModelResponse:
        raise ProviderUnavailable(
            self.reason, {"provider": self.name, "model": model}
        )


def create_model_provider(provider_name: str | None = None) -> ModelProvider:
    configured = (provider_name or os.getenv("ZIS_MODEL_PROVIDER", "")).strip().lower()
    if configured == "openai":
        return OpenAIProvider()
    if not configured:
        return UnavailableProvider("unconfigured", "ZIS_MODEL_PROVIDER is not configured")
    return UnavailableProvider(configured, f"Unsupported model provider: {configured}")
