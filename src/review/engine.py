from __future__ import annotations

from pathlib import Path
from typing import Any

from src.io import utc_now


def _issue(code: str, message: str, severity: str) -> dict[str, str]:
    return {"code": code, "message": message, "severity": severity}


class ReviewEngine:
    UNSUPPORTED_ABSOLUTES = ("百分之百", "100%保证", "绝对不会", "全网第一")

    def review_content(
        self,
        task: dict[str, Any],
        payload: dict[str, Any],
        review_version: int,
    ) -> dict[str, Any]:
        issues: list[dict[str, str]] = []
        topic = str(payload.get("selected_topic", "")).strip()
        title = str(payload.get("title", "")).strip()
        script = str(payload.get("script", "")).strip()
        summary = str(payload.get("content_summary", "")).strip()

        if not topic:
            issues.append(_issue("missing_topic", "缺少明确选题。", "high"))
        if not title:
            issues.append(_issue("missing_title", "缺少标题。", "high"))
        if not script:
            issues.append(_issue("missing_script", "缺少口播稿。", "high"))
        elif len(script) < 100:
            issues.append(_issue("script_too_thin", "口播稿过短，无法完整支撑任务目标。", "high"))
        if not summary:
            issues.append(_issue("missing_summary", "缺少内容摘要。", "medium"))
        if topic and title and topic.lower() not in title.lower():
            issues.append(_issue("title_topic_mismatch", "标题没有覆盖选定主题。", "high"))
        if script and not any(marker in script for marker in ("？", "?", "第一", "先")):
            issues.append(_issue("weak_opening", "开头未快速建立问题或相关性。", "medium"))
        found_absolutes = [term for term in self.UNSUPPORTED_ABSOLUTES if term in script]
        if found_absolutes:
            issues.append(
                _issue(
                    "unsupported_absolute",
                    f"出现明显无依据的绝对化表达：{', '.join(found_absolutes)}。",
                    "high",
                )
            )

        deductions = {"low": 5, "medium": 12, "high": 25}
        score = max(0, 100 - sum(deductions[item["severity"]] for item in issues))
        passed = score >= 80 and not any(item["severity"] == "high" for item in issues)
        return {
            "task_id": task["task_id"],
            "review_version": review_version,
            "artifact_type": "content_package",
            "review_status": "PASS" if passed else "FAIL",
            "score": score,
            "issues": issues,
            "owner_agent": "" if passed else "content_agent",
            "required_action": "" if passed else "；".join(item["message"] for item in issues),
            "need_re_review": not passed,
            "created_at": utc_now(),
            "reviewed_against": {
                "request": task["request"],
                "workflow_id": task["workflow_id"],
            },
        }

    def review_video(
        self,
        task: dict[str, Any],
        payload: dict[str, Any],
        task_dir: Path,
        review_version: int,
    ) -> dict[str, Any]:
        issues: list[dict[str, str]] = []
        output_value = str(payload.get("output_file", "")).strip()
        if not output_value:
            issues.append(_issue("missing_output", "没有声明输出视频文件。", "high"))
        else:
            output_path = Path(output_value)
            if not output_path.is_absolute():
                output_path = task_dir / output_path
            if not output_path.is_file() or output_path.stat().st_size == 0:
                issues.append(_issue("invalid_output", "输出视频不存在或为空文件。", "high"))

        timeline = payload.get("timeline", [])
        previous_end = -1.0
        seen: set[tuple[float, float]] = set()
        for index, item in enumerate(timeline):
            try:
                start, end = float(item["start"]), float(item["end"])
            except (KeyError, TypeError, ValueError):
                issues.append(_issue("invalid_timeline", f"第{index + 1}段时间轴无效。", "high"))
                continue
            if start < 0 or end <= start or start < previous_end:
                issues.append(_issue("invalid_timeline", f"第{index + 1}段时间轴顺序或范围无效。", "high"))
            if (start, end) in seen:
                issues.append(_issue("duplicate_segment", f"第{index + 1}段发生重复。", "high"))
            seen.add((start, end))
            previous_end = max(previous_end, end)

        if payload.get("subtitles_required") and not payload.get("subtitle_file"):
            issues.append(_issue("missing_subtitles", "Workflow要求字幕，但没有字幕文件。", "high"))

        score = max(0, 100 - 25 * len(issues))
        passed = not issues
        return {
            "task_id": task["task_id"],
            "review_version": review_version,
            "artifact_type": "video_package",
            "review_status": "PASS" if passed else "FAIL",
            "score": score,
            "issues": issues,
            "owner_agent": "" if passed else "video_agent",
            "required_action": "" if passed else "；".join(item["message"] for item in issues),
            "need_re_review": not passed,
            "created_at": utc_now(),
        }

