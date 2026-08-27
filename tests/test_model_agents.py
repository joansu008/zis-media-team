from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable
from unittest.mock import patch

from src.config import ProjectPaths
from src.content.agent import ModelBackedContentAgent
from src.io import read_json
from src.manager.runtime import ManagerRuntime
from src.models.base import ModelProvider, ModelRequest, ModelResponse, ProviderCapability
from src.models.openai_provider import OpenAIProvider


ROOT = Path(__file__).resolve().parents[1]


def content_artifact(goal: str, platform: str, angle: str, attempt: int = 0) -> dict[str, Any]:
    hook = f"{angle}：真正的问题通常藏在第一个错误判断里，你可能每天都在重复它。"
    body = (
        f"先把{angle}拆成一个明确目标，再检查最容易忽略的现实约束。"
        "接着不要同时尝试所有办法，只选择一个能在今天完成的小动作，用真实反馈判断方向。"
        "如果结果没有变化，就修改假设，而不是单纯增加时间和意志力。"
    )
    close = "把模糊焦虑改写成可验证动作，连续记录一周，你会更快看到问题究竟出在哪里。"
    return {
        "goal": goal,
        "platform": platform,
        "selected_topic": angle,
        "content_summary": f"围绕{angle}给出一个误区、三个判断和一个可执行动作。",
        "structure": [
            {"section": "hook", "purpose": "建立冲突", "text": hook},
            {"section": "body", "purpose": "展开具体判断", "text": body},
            {"section": "close", "purpose": "给出行动", "text": close},
        ],
        "script": "\n".join((hook, body, close)),
        "title": f"{angle}，先别急着怪自己",
        "post_copy": f"理解{angle}，从一个可验证动作开始。",
        "source_range": None,
        "constraints": ["约60秒", "不虚构数据"],
        "production_requirements": {
            "target_duration_seconds": 60,
            "needs_source_video": True,
            "caption_language": "zh-CN",
        },
        "revision_attempt": attempt,
        "addressed_issues": [] if attempt == 0 else ["too_generic"],
        "execution_mode": "api",
    }


def pass_review() -> dict[str, Any]:
    return {
        "review_status": "PASS",
        "score": 90,
        "issues": [],
        "owner_agent": "",
        "required_action": "",
        "need_re_review": False,
    }


def fail_review() -> dict[str, Any]:
    return {
        "review_status": "FAIL",
        "score": 62,
        "issues": [
            {
                "code": "too_generic",
                "category": "specificity",
                "severity": "high",
                "message": "建议过泛，缺少具体抓手。",
                "evidence": "正文只说要坚持，没有可执行步骤。",
                "suggested_fix": "加入一个当天可完成的动作和判断标准。",
            }
        ],
        "owner_agent": "content_agent",
        "required_action": "加入具体动作和判断标准。",
        "need_re_review": True,
    }


class FakeProvider(ModelProvider):
    name = "fake"

    def __init__(
        self,
        handler: Callable[[ModelRequest, str, int], str | dict[str, Any]],
        available: bool = True,
    ) -> None:
        self.handler = handler
        self.available = available
        self.calls: list[tuple[ModelRequest, str]] = []

    def capability(self) -> ProviderCapability:
        return ProviderCapability(
            self.available,
            "fake available" if self.available else "fake unavailable",
            [] if self.available else ["FAKE_API_KEY"],
        )

    def generate(self, request: ModelRequest, model: str) -> ModelResponse:
        self.calls.append((request, model))
        value = self.handler(request, model, len(self.calls))
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        return ModelResponse(
            output_text=text,
            provider=self.name,
            model=model,
            latency_ms=7,
            usage={"input_tokens": 120, "output_tokens": 240, "total_tokens": 360},
            response_id=f"fake_{len(self.calls)}",
        )


def normal_handler(request: ModelRequest, model: str, call: int) -> dict[str, Any]:
    payload = json.loads(request.input_text)
    if request.schema_name == "ai_content_review":
        return pass_review()
    goal = payload.get("goal") or payload.get("original_goal")
    platform = payload["platform"]
    attempt = int(payload.get("revision_attempt", 0))
    return content_artifact(goal, platform, "模型生成的新主题角度", attempt)


class ModelAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name) / "workspace"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def runtime(self, provider: ModelProvider) -> ManagerRuntime:
        return ManagerRuntime(
            root=ROOT,
            workspace=self.workspace,
            execution_mode="api",
            model_provider=provider,
            content_model="fake-content",
            review_model="fake-review",
        )

    def test_11_content_and_reviewer_use_model_provider_with_valid_json(self) -> None:
        provider = FakeProvider(normal_handler)
        result = self.runtime(provider).start("做一条以前没写死过的新主题短视频")
        task_dir = Path(result["task_dir"])
        artifact = read_json(task_dir / "outputs" / "content_package_v1.json")

        self.assertEqual(result["status"], "awaiting_video")
        self.assertEqual(artifact["execution_mode"], "api")
        self.assertEqual(
            [item[0].schema_name for item in provider.calls],
            ["content_artifact", "ai_content_review"],
        )

    def test_12_invalid_model_json_retries_then_fails_truthfully(self) -> None:
        provider = FakeProvider(lambda request, model, call: "not-json")
        result = self.runtime(provider).start("一个新主题")
        task_dir = Path(result["task_dir"])

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["capability"]["status"], "model_output_invalid")
        self.assertEqual(len(provider.calls), 2)
        self.assertFalse((task_dir / "handoffs" / "content_to_review.json").exists())

    def test_13_provider_unavailable_is_not_replaced_by_template(self) -> None:
        provider = FakeProvider(normal_handler, available=False)
        result = self.runtime(provider).start("为什么总是拖延？")
        task_dir = Path(result["task_dir"])

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["capability"]["status"], "model_capability_unavailable")
        self.assertEqual(provider.calls, [])
        self.assertFalse((task_dir / "outputs" / "content_package_v1.json").exists())

    def test_14_ai_reviewer_pass_is_fused_with_deterministic_gates(self) -> None:
        result = self.runtime(FakeProvider(normal_handler)).start("怎样建立阅读习惯？")
        review = read_json(Path(result["task_dir"]) / "reviews" / "review_v1.json")

        self.assertEqual(review["review_status"], "PASS")
        self.assertEqual(review["execution_mode"], "api")
        self.assertEqual(review["review_layers"]["deterministic_gates"], "PASS")
        self.assertEqual(review["review_layers"]["ai_review"], "PASS")

    def test_15_ai_fail_causes_revision_then_ai_re_review_pass(self) -> None:
        review_calls = 0

        def handler(request: ModelRequest, model: str, call: int) -> dict[str, Any]:
            nonlocal review_calls
            payload = json.loads(request.input_text)
            if request.schema_name == "ai_content_review":
                review_calls += 1
                return fail_review() if review_calls == 1 else pass_review()
            goal = payload.get("goal") or payload.get("original_goal")
            attempt = int(payload.get("revision_attempt", 0))
            return content_artifact(goal, payload["platform"], "副业坚持的真实阻力", attempt)

        provider = FakeProvider(handler)
        result = self.runtime(provider).start("为什么很多人做副业总是坚持不到一个月？")
        task_dir = Path(result["task_dir"])
        revised = read_json(task_dir / "outputs" / "content_package_v2.json")

        self.assertEqual(result["status"], "awaiting_video")
        self.assertEqual(revised["revision_attempt"], 1)
        self.assertIn("too_generic", revised["addressed_issues"])
        self.assertEqual(len(list((task_dir / "reviews").glob("review_v*.json"))), 2)

    def test_16_repeated_ai_fail_stops_after_two_revisions(self) -> None:
        def handler(request: ModelRequest, model: str, call: int) -> dict[str, Any]:
            payload = json.loads(request.input_text)
            if request.schema_name == "ai_content_review":
                return fail_review()
            goal = payload.get("goal") or payload.get("original_goal")
            attempt = int(payload.get("revision_attempt", 0))
            return content_artifact(goal, payload["platform"], "持续失败测试", attempt)

        result = self.runtime(FakeProvider(handler)).start("一个会被连续打回的主题")
        state = read_json(Path(result["task_dir"]) / "state.json")

        self.assertEqual(result["status"], "needs_human_review")
        self.assertEqual(state["revision_counts"]["content"], 2)

    def test_17_three_topics_receive_distinct_model_artifacts(self) -> None:
        angles = {
            "Multi-Agent": "多角色协作靠责任和交接",
            "副业": "副业中断来自反馈周期设计",
            "新能源": "新能源首购先判断补能场景",
        }

        def handler(request: ModelRequest, model: str, call: int) -> dict[str, Any]:
            payload = json.loads(request.input_text)
            goal = payload["goal"]
            angle = next(value for key, value in angles.items() if key in goal)
            return content_artifact(goal, payload["platform"], angle)

        provider = FakeProvider(handler)
        agent = ModelBackedContentAgent(
            ProjectPaths.discover(root=ROOT, workspace=self.workspace),
            provider,
            "fake-content",
        )
        goals = [
            "我要做一条介绍 Multi-Agent 工作方式的60秒短视频。",
            "为什么很多人做副业总是坚持不到一个月？",
            "普通人第一次买新能源汽车应该先看什么？",
        ]
        artifacts = []
        for index, goal in enumerate(goals):
            task_dir = self.workspace / f"task_fixture_{index}"
            (task_dir / "logs").mkdir(parents=True)
            artifacts.append(
                agent.topic_to_script(
                    goal,
                    "douyin",
                    task_id=f"task_fixture_{index}",
                    task_dir=task_dir,
                )
            )

        self.assertEqual(len({item["selected_topic"] for item in artifacts}), 3)
        self.assertEqual(len({item["title"] for item in artifacts}), 3)
        self.assertEqual(len({item["script"] for item in artifacts}), 3)

    def test_18_execution_mode_and_usage_are_recorded(self) -> None:
        model_result = self.runtime(FakeProvider(normal_handler)).start("一个模型任务")
        model_logs = [
            read_json(path)
            for path in Path(model_result["task_dir"]).joinpath("logs").glob("model_call_*.json")
        ]
        self.assertEqual({item["execution_mode"] for item in model_logs}, {"api"})
        self.assertTrue(any(item["token_usage"].get("total_tokens") == 360 for item in model_logs))

        deterministic_workspace = Path(self.temporary.name) / "deterministic"
        deterministic = ManagerRuntime(
            root=ROOT,
            workspace=deterministic_workspace,
            execution_mode="deterministic",
        ).start("一个离线任务")
        deterministic_logs = [
            read_json(path)
            for path in Path(deterministic["task_dir"]).joinpath("logs").glob("model_call_*.json")
        ]
        self.assertEqual(
            {item["execution_mode"] for item in deterministic_logs}, {"deterministic"}
        )

    def test_19_deterministic_hard_gate_overrides_ai_pass(self) -> None:
        def handler(request: ModelRequest, model: str, call: int) -> dict[str, Any]:
            payload = json.loads(request.input_text)
            if request.schema_name == "ai_content_review":
                return pass_review()
            goal = payload.get("goal") or payload.get("original_goal")
            attempt = int(payload.get("revision_attempt", 0))
            artifact = content_artifact(
                goal, payload["platform"], "硬规则融合测试", attempt
            )
            artifact["script"] += " 这个方法百分之百有效。"
            return artifact

        result = self.runtime(FakeProvider(handler)).start("测试确定性硬规则")
        first_review = read_json(
            Path(result["task_dir"]) / "reviews" / "review_v1.json"
        )

        self.assertEqual(first_review["review_status"], "FAIL")
        self.assertEqual(first_review["review_layers"]["deterministic_gates"], "FAIL")
        self.assertEqual(first_review["review_layers"]["ai_review"], "PASS")

    def test_20_openai_provider_builds_structured_responses_request(self) -> None:
        captured: dict[str, Any] = {}

        class FakeHTTPResponse:
            def __enter__(self) -> "FakeHTTPResponse":
                return self

            def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps(
                    {
                        "id": "response_fixture",
                        "model": "configured-model",
                        "output": [
                            {
                                "type": "message",
                                "content": [{"type": "output_text", "text": "{}"}],
                            }
                        ],
                        "usage": {"total_tokens": 12},
                    }
                ).encode("utf-8")

        def fake_urlopen(request: Any, timeout: float) -> FakeHTTPResponse:
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeHTTPResponse()

        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "fixture-secret",
                "OPENAI_BASE_URL": "https://example.invalid/v1",
            },
            clear=False,
        ), patch("src.models.openai_provider.urllib.request.urlopen", fake_urlopen):
            provider = OpenAIProvider()
            response = provider.generate(
                ModelRequest(
                    instructions="fixture",
                    input_text="fixture",
                    schema_name="fixture_schema",
                    schema={
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": False,
                    },
                ),
                "configured-model",
            )

        self.assertEqual(response.output_text, "{}")
        self.assertEqual(captured["payload"]["text"]["format"]["type"], "json_schema")
        self.assertTrue(captured["payload"]["text"]["format"]["strict"])
        self.assertNotIn("$schema", captured["payload"]["text"]["format"]["schema"])
        self.assertFalse(captured["payload"]["store"])

    def test_21_schema_invalid_json_retries_and_never_writes_handoff(self) -> None:
        provider = FakeProvider(lambda request, model, call: {"goal": "incomplete"})
        result = self.runtime(provider).start("结构不完整的模型输出")

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["capability"]["status"], "model_output_invalid")
        self.assertEqual(len(provider.calls), 2)
        self.assertFalse(
            (Path(result["task_dir"]) / "handoffs" / "content_to_review.json").exists()
        )


if __name__ == "__main__":
    unittest.main()
