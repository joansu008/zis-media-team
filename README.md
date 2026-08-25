# zis-media-team

A file-first, cross-platform AI media team operated from one Codex Manager conversation. Version 1 focuses on one inspectable loop:

```text
User -> Manager -> Content / Video / Design -> Review
                     ^                         |
                     +------ revision --------+
```

The repository intentionally avoids a multi-agent framework. Codex supplies judgment and can delegate bounded analysis; the Python runtime supplies deterministic routing, task workspaces, state transitions, handoffs, review records, capability checks, and revision limits.

## Quick start

Python 3.9+ is sufficient; v1 has no third-party runtime dependencies.

```bash
python -m src.cli capabilities
python -m src.cli start "我要做一条介绍 Multi-Agent 工作方式的60秒短视频。"
python -m src.cli status <task_id>
python -m unittest discover -s tests -v
```

For a long-video request:

```bash
python -m src.cli start "把这场直播找出3条适合发布的视频。" --input path/to/video.mp4
```

Copy `.env.example` to `.env` or set equivalent environment variables in your shell. A small built-in loader reads simple `KEY=VALUE` lines from `.env` without overriding existing shell values. Configure `ZIS_VIDEO_WORKFLOW_PATH` and `ZIS_VIDEO_WORKFLOW_COMMAND` on each machine that has the external workflow.

## What v1 does

- Creates `workspace/task_<timestamp>_<suffix>/` with task, state, inputs, outputs, handoffs, reviews, and logs.
- Routes topic/script and long-video intents using explicit rules.
- Produces a usable first-pass short-video script package for topic requests.
- Independently reviews content and records PASS/FAIL JSON.
- Creates owner-specific revision requests and caps automatic revisions at two.
- Detects OS, Python, Git, FFmpeg, and the external video workflow without pretending missing capabilities exist.
- Defines—but does not yet implement—Design production.

Task workspaces are local and ignored by Git. See `docs/architecture.md`, `docs/workflows.md`, and `docs/cross-platform.md`.
