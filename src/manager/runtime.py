from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.adapters.zis_video_workflow import ZisVideoWorkflowAdapter
from src.capabilities import detect_capabilities
from src.config import ProjectPaths
from src.content.service import ContentService
from src.handoff.writer import write_handoff
from src.io import read_json, utc_now, write_json
from src.registry import Registry
from src.review.engine import ReviewEngine
from src.routing.router import WorkflowRouter
from src.state.store import TaskStore


class ManagerRuntime:
    MAX_AUTOMATIC_REVISIONS = 2

    def __init__(
        self,
        root: Path | None = None,
        workspace: Path | None = None,
    ) -> None:
        self.paths = ProjectPaths.discover(root=root, workspace=workspace)
        self.store = TaskStore(self.paths)
        self.router = WorkflowRouter()
        self.content = ContentService()
        self.reviewer = ReviewEngine()
        self.registry = Registry(
            self.paths.agents_registry, self.paths.skills_registry
        )
        self.video_adapter = ZisVideoWorkflowAdapter(self.paths)

    def start(
        self,
        request: str,
        input_path: str | None = None,
        platform: str = "unspecified",
    ) -> dict[str, Any]:
        if not request.strip():
            raise ValueError("request must not be empty")
        route = self.router.route(request, input_path)
        self.registry.workflow(self.paths.workflow(route.workflow_id))
        self.registry.agent("manager")
        inputs: dict[str, Any] = {"source_media": input_path}
        task_id, task_dir = self.store.create(
            request, route.workflow_id, platform, inputs, route.as_dict()
        )
        self.store.transition(
            task_id, "analyzing", "routing", route.reason, f"Selected {route.workflow_id}"
        )
        if route.workflow_id == "topic_to_script":
            return self._run_topic_to_script(task_id)
        return self._run_long_video(task_id, input_path)

    def _run_topic_to_script(self, task_id: str) -> dict[str, Any]:
        task = self.store.task(task_id)
        task_dir = self.paths.task_dir(task_id)
        self.registry.agent("content_agent")
        self.registry.skill("topic-to-script")
        self.store.transition(
            task_id,
            "content_processing",
            "content",
            "delegated to content_agent",
            "Content Agent is building the script package",
        )
        payload = self.content.topic_to_script(task["request"], task["platform"])
        _, handoff = write_handoff(
            task_dir,
            "content_to_review.json",
            task_id,
            "content_agent",
            "review_agent",
            "content_package",
            payload,
        )
        write_json(task_dir / "outputs" / "content_package_v1.json", payload)
        review = self._review_content_handoff(task_id, handoff)

        while review["review_status"] == "FAIL":
            if self.store.state(task_id)["status"] != "revision_required":
                break
            self._rework_content(task_id, review)
            latest = read_json(task_dir / "handoffs" / "content_to_review.json")
            review = self._review_content_handoff(task_id, latest)
        return self.summary(task_id, last_review=review)

    def _run_long_video(
        self, task_id: str, input_path: str | None
    ) -> dict[str, Any]:
        task = self.store.task(task_id)
        task_dir = self.paths.task_dir(task_id)
        if not input_path:
            self.store.transition(
                task_id,
                "awaiting_video",
                "source_input",
                "long-video workflow requires source media",
                "Waiting for source video",
            )
            return self.summary(task_id)

        source = Path(input_path).expanduser()
        if not source.is_absolute():
            source = (self.paths.root / source).resolve()
        if not source.is_file():
            self.store.transition(
                task_id,
                "awaiting_video",
                "source_input",
                "provided source path does not exist",
                "Waiting for a valid source video path",
            )
            return self.summary(task_id)

        probe = self.video_adapter.probe()
        if probe.status != "available":
            self.store.transition(
                task_id,
                "needs_human_review",
                "video_adapter",
                probe.reason,
                probe.required_action,
            )
            return self.summary(task_id, capability=probe.as_dict())

        count_match = re.search(r"(\d+)\s*条", task["request"])
        candidates = int(count_match.group(1)) if count_match else 3
        content_payload = {
            "goal": task["request"],
            "platform": task["platform"],
            "selected_topic": "由外部工作流从长视频中识别候选内容",
            "content_summary": "长视频分析和候选片段选择请求；具体观点必须保留来源时间范围。",
            "script": "",
            "title": "",
            "source_range": None,
            "constraints": ["不得虚构来源时间范围", "不得修改外部项目"],
            "production_requirements": {
                "candidate_count": candidates,
                "source_media": str(source),
            },
        }
        handoff_path, _ = write_handoff(
            task_dir,
            "content_to_video.json",
            task_id,
            "content_agent",
            "video_agent",
            "long_video_analysis_request",
            content_payload,
        )
        self.store.transition(
            task_id,
            "video_processing",
            "video",
            "external workflow is configured",
            "Video Agent invoked the configured adapter",
        )
        result = self.video_adapter.run(source, task_dir, handoff_path)
        if result.get("status") != "available":
            self.store.transition(
                task_id,
                "failed",
                "video_adapter",
                "configured external command failed",
                result.get("required_action", "Inspect adapter logs"),
            )
            write_json(task_dir / "logs" / "video_adapter_failure.json", result)
            return self.summary(task_id, capability=result)

        _, video_handoff = write_handoff(
            task_dir,
            "video_to_review.json",
            task_id,
            "video_agent",
            "review_agent",
            "video_package",
            result,
        )
        review = self._review_video_handoff(task_id, video_handoff)
        while review["review_status"] == "FAIL":
            if self.store.state(task_id)["status"] != "revision_required":
                break
            next_review = self._rework_video(task_id)
            if next_review.get("review_status") not in {"PASS", "FAIL"}:
                break
            review = next_review
        return self.summary(task_id, last_review=review)

    def _next_review_version(self, task_id: str) -> int:
        reviews_dir = self.paths.task_dir(task_id) / "reviews"
        return len(list(reviews_dir.glob("review_v*.json"))) + 1

    def _review_content_handoff(
        self, task_id: str, handoff: dict[str, Any]
    ) -> dict[str, Any]:
        state = self.store.state(task_id)
        if state["status"] != "reviewing":
            self.store.transition(
                task_id,
                "reviewing",
                "content_review",
                "artifact handed to independent review_agent",
                "Review Agent is checking the content package",
            )
        version = self._next_review_version(task_id)
        review = self.reviewer.review_content(
            self.store.task(task_id), handoff["payload"], version
        )
        write_json(
            self.paths.task_dir(task_id) / "reviews" / f"review_v{version}.json",
            review,
        )
        self._apply_review(task_id, review, "content")
        return review

    def _review_video_handoff(
        self, task_id: str, handoff: dict[str, Any]
    ) -> dict[str, Any]:
        self.store.transition(
            task_id,
            "reviewing",
            "video_review",
            "video handed to independent review_agent",
            "Review Agent is checking the video package",
        )
        version = self._next_review_version(task_id)
        review = self.reviewer.review_video(
            self.store.task(task_id),
            handoff["payload"],
            self.paths.task_dir(task_id),
            version,
        )
        write_json(
            self.paths.task_dir(task_id) / "reviews" / f"review_v{version}.json",
            review,
        )
        self._apply_review(task_id, review, "video")
        return review

    def _apply_review(
        self, task_id: str, review: dict[str, Any], stage: str
    ) -> None:
        if review["review_status"] == "PASS":
            self.store.transition(
                task_id,
                "approved",
                f"{stage}_approved",
                f"review_v{review['review_version']} passed",
                f"{stage.title()} artifact passed independent review",
            )
            workflow_id = self.store.task(task_id)["workflow_id"]
            terminal = "awaiting_video" if workflow_id == "topic_to_script" else "completed"
            summary = (
                "Approved script package; waiting for source video"
                if terminal == "awaiting_video"
                else "Approved deliverables completed"
            )
            self.store.transition(task_id, terminal, terminal, "workflow pass route", summary)
            return

        state = self.store.state(task_id)
        used = int(state["revision_counts"].get(stage, 0))
        if used >= self.MAX_AUTOMATIC_REVISIONS:
            self.store.transition(
                task_id,
                "needs_human_review",
                stage,
                "automatic revision limit reached",
                "Two automatic revisions failed; human direction is required",
            )
            return
        attempt = self.store.increment_revision(task_id, stage)
        revision_request = {
            "task_id": task_id,
            "review_version": review["review_version"],
            "revision_attempt": attempt,
            "stage": stage,
            "owner_agent": review["owner_agent"],
            "issues": review["issues"],
            "required_action": review["required_action"],
            "need_re_review": True,
            "created_at": utc_now(),
        }
        write_json(
            self.paths.task_dir(task_id)
            / "reviews"
            / f"revision_request_v{attempt}.json",
            revision_request,
        )
        self.store.transition(
            task_id,
            "revision_required",
            stage,
            f"review assigned revision to {review['owner_agent']}",
            f"Revision attempt {attempt} assigned to {review['owner_agent']}",
        )

    def _rework_content(
        self, task_id: str, failed_review: dict[str, Any]
    ) -> dict[str, Any]:
        task = self.store.task(task_id)
        task_dir = self.paths.task_dir(task_id)
        current = read_json(task_dir / "handoffs" / "content_to_review.json")
        attempt = self.store.state(task_id)["revision_counts"]["content"]
        self.store.transition(
            task_id,
            "content_processing",
            "content_revision",
            f"content_agent is applying revision attempt {attempt}",
            "Content Agent is applying the Review issues",
        )
        payload = self.content.revise(
            task["request"], task["platform"], current["payload"], failed_review["issues"]
        )
        _, handoff = write_handoff(
            task_dir,
            "content_to_review.json",
            task_id,
            "content_agent",
            "review_agent",
            "content_package",
            payload,
        )
        write_json(
            task_dir / "outputs" / f"content_package_v{attempt + 1}.json", payload
        )
        return handoff

    def _rework_video(self, task_id: str) -> dict[str, Any]:
        task = self.store.task(task_id)
        task_dir = self.paths.task_dir(task_id)
        source_value = task.get("inputs", {}).get("source_media")
        if not source_value:
            self.store.transition(
                task_id,
                "needs_human_review",
                "video",
                "video revision has no source media",
                "Provide the original source media before video revision",
            )
            return {"status": "capability_unavailable", "review_status": "unavailable"}
        source = Path(str(source_value)).expanduser()
        if not source.is_absolute():
            source = (self.paths.root / source).resolve()
        attempt = self.store.state(task_id)["revision_counts"]["video"]
        revision_path = task_dir / "reviews" / f"revision_request_v{attempt}.json"
        handoff_path = task_dir / "handoffs" / "content_to_video.json"
        self.store.transition(
            task_id,
            "video_processing",
            "video_revision",
            f"video_agent is applying revision attempt {attempt}",
            "Video Agent re-invoked the adapter with the Review issues",
        )
        result = self.video_adapter.run(
            source, task_dir, handoff_path, revision_request=revision_path
        )
        if result.get("status") != "available":
            self.store.transition(
                task_id,
                "needs_human_review",
                "video_adapter",
                "video revision adapter call failed or became unavailable",
                result.get("required_action", "Inspect the external video workflow"),
            )
            write_json(
                task_dir / "logs" / f"video_revision_failure_v{attempt}.json", result
            )
            return result
        _, handoff = write_handoff(
            task_dir,
            "video_to_review.json",
            task_id,
            "video_agent",
            "review_agent",
            "video_package",
            result,
        )
        return self._review_video_handoff(task_id, handoff)

    def review_task(self, task_id: str) -> dict[str, Any]:
        task = self.store.task(task_id)
        task_dir = self.paths.task_dir(task_id)
        if task["workflow_id"] == "topic_to_script":
            handoff = read_json(task_dir / "handoffs" / "content_to_review.json")
            return self._review_content_handoff(task_id, handoff)
        handoff = read_json(task_dir / "handoffs" / "video_to_review.json")
        return self._review_video_handoff(task_id, handoff)

    def rework(self, task_id: str) -> dict[str, Any]:
        state = self.store.state(task_id)
        if state["status"] != "revision_required":
            raise ValueError(f"Task is not awaiting revision: {state['status']}")
        task_dir = self.paths.task_dir(task_id)
        reviews = sorted(task_dir.joinpath("reviews").glob("review_v*.json"))
        failed_review = read_json(reviews[-1])
        if failed_review["owner_agent"] == "content_agent":
            handoff = self._rework_content(task_id, failed_review)
            return self._review_content_handoff(task_id, handoff)
        if failed_review["owner_agent"] == "video_agent":
            return self._rework_video(task_id)
        raise NotImplementedError(
            f"No automatic revision executor for {failed_review['owner_agent']}"
        )

    def summary(
        self,
        task_id: str,
        last_review: dict[str, Any] | None = None,
        capability: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        state = self.store.state(task_id)
        result: dict[str, Any] = {
            "task_id": task_id,
            "workflow_id": self.store.task(task_id)["workflow_id"],
            "status": state["status"],
            "current_stage": state["current_stage"],
            "summary": state["last_summary"],
            "task_dir": str(self.paths.task_dir(task_id)),
        }
        if last_review is not None:
            result["review"] = last_review
        if capability is not None:
            result["capability"] = capability
        return result

    def capabilities(self) -> dict[str, Any]:
        return detect_capabilities(self.paths)
