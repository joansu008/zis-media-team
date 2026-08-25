from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RouteDecision:
    workflow_id: str
    reason: str
    confidence: float

    def as_dict(self) -> dict[str, object]:
        return {
            "workflow_id": self.workflow_id,
            "reason": self.reason,
            "confidence": self.confidence,
        }


class WorkflowRouter:
    LONG_VIDEO_TERMS = (
        "直播",
        "长视频",
        "切片",
        "切成",
        "片段",
        "找出",
        "素材里",
        "from this video",
        "clips",
        "livestream",
    )

    def route(self, request: str, input_path: str | None = None) -> RouteDecision:
        normalized = request.strip().lower()
        matches = [term for term in self.LONG_VIDEO_TERMS if term in normalized]
        if matches or input_path:
            reason = (
                f"matched long-video intent: {', '.join(matches)}"
                if matches
                else "source media was supplied"
            )
            return RouteDecision("long_video_to_clips", reason, 0.95)
        return RouteDecision(
            "topic_to_script",
            "no source-media intent; route to topic and script production",
            0.85,
        )

