from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from src.io import read_json, write_json
from src.manager.runtime import ManagerRuntime
from src.models.base import ModelProvider, ModelRequest, ModelResponse, ProviderCapability


ROOT = Path(__file__).resolve().parents[1]


class NeverCalledProvider(ModelProvider):
    name = "never_called"

    def __init__(self) -> None:
        self.calls = 0

    def capability(self) -> ProviderCapability:
        return ProviderCapability(True, "fixture", [])

    def generate(self, request: ModelRequest, model: str) -> ModelResponse:
        self.calls += 1
        raise AssertionError("codex_native must not call the API provider")


def content_artifact(goal: str, platform: str, attempt: int = 0) -> dict[str, Any]:
    hook = "副业坚持不到一个月，常常不是因为懒，而是启动方式让反馈来得太迟。"
    body = (
        "很多人第一周同时学剪辑、做账号、找客户，还把目标只写成赚钱。"
        "任务太多、反馈太慢，大脑就会把正常冷启动误判成失败。"
        "先固定一种交付，每天只做一个三十分钟动作，再记录触达数、回复数和完成次数。"
    )
    close = "连续观察四周后，再决定调整方向还是扩大投入，让反馈替代意志力硬扛。"
    return {
        "goal": goal,
        "platform": platform,
        "selected_topic": "副业早期中断来自反馈周期失衡",
        "content_summary": "解释副业冷启动为何消耗意志力，并给出四周验证法。",
        "structure": [
            {"section": "hook", "purpose": "反转归因", "text": hook},
            {"section": "body", "purpose": "解释机制与动作", "text": body},
            {"section": "close", "purpose": "给出判断标准", "text": close},
        ],
        "script": "\n".join((hook, body, close)),
        "title": "副业坚持不到一个月，可能不是自律问题",
        "post_copy": "先缩短反馈周期，再谈长期坚持。",
        "source_range": None,
        "constraints": ["约60秒", "不虚构数据"],
        "production_requirements": {
            "target_duration_seconds": 60,
            "needs_source_video": False,
            "caption_language": "zh-CN",
        },
        "revision_attempt": attempt,
        "addressed_issues": [] if not attempt else ["specificity"],
        "execution_mode": "codex_native",
    }


def pass_review() -> dict[str, Any]:
    return {
        "review_status": "PASS",
        "score": 91,
        "issues": [],
        "owner_agent": "",
        "required_action": "",
        "need_re_review": False,
    }


def fail_review() -> dict[str, Any]:
    return {
        "review_status": "FAIL",
        "score": 66,
        "issues": [
            {
                "code": "specificity",
                "category": "actionability",
                "severity": "high",
                "message": "动作仍不够具体。",
                "evidence": "没有说明每天记录哪些反馈指标。",
                "suggested_fix": "明确每日动作以及触达、回复、完成次数三个指标。",
            }
        ],
        "owner_agent": "content_agent",
        "required_action": "补充每日动作和可观察指标。",
        "need_re_review": True,
    }


class NativeAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name) / "workspace"
        self.provider = NeverCalledProvider()
        self.runtime = ManagerRuntime(
            root=ROOT,
            workspace=self.workspace,
            execution_mode="codex_native",
            model_provider=self.provider,
        )
        self.result = self.runtime.start(
            "为什么很多人做副业总是坚持不到一个月？", platform="douyin"
        )
        self.task_id = self.result["task_id"]
        self.task_dir = Path(self.result["task_dir"])

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def submit_content(self, attempt: int = 0, subagent: str = "content-subagent") -> dict[str, Any]:
        path = self.task_dir / "inputs" / f"content_submission_v{attempt + 1}.json"
        write_json(
            path,
            content_artifact(
                "为什么很多人做副业总是坚持不到一个月？", "douyin", attempt
            ),
        )
        return self.runtime.submit_native_content(
            self.task_id,
            path,
            subagent_id=subagent,
            started_at="2026-08-27T01:00:00+00:00",
            completed_at="2026-08-27T01:00:01+00:00",
        )

    def submit_review(self, value: dict[str, Any], subagent: str = "review-subagent") -> dict[str, Any]:
        version = len(list((self.task_dir / "reviews").glob("review_v*.json"))) + 1
        path = self.task_dir / "inputs" / f"review_submission_v{version}.json"
        write_json(path, value)
        return self.runtime.submit_native_review(
            self.task_id,
            path,
            subagent_id=subagent,
            started_at="2026-08-27T01:01:00+00:00",
            completed_at="2026-08-27T01:01:01+00:00",
        )

    def test_22_start_returns_bounded_content_delegation_without_api(self) -> None:
        action = self.result["next_action"]
        self.assertEqual(action["agent_id"], "content_agent")
        self.assertEqual(action["execution_mode"], "codex_native")
        self.assertNotIn("review_file", action["context"])
        self.assertEqual(self.provider.calls, 0)

    def test_23_invalid_content_json_is_rejected_without_handoff(self) -> None:
        path = self.task_dir / "inputs" / "invalid.json"
        path.write_text("not-json", encoding="utf-8")
        result = self.runtime.submit_native_content(
            self.task_id,
            path,
            subagent_id="bad-content",
            started_at="2026-08-27T01:00:00+00:00",
        )
        self.assertEqual(result["submission"]["status"], "model_output_invalid")
        self.assertEqual(result["status"], "content_processing")
        self.assertFalse((self.task_dir / "handoffs" / "content_to_review.json").exists())

    def test_24_valid_content_runs_gates_then_requests_separate_review(self) -> None:
        result = self.submit_content()
        self.assertEqual(result["status"], "reviewing")
        self.assertEqual(result["next_action"]["agent_id"], "review_agent")
        context = result["next_action"]["context"]
        self.assertNotIn("content_role_file", context)
        self.assertTrue((self.task_dir / "reviews" / "deterministic_gate_v1.json").is_file())

    def test_25_native_review_pass_is_fused_and_approved(self) -> None:
        self.submit_content(subagent="content-A")
        result = self.submit_review(pass_review(), subagent="review-B")
        self.assertEqual(result["status"], "awaiting_video")
        self.assertEqual(result["review"]["execution_mode"], "codex_native")
        self.assertEqual(result["review"]["review_layers"]["ai_review"], "PASS")

    def test_26_fail_returns_state_driven_revision_context(self) -> None:
        self.submit_content()
        result = self.submit_review(fail_review())
        action = result["next_action"]
        self.assertEqual(result["status"], "revision_required")
        self.assertEqual(action["agent_id"], "content_agent")
        self.assertTrue(action["is_revision"])
        self.assertEqual(action["revision_attempt"], 1)
        self.assertIn("previous_artifact_file", action["context"])
        self.assertIn("revision_request_file", action["context"])

    def test_27_revision_then_re_review_passes(self) -> None:
        self.submit_content()
        self.submit_review(fail_review())
        self.submit_content(attempt=1, subagent="content-revision")
        result = self.submit_review(pass_review(), subagent="review-second")
        self.assertEqual(result["status"], "awaiting_video")
        revised = read_json(self.task_dir / "outputs" / "content_package_v2.json")
        self.assertEqual(revised["revision_attempt"], 1)
        self.assertIn("specificity", revised["addressed_issues"])

    def test_28_three_failed_reviews_stop_after_two_revisions(self) -> None:
        for attempt in range(3):
            self.submit_content(attempt=attempt, subagent=f"content-{attempt}")
            result = self.submit_review(fail_review(), subagent=f"review-{attempt}")
        state = read_json(self.task_dir / "state.json")
        self.assertEqual(result["status"], "needs_human_review")
        self.assertEqual(state["revision_counts"]["content"], 2)
        self.assertEqual(len(list((self.task_dir / "reviews").glob("review_v*.json"))), 3)

    def test_29_native_logs_preserve_role_and_temporary_subagent_ids(self) -> None:
        self.submit_content(subagent="temporary-content-123")
        self.submit_review(pass_review(), subagent="temporary-review-456")
        logs = [
            read_json(path)
            for path in (self.task_dir / "logs").glob("native_agent_*.json")
        ]
        self.assertEqual({item["execution_mode"] for item in logs}, {"codex_native"})
        self.assertEqual(
            {item["agent_id"] for item in logs}, {"content_agent", "review_agent"}
        )
        self.assertEqual(
            {item["subagent_id"] for item in logs},
            {"temporary-content-123", "temporary-review-456"},
        )
        self.assertTrue(all("token_usage" not in item for item in logs))
        self.assertEqual(self.provider.calls, 0)


if __name__ == "__main__":
    unittest.main()
