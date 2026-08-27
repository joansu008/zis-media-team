from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.adapters.zis_video_workflow import ZisVideoWorkflowAdapter
from src.config import ProjectPaths
from src.content.service import ContentService
from src.io import read_json, write_json
from src.manager.runtime import ManagerRuntime
from src.review.engine import ReviewEngine


ROOT = Path(__file__).resolve().parents[1]


class RuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name) / "workspace"
        self.runtime = ManagerRuntime(
            root=ROOT, workspace=self.workspace, execution_mode="deterministic"
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_01_topic_to_script_closes_content_review_loop(self) -> None:
        result = self.runtime.start(
            "我要做一条介绍 Multi-Agent 工作方式的60秒短视频。",
            platform="douyin",
        )
        task_dir = Path(result["task_dir"])
        state = read_json(task_dir / "state.json")
        review = read_json(task_dir / "reviews" / "review_v1.json")

        self.assertEqual(result["workflow_id"], "topic_to_script")
        self.assertEqual(state["status"], "awaiting_video")
        self.assertEqual(review["review_status"], "PASS")
        self.assertTrue((task_dir / "handoffs" / "content_to_review.json").is_file())
        self.assertIn("content_processing", [item["to"] for item in state["history"]])
        self.assertIn("reviewing", [item["to"] for item in state["history"]])

    def test_02_failed_review_creates_owner_revision_request(self) -> None:
        result = self.runtime.start("做一条关于 Multi-Agent 的短视频")
        task_dir = Path(result["task_dir"])
        handoff_path = task_dir / "handoffs" / "content_to_review.json"
        handoff = read_json(handoff_path)
        handoff["payload"] = {
            "selected_topic": "Multi-Agent",
            "title": "无关标题",
            "script": "太短",
            "content_summary": "",
        }
        write_json(handoff_path, handoff)

        review = self.runtime.review_task(result["task_id"])
        state = read_json(task_dir / "state.json")
        revision = read_json(task_dir / "reviews" / "revision_request_v1.json")

        self.assertEqual(review["review_status"], "FAIL")
        self.assertEqual(review["owner_agent"], "content_agent")
        self.assertEqual(state["status"], "revision_required")
        self.assertEqual(revision["owner_agent"], "content_agent")
        self.assertTrue(revision["need_re_review"])

    def test_03_assigned_content_rework_is_re_reviewed(self) -> None:
        result = self.runtime.start("做一条关于 Multi-Agent 的短视频")
        task_dir = Path(result["task_dir"])
        handoff_path = task_dir / "handoffs" / "content_to_review.json"
        handoff = read_json(handoff_path)
        handoff["payload"] = {"title": "", "script": "", "selected_topic": ""}
        write_json(handoff_path, handoff)
        self.runtime.review_task(result["task_id"])

        review = self.runtime.rework(result["task_id"])
        state = read_json(task_dir / "state.json")
        self.assertEqual(review["review_status"], "PASS")
        self.assertEqual(state["status"], "awaiting_video")
        self.assertEqual(state["revision_counts"]["content"], 1)

    def test_04_core_runtime_has_no_machine_specific_absolute_paths(self) -> None:
        mac_pattern = re.compile(r"/Users/[^/]+/")
        windows_pattern = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/]")
        violations = []
        for path in (ROOT / "src").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if mac_pattern.search(text) or windows_pattern.search(text):
                violations.append(str(path.relative_to(ROOT)))
        self.assertEqual(violations, [])

        paths = ProjectPaths.discover(root=ROOT, workspace=Path("local-work"))
        self.assertEqual(paths.workspace, (ROOT / "local-work").resolve())

    def test_05_video_adapter_reports_capability_unavailable(self) -> None:
        missing = Path(self.temporary.name) / "not-installed"
        with patch.dict(
            os.environ,
            {
                "ZIS_VIDEO_WORKFLOW_PATH": str(missing),
                "ZIS_VIDEO_WORKFLOW_COMMAND": "",
            },
            clear=False,
        ):
            adapter = ZisVideoWorkflowAdapter(
                ProjectPaths.discover(root=ROOT, workspace=self.workspace)
            )
            probe = adapter.probe()
        self.assertEqual(probe.status, "capability_unavailable")
        self.assertFalse(probe.root_found)
        self.assertTrue(probe.can_continue_without_video)

    def test_06_long_video_without_source_waits_truthfully(self) -> None:
        result = self.runtime.start("把这场直播找出3条适合发布的视频")
        self.assertEqual(result["workflow_id"], "long_video_to_clips")
        self.assertEqual(result["status"], "awaiting_video")

    def test_07_video_review_rejects_missing_file_and_bad_timeline(self) -> None:
        task = {
            "task_id": "task_test",
            "request": "cut a clip",
            "workflow_id": "long_video_to_clips",
        }
        review = ReviewEngine().review_video(
            task,
            {
                "output_file": "outputs/missing.mp4",
                "timeline": [{"start": 10, "end": 5}],
                "subtitles_required": True,
            },
            self.workspace,
            1,
        )
        self.assertEqual(review["review_status"], "FAIL")
        self.assertEqual(review["owner_agent"], "video_agent")
        self.assertGreaterEqual(len(review["issues"]), 3)

    def test_08_registries_workflows_and_schemas_are_valid_json(self) -> None:
        files = list((ROOT / "registry").glob("*.yaml"))
        files += list((ROOT / "workflows").glob("*.yaml"))
        files += list((ROOT / "schemas").glob("*.json"))
        self.assertGreater(len(files), 0)
        for path in files:
            with self.subTest(path=path.name):
                value = json.loads(path.read_text(encoding="utf-8"))
                self.assertIsInstance(value, dict)

    def test_09_automatic_revision_stops_after_two_attempts(self) -> None:
        class AlwaysBadContent(ContentService):
            def topic_to_script(self, request: str, platform: str = "unspecified") -> dict:
                return {
                    "selected_topic": "Multi-Agent",
                    "title": "无关",
                    "script": "太短",
                    "content_summary": "",
                }

            def revise(
                self,
                request: str,
                platform: str,
                previous: dict,
                issues: list,
                required_action: str = "",
                revision_attempt: int = 1,
            ) -> dict:
                return self.topic_to_script(request, platform)

        self.runtime.content = AlwaysBadContent()
        result = self.runtime.start("做一条关于 Multi-Agent 的短视频")
        state = self.runtime.store.state(result["task_id"])
        reviews_dir = Path(result["task_dir"]) / "reviews"

        self.assertEqual(state["status"], "needs_human_review")
        self.assertEqual(state["revision_counts"]["content"], 2)
        self.assertEqual(len(list(reviews_dir.glob("review_v*.json"))), 3)
        self.assertEqual(len(list(reviews_dir.glob("revision_request_v*.json"))), 2)

    def test_10_video_revision_reinvokes_adapter_then_stops(self) -> None:
        class AlwaysBadVideoAdapter:
            def __init__(self) -> None:
                self.calls = 0

            def probe(self) -> SimpleNamespace:
                return SimpleNamespace(status="available")

            def run(
                self,
                source: Path,
                task_dir: Path,
                handoff: Path,
                revision_request: Path | None = None,
            ) -> dict:
                self.calls += 1
                return {
                    "status": "available",
                    "output_file": "outputs/missing.mp4",
                    "timeline": [{"start": 9, "end": 2}],
                    "subtitles_required": True,
                }

        source = Path(self.temporary.name) / "source.mp4"
        source.write_bytes(b"fixture")
        adapter = AlwaysBadVideoAdapter()
        self.runtime.video_adapter = adapter

        result = self.runtime.start(
            "把这场直播找出3条适合发布的视频", input_path=str(source)
        )
        state = self.runtime.store.state(result["task_id"])

        self.assertEqual(result["status"], "needs_human_review")
        self.assertEqual(state["revision_counts"]["video"], 2)
        self.assertEqual(adapter.calls, 3)


if __name__ == "__main__":
    unittest.main()
