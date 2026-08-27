# Content Agent

Owns whether the content works: topic interpretation, long-form extraction, candidate judgment, structure, spoken script, title, basic post copy, and content revisions.

Inputs: current task, content/source input, `rules/content.md`, necessary context only.

Outputs: a structured content handoff conforming to `schemas/handoff.schema.json`. Claims derived from source material should retain source ranges or be marked as needing verification.

In production, creation and revision run through `ModelProvider` and strict JSON Schema validation. Revision context is limited to the original goal, previous artifact, review issues, required action, and revision attempt. The deterministic service is only an explicitly labeled offline fallback.
