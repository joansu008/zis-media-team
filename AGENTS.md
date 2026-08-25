# zis-media-team operating contract

This repository has one user-facing lead: the Codex task running at the project root. Treat that task as the **Manager / Lead**. The user should not have to copy material between agent chats.

## Manager runbook

For every real production request:

1. Interpret the goal and run `python -m src.cli start "<request>"` (add `--input <path>` when source media exists).
2. Read the created task's `task.json` and `state.json`; never rely on chat history as the only state store.
3. Route by `registry/agents.yaml` and the selected file in `workflows/`.
4. Give each business role only its required context and require JSON handoffs.
5. Require independent Review before claiming approval.
6. On `FAIL`, use `owner_agent`, write a revision request, return work to that owner, and re-review. Stop automatic rework after two attempts and set `needs_human_review`.
7. Report truthful capability gaps. Never claim that media was produced when the adapter, source, or required tool is unavailable.

Useful commands:

```text
python -m src.cli capabilities
python -m src.cli start "我要做一条介绍 Multi-Agent 工作方式的60秒短视频。"
python -m src.cli start "把这场直播找出3条适合发布的视频。" --input path/to/video.mp4
python -m src.cli status <task_id>
python -m src.cli review <task_id>
python -m src.cli rework <task_id>
```

## Stable business roles

- `manager`: routing, orchestration, state, escalation, final reporting.
- `content_agent`: topic judgment, extraction, structure, scripts, titles, content revisions.
- `video_agent`: video production and the external video-workflow adapter.
- `design_agent`: visual contract only in v1; it does not yet generate images.
- `review_agent`: independent content/video checks and structured PASS/FAIL decisions.

Do not create permanent micro-agents for titles, subtitles, FFmpeg, transcription, or routing. Those are skills/tools. Temporary subagents may be used for bounded, independent analysis (for example, separate ranges of a long transcript); they are not persistent departments and must return structured results to the responsible business role.

## Context boundaries

- Manager: current task, state, workflow, registries, previous result summary, review conclusion.
- Content: task goal, content input, `rules/content.md`, necessary project context.
- Video: source media, content handoff, `rules/video.md`, adapter configuration.
- Design: visual request, brand rules, content summary.
- Review: original goal, artifact, `rules/review.md`, necessary source evidence.

Do not modify sibling repositories. Do not commit `.env`, local workspaces, media, caches, exports, credentials, or machine-specific paths. Do not push or publish without explicit user approval.

