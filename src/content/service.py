from __future__ import annotations

import re
from typing import Any


class ContentService:
    """Deterministic v1 content baseline; Codex may replace/refine its payload."""

    def extract_topic(self, request: str) -> str:
        cleaned = request.strip().rstrip("。.!！?")
        match = re.search(
            r"(?:关于|介绍)\s*(.+?)(?:(?:的)?\s*\d+\s*秒|(?:的)?短视频|视频|$)",
            cleaned,
            flags=re.IGNORECASE,
        )
        if match and match.group(1).strip():
            return match.group(1).strip(" 的")
        cleaned = re.sub(r"^(我想|我要|请|帮我|做一条|制作一条)+", "", cleaned).strip()
        return cleaned[:60] or "待确认主题"

    def topic_to_script(
        self, request: str, platform: str = "unspecified"
    ) -> dict[str, Any]:
        topic = self.extract_topic(request)
        title = f"{topic}：一个人也能用团队方式推进内容"
        hook = f"你以为“{topic}”只是同时打开几个 AI 对话吗？真正的关键不是数量，而是分工和交接。"
        body = (
            "第一，先设一个总控，只让它理解目标、拆解流程和维护进度；"
            "第二，把内容判断、视频制作和质量审核交给不同角色，每个角色只读取完成工作所需的上下文；"
            "第三，用结构化文件交接，让下一步知道输入、约束、产物和责任人。"
        )
        close = (
            "如果审核不通过，问题会按责任人自动打回，并限制返工次数；通过后才交付。"
            "这样做的价值，不是让流程看起来复杂，而是让一个人也能稳定复用一套可检查、可维护的团队工作方式。"
        )
        script = "\n".join((hook, body, close))
        return {
            "goal": request,
            "platform": platform,
            "selected_topic": topic,
            "content_summary": f"用总控、专业分工、结构化交接和独立审核解释{topic}的工作方式。",
            "structure": [
                {"section": "hook", "purpose": "纠正常见误解", "text": hook},
                {"section": "body", "purpose": "给出三步工作方式", "text": body},
                {"section": "close", "purpose": "说明审核闭环与实际价值", "text": close},
            ],
            "script": script,
            "title": title,
            "post_copy": f"{topic}不是多开几个窗口，而是一套有责任、有交接、有审核的工作系统。",
            "source_range": None,
            "constraints": ["目标时长约60秒", "不得虚构数据或来源"],
            "production_requirements": {
                "target_duration_seconds": 60,
                "needs_source_video": True,
                "caption_language": "zh-CN",
            },
        }

    def revise(
        self, request: str, platform: str, previous: dict[str, Any], issues: list[dict[str, Any]]
    ) -> dict[str, Any]:
        revised = self.topic_to_script(request, platform)
        revised["revision_note"] = {
            "replaced_previous_artifact": True,
            "addressed_issue_codes": [item.get("code", "unknown") for item in issues],
        }
        return revised

