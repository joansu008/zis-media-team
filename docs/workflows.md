# Workflows

## `topic_to_script`

1. Manager creates the task and records the explicit route.
2. In the default native mode, Python returns a Content `next_action`; the Codex Lead dispatches a bounded Content subagent and submits its strict JSON.
3. The runtime validates the Content schema, persists the handoff, and runs deterministic gates before returning a separate Review `next_action`.
4. An isolated Review subagent reads only the original goal, artifact, Review role/rules and schema. Python validates and fuses its decision into `review_vN.json`.
5. FAIL creates an owner-specific revision request and a state-driven Content revision action. The revised artifact is gated and independently reviewed again. PASS becomes `approved` and then `awaiting_video`.

Native JSON/schema failures are rejected without a handoff or hidden fallback. API provider/credential failures stop truthfully. The deterministic content service runs only through explicit offline mode and records `execution_mode=deterministic`.

## `long_video_to_clips`

1. Missing source media becomes `awaiting_video`.
2. A real source with missing adapter capability becomes `needs_human_review` with configuration guidance.
3. When explicitly configured, the Video Agent passes the source and `content_to_video.json` through the external adapter.
4. The adapter must produce a real video manifest. Review checks output existence, timeline order/duplicates, and subtitle requirements.
5. Review PASS completes the workflow; FAIL names the responsible Agent.

Long-video semantic analysis remains unavailable on this machine until the external workflow or a transcript is configured. The runtime does not fabricate candidates or exports.
