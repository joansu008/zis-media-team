# Architecture

## Runtime shape

```text
User (one Codex task)
          |
          v
Manager / Lead -- explicit Router -- task.json + state.json
          |
          +--> Content Agent -- content handoff ----+
          +--> Video Agent --- video handoff -------+--> Review Agent
          +--> Design Agent (v1 contract only) -----+       |
                    ^                                       |
                    +------ owner-specific revision --------+
```

Business roles own decisions and outcomes. Skills own repeatable procedures; tools perform fixed actions. This is why title writing, subtitles, FFmpeg, transcription, and routing are not permanent agents.

## Why no agent framework

The v1 requirements are met with Codex plus a small standard-library runtime. A framework would add dependency, deployment, tracing, and provider configuration before the workflow itself is proven. The file-first runtime keeps each transition inspectable and works without API credentials.

Codex in this environment can coordinate temporary subagents and return their results to the active task. That is useful for independent ranges of a long transcript, but the repository does not require it for correctness. The stable Content/Video/Design/Review roles remain Registry entries regardless of which temporary execution units Codex uses. Official OpenAI documentation describes parallel multi-agent coordination as a supported beta capability of current GPT-5.6/Responses workflows: <https://developers.openai.com/api/docs/guides/latest-model#what-is-new>.

## State and isolation

Each task owns `task.json`, `state.json`, and separate `inputs/`, `outputs/`, `handoffs/`, `reviews/`, and `logs/` directories. State transitions are validated in code and appended to history. JSON writes use same-directory atomic replacement.

Manager reads only task control data. Specialists receive the input, rule file, handoff, and minimal evidence necessary for their responsibility. Task production workspaces are deliberately local and Git-ignored.

## Revision policy

A Review FAIL names `owner_agent` and produces `revision_request_vN.json`. The Manager returns it to that owner, then requires a new review. After two automatic revisions at the same stage, the next FAIL becomes `needs_human_review`.

