from __future__ import annotations

from pathlib import Path
from typing import Any

from src.io import utc_now


def _issue(
    code: str,
    message: str,
    severity: str,
    *,
    category: str = "deterministic_gate",
    evidence: str = "",
    suggested_fix: str = "",
) -> dict[str, str]:
    return {
        "code": code,
        "category": category,
        "message": message,
        "severity": severity,
        "evidence": evidence,
        "suggested_fix": suggested_fix or message,
    }


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
            "execution_mode": "deterministic",
            "review_layers": {"deterministic_gates": "PASS" if passed else "FAIL"},
        }

    def fuse_content_reviews(
        self,
        task: dict[str, Any],
        deterministic: dict[str, Any],
        ai_review: dict[str, Any],
        review_version: int,
        execution_mode: str = "api",
    ) -> dict[str, Any]:
        issues = list(deterministic["issues"]) + list(ai_review["issues"])
        ai_claims_pass = ai_review["review_status"] == "PASS"
        ai_has_high_issue = any(
            item["severity"] == "high" for item in ai_review["issues"]
        )
        if ai_claims_pass and (
            ai_review["score"] < 80
            or ai_has_high_issue
            or ai_review["need_re_review"]
        ):
            issues.append(
                _issue(
                    "ai_review_inconsistent",
                    "AI审核结论与分数、问题严重度或复审标记不一致。",
                    "high",
                    category="review_integrity",
                    evidence=f"status={ai_review['review_status']}, score={ai_review['score']}, need_re_review={ai_review['need_re_review']}",
                    suggested_fix="按PASS门槛重新给出一致、可执行的审核结论。",
                )
            )
        if ai_review["review_status"] == "FAIL" and not ai_review["issues"]:
            issues.append(
                _issue(
                    "ai_review_missing_issue",
                    "AI审核判定FAIL但没有提供问题证据。",
                    "high",
                    category="review_integrity",
                    suggested_fix="给出至少一个带证据和修复建议的问题。",
                )
            )
        passed = (
            deterministic["review_status"] == "PASS"
            and ai_claims_pass
            and ai_review["score"] >= 80
            and not ai_review["need_re_review"]
            and not any(item["severity"] == "high" for item in issues)
        )
        required_actions = []
        if deterministic.get("required_action"):
            required_actions.append(deterministic["required_action"])
        if ai_review.get("required_action"):
            required_actions.append(ai_review["required_action"])
        if not passed and not required_actions:
            required_actions.extend(
                item.get("suggested_fix") or item["message"] for item in issues
            )
        return {
            "task_id": task["task_id"],
            "review_version": review_version,
            "artifact_type": "content_package",
            "review_status": "PASS" if passed else "FAIL",
            "score": min(deterministic["score"], ai_review["score"]),
            "issues": issues,
            "owner_agent": "" if passed else "content_agent",
            "required_action": "；".join(required_actions),
            "need_re_review": not passed,
            "created_at": utc_now(),
            "reviewed_against": {
                "request": task["request"],
                "workflow_id": task["workflow_id"],
            },
            "execution_mode": execution_mode,
            "review_layers": {
                "deterministic_gates": deterministic["review_status"],
                "ai_review": ai_review["review_status"],
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
