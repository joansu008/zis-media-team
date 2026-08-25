# Workflows

## `topic_to_script`

1. Manager creates the task and records the explicit route.
2. Content Agent produces topic, summary, structure, spoken script, title, post copy, constraints, and production requirements.
3. Review Agent independently evaluates it and writes `review_vN.json`.
4. FAIL creates an owner-specific revision request and re-enters Content; PASS becomes `approved` and then `awaiting_video` because no source video was supplied.

The v1 deterministic script is a working baseline, not a claim that template text replaces editorial judgment. In normal Codex use, the Content role can refine the structured payload before review.

## `long_video_to_clips`

1. Missing source media becomes `awaiting_video`.
2. A real source with missing adapter capability becomes `needs_human_review` with configuration guidance.
3. When explicitly configured, the Video Agent passes the source and `content_to_video.json` through the external adapter.
4. The adapter must produce a real video manifest. Review checks output existence, timeline order/duplicates, and subtitle requirements.
5. Review PASS completes the workflow; FAIL names the responsible Agent.

Long-video semantic analysis remains unavailable on this machine until the external workflow or a transcript is configured. The runtime does not fabricate candidates or exports.

