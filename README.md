# zis-media-team

A file-first, cross-platform AI media team operated from one Codex Manager conversation. Phase 2.5 makes signed-in Codex native subagents the default execution path while retaining the Phase 2 provider API and offline baseline:

```text
User -> Manager -> Content / Video / Design -> Review
                     ^                         |
                     +------ revision --------+
```

The repository intentionally avoids an orchestration framework. Python owns routing, state, schemas, handoffs, hard gates, review fusion, and revision limits. In `codex_native`, the Codex Lead dispatches isolated Content and Review subagents and submits their JSON results back to Python.

## Quick start

Python 3.9+ is sufficient; the runtime has no third-party dependencies. Native mode needs no API credential:

```text
ZIS_EXECUTION_MODE=codex_native
```

```bash
python3 -m src.cli capabilities
python3 -m src.cli start "我要做一条介绍 Multi-Agent 工作方式的60秒短视频。"
python3 -m src.cli status <task_id>
python3 -m unittest discover -s tests -v
```

If you explicitly want the offline fixture/fallback, label it at invocation time:

```bash
python3 -m src.cli --execution-mode deterministic start "离线测试主题"
```

The deterministic mode is never silently selected and is recorded in task logs.

For a long-video request:

```bash
python -m src.cli start "把这场直播找出3条适合发布的视频。" --input path/to/video.mp4
```

Copy `.env.example` to `.env` or set equivalent environment variables in your shell. A small built-in loader reads simple `KEY=VALUE` lines without overriding existing shell values. `.env` and task logs are local and ignored by Git.

For explicit Phase 2 API execution, configure `ZIS_MODEL_PROVIDER`, `ZIS_CONTENT_MODEL`, `ZIS_REVIEW_MODEL`, and the provider credential, then select `--execution-mode api`.

## What Phase 2.5 does

- Creates `workspace/task_<timestamp>_<suffix>/` with task, state, inputs, outputs, handoffs, reviews, and logs.
- Routes topic/script and long-video intents using explicit rules.
- Returns a state-authorized native `next_action` instead of asking Python to call the signed-in Codex session.
- Accepts schema-bound Content and Review JSON from separate temporary subagents.
- Runs deterministic gates before Review and fuses those gates with independent semantic Review.
- Creates owner-specific revision requests and caps automatic revisions at two.
- Records native role/subagent provenance and API provider usage separately without inventing native token usage.
- Detects OS, Python, Git, FFmpeg, and the external video workflow without pretending missing capabilities exist.
- Defines—but does not yet implement—Design production.

Task workspaces are local and ignored by Git. See `docs/architecture.md`, `docs/model-agents.md`, `docs/workflows.md`, and `docs/cross-platform.md`.
