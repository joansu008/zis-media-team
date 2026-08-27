# Model-backed Content and Review

## Execution modes

- `codex_native` (default): the signed-in Codex Lead creates isolated Content and Review subagent executions. Python never calls a subscription or provider; it validates and persists the returned JSON.
- `api`: the Phase 2 `ModelProvider` path below calls the configured provider and model names.
- `deterministic`: an explicit offline fixture/fallback for tests. It is never selected silently.

Native state flow is `start -> next -> submit-content -> next -> submit-review`. Each submission includes the real temporary subagent identifier and timestamps. Native token usage is omitted unless Codex can report it reliably.

## Provider boundary

Business agents depend on `ModelProvider`, not OpenAI directly. `src/models/openai_provider.py` is the first provider implementation; future providers can implement the same `capability()` and `generate()` interface without changing Workflow or State code.

The OpenAI implementation uses the Responses API with strict JSON Schema Structured Outputs, following the official [Responses reference](https://developers.openai.com/api/reference/cli/resources/responses/methods/create) and [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs). The provider sends the broadly supported structural subset; the runtime then applies the complete local constraints before writing a handoff. It uses the standard library HTTP client, so Phase 2 adds no package dependency.

## Content call

```text
Manager
  -> ModelBackedContentAgent
  -> agents/content.md + rules/content.md + task goal/platform/context
  -> ModelProvider
  -> JSON parse
  -> content-artifact schema validation
  -> existing content handoff
```

Revision sends only the original goal, previous artifact, review issues, required action and revision attempt. The returned object is complete and records `revision_attempt` and `addressed_issues`.

## Review call

```text
content handoff
  -> deterministic hard gates
  -> AIReviewAgent(original task + artifact + review rules)
  -> AI review JSON/schema validation
  -> fusion (both layers must pass)
  -> existing review record
```

Hard gates own required fields, minimum script substance, unsupported absolutes, media existence, timeline and subtitle checks. AI review owns clarity, hook, specificity, information density, logic, real title fit, actionable handles, clichés, goal fit and production worthiness.

## Failure and provenance

In API mode, missing configuration, provider errors, invalid JSON and schema-invalid model output are explicit failures. One retry is the default and is configurable. There is no automatic deterministic fallback.

Every attempt creates a small JSON record under the local task `logs/` directory containing task/agent/provider/model/mode/timestamp/success/latency/usage/retry/error code. Prompts, artifacts and credentials are not copied into those call records.
