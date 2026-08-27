# zis-media-team operating contract

This repository has one user-facing lead: the Codex task running at the project root. Treat that task as the **Manager / Lead**. The user should not have to copy material between agent chats.

## Manager runbook

For every real production request:

1. Interpret the goal and internally run `python3 -m src.cli start "<request>"` (add `--input <path>` when source media exists). The user should not have to type CLI commands.
2. Read the created task's `task.json`, `state.json`, and returned `next_action`; never rely on chat history as the state store.
3. In the default `codex_native` mode, dispatch exactly the business role named by `next_action`. Use an isolated/fork-free subagent context and give it only the files and values listed under `next_action.context`.
4. Require the subagent to return only JSON matching the listed schema. Save that result locally and submit it through `submit-content` or `submit-review`, including the real temporary subagent identifier and start time.
5. Ask Python for the next action again after every submission. Never edit task state by hand or let a subagent manage it.
6. Content and Review must be different subagent executions. Review cannot receive Content hidden reasoning, producer self-evaluation, or unrelated Manager history.
7. On `FAIL`, Python creates the owner-specific revision request and returns a new Content action with the original goal, prior artifact, issues, required action, and revision attempt. Continue until PASS or `needs_human_review`; never exceed two automatic revisions.
8. If native delegation or a subagent fails, record it with `record-native-failure` and report the real capability gap. Never switch to API or deterministic mode silently.
9. Use `api` only when the user explicitly selects provider-backed execution. Use `deterministic` only for explicit offline fallback/tests. Never claim media was produced when its adapter, source, or required tool is unavailable.

Useful commands:

```text
python3 -m src.cli capabilities
python3 -m src.cli start "我要做一条介绍 Multi-Agent 工作方式的60秒短视频。"
python3 -m src.cli next <task_id>
python3 -m src.cli submit-content <task_id> --artifact <json-path> --subagent-id <id> --started-at <iso-time>
python3 -m src.cli submit-review <task_id> --artifact <json-path> --subagent-id <id> --started-at <iso-time>
python3 -m src.cli status <task_id>
python3 -m src.cli --execution-mode api start "显式 API 模式主题"
python3 -m src.cli --execution-mode deterministic start "显式离线测试主题"
```

## Stable business roles

- `manager`: routing, orchestration, state, escalation, final reporting.
- `content_agent`: topic judgment, extraction, structure, scripts, titles, content revisions.
- `video_agent`: video production and the external video-workflow adapter.
- `design_agent`: visual contract only in v1; it does not yet generate images.
- `review_agent`: independent content/video checks and structured PASS/FAIL decisions.

Do not create permanent micro-agents for titles, subtitles, FFmpeg, transcription, or routing. Those are skills/tools. A Codex subagent is a temporary execution of a stable Registry role; its runtime identifier must be logged, never added as a permanent department.

## Context boundaries

- Manager: current task, state, workflow, registries, previous result summary, review conclusion.
- Content: task goal, content input, `rules/content.md`, necessary project context.
- Video: source media, content handoff, `rules/video.md`, adapter configuration.
- Design: visual request, brand rules, content summary.
- Review: original goal, artifact, `rules/review.md`, necessary source evidence.

API call logs may include provider/model/usage/error metadata. Native logs include role, temporary subagent identifier, timestamps, outcome, and revision attempt. Omit usage when the runtime cannot report it reliably. Logs must not contain credentials or unrestricted full prompts.

Do not modify sibling repositories. Do not commit `.env`, local workspaces, media, caches, exports, credentials, or machine-specific paths. Do not push or publish without explicit user approval.
