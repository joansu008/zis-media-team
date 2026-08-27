# Roadmap

## Implemented through Phase 2

- File-backed Manager, explicit routing, task state, handoffs, content review, video technical checks, capability detection, and bounded content revision.
- Topic-to-script production and honest `awaiting_video` behavior.
- External video adapter contract and non-heavy probe.
- Replaceable Model Provider interface and an OpenAI Responses API provider.
- Strict JSON/schema Content generation and issue-targeted model revision.
- Independent AI content review fused with deterministic hard gates.
- Local model usage/failure logs and truthful unavailable behavior.

## Reserved, not implemented

- Design Agent image production; only role and I/O schemas exist.
- Long-video semantic extraction without the external workflow or transcript.
- The internal repair logic of the sibling workflow; v1 can pass a structured revision request back to its configured CLI and re-review the replacement output.
- Research, Operation, Publisher, Data Analysis, Skill Scout, non-OpenAI providers, analytics, and automatic publishing.
- Cross-computer continuation of a single in-progress task.

## Deferred until Phase 2 acceptance

1. Map the real `zis-video-workflow` CLI into the adapter contract using a thin, tested wrapper.
2. Add transcript ingestion and source-range validation independent of video rendering.
3. Add brand configuration and one reviewed Design skill.
4. Add end-to-end fixtures from real production tasks before introducing any orchestration framework.
