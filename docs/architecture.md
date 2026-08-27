# Architecture

## Runtime shape

```text
User (one Codex task)
          |
          v
Codex Lead ---- explicit Router ---- task.json + state.json (Python)
          |
          +--> Content Subagent -- JSON/schema -- hard gates --+
          +--> Video Agent --- video handoff -------+--> Review Agent
          +--> Design Agent (v1 contract only) -----+       |
                    ^                                       |
                    +------ owner-specific revision --------+
```

Business roles own decisions and outcomes. Skills own repeatable procedures; tools perform fixed actions. This is why title writing, subtitles, FFmpeg, transcription, and routing are not permanent agents.

## Why no agent framework

The requirements are met with Codex plus a small standard-library runtime. A framework would duplicate the existing Manager/State/Handoff controls. The file-first runtime keeps each transition inspectable. Native mode uses the signed-in Codex Lead/subagent session and no API key; API mode still uses the replaceable Phase 2 provider; deterministic mode remains an explicit offline fixture only.

Codex native mode coordinates temporary, isolated subagents and returns their structured results to the active Lead task. Stable Content/Video/Design/Review roles remain Registry entries; temporary identifiers are execution provenance only. The runtime does not attempt to turn a ChatGPT/Codex subscription into an HTTP provider.

## State and isolation

Each task owns `task.json`, `state.json`, and separate `inputs/`, `outputs/`, `handoffs/`, `reviews/`, and `logs/` directories. State transitions are validated in code and appended to history. JSON writes use same-directory atomic replacement.

Manager reads only task control data. Specialists receive the input, rule file, handoff, and minimal evidence necessary for their responsibility. Task production workspaces are deliberately local and Git-ignored.

Content Agent receives the task goal, platform, its role definition, content rules and necessary task context. AI Reviewer receives the original task, finished artifact and review rules. It does not receive producer hidden reasoning. The model never writes task state directly.

## Revision policy

A Review FAIL names `owner_agent` and produces `revision_request_vN.json`. The Manager returns it to that owner, then requires a new review. After two automatic revisions at the same stage, the next FAIL becomes `needs_human_review`.

Content review PASS requires both deterministic gates and the independent editorial decision to pass. Native submission failures remain at the current state for truthful retry/diagnosis; API provider failures stop with explicit capability metadata. Neither is converted into a fabricated PASS/FAIL judgment.
