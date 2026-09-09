---
name: model-routing-review
description: Reassesses the Pi model-routing profile with independent benchmarks, real task telemetry, current provider pricing, and user-reported failure modes. Use when reviewing the model mix, token spend, Pi subagent roles, GLM, Sol, OpenRouter, or whether to change the cost-aware development setup.
---

# Grounded model-routing review

Review the model allocation before changing `config/settings.json`. Optimize for cost per accepted engineering task while preserving reliability on consequential work.

## Evidence hierarchy

1. **Local evaluation data**: accepted tasks, retries, tests, regressions, wall time, cache use, and human correction time. This decides the change.
2. **Independent, comparable benchmarks**: use as many relevant evaluations as available, up to ten. Prefer tests that cover the exact model/version and relevant agentic coding work. Record benchmark date, methodology, model effort setting, and whether a score is measured or estimated.
3. **Current provider data**: pricing, context/output limits, availability, and structured-output/tool support. Use it for operational facts and cost calculations, never as proof of quality.
4. **User reports**: identify possible failure modes or harness interactions. Label them anecdotal; never average votes or treat them as performance data.
5. **Vendor benchmarks and model cards**: background only. Do not use them as the sole evidence for a capability claim.

If a fact can change, browse for it. Cite the direct page that supports it. Do not conflate a model family, a `latest` alias, a preview, a provider-specific variant, or one reasoning effort with another.

## Before research

Read these files:

- `config/settings.json` for the effective intended profile.
- `config/versions.json` for Pi and extension versions.
- `agents/` for role prompts and their explicit model/thinking fields.
- Existing task telemetry, if available.

Write down the exact decision: for example, “Should `worker` remain GLM high?” or “Should reviewer move from Sol high to another model?” Do not research a vague ranking.

## Gather comparable evidence

For every candidate, collect:

- Exact provider/model identifier, release/version date, reasoning setting, context and output limits.
- Independent composite score and relevant component scores: terminal/coding agent tasks, tool use, instruction following, long-context behavior, and reliability where available.
- Price per million input, output, and cache tokens from the provider actually used by Pi. Record promotional and list prices separately.
- Availability/latency only when it affects the developer workflow.
- At least two recent user reports when there is enough discussion. State the sample bias and disagreements.

Select up to ten independent benchmarks across these dimensions, favoring direct evidence over breadth for its own sake:

1. Terminal or repository-level coding agents.
2. Software engineering issue resolution.
3. Tool use and multi-step automation.
4. Realistic knowledge work or planning.
5. Instruction following and constrained output.
6. Long-context retrieval and reasoning.
7. Hallucination or faithfulness.
8. Debugging and scientific/code reasoning.
9. Security or data-integrity reasoning when the project needs it.
10. A domain-relevant benchmark, when one exists.

For each benchmark, state whether it is independent, its task type, the exact setting
tested, score direction, and why it matters to the role under review. Do not average
unrelated scores into a homemade leaderboard. If fewer than ten valid comparisons exist,
report the smaller set and name the gaps. If a benchmark covers an obsolete model, a
different effort level, or a non-comparable provider variant, exclude it and explain why.

Reject an apparent comparison when settings differ materially or only vendor evidence exists. Mark missing evidence as unknown rather than inferring it.

## Evaluate on this harness

Use 20–30 representative tasks before a permanent change when the candidate could affect the default model or a frontier role. Include small implementation, multi-file feature, debugging, code review, and a task with the project’s highest-risk domain rules.

Keep acceptance criteria, repository revision, tool permissions, task budget, and review method comparable. Randomize task order. Review diffs blind to model identity when practical. Repeat important failures once before assigning cause.

Record per task:

```text
task_id, category, agent_role, model, thinking, provider, prompt/input tokens,
cache-read tokens, output+reasoning tokens, tool calls, attempts, tests passed,
accepted_without_edit, regression, elapsed_minutes, human_minutes, notes
```

Compute:

```text
acceptance_rate = accepted_without_edit / completed_tasks
retry_rate      = (attempts - completed_tasks) / completed_tasks
cost_task       = model spend / completed_tasks
cost_accepted   = model spend / accepted_without_edit
total_cost      = model spend + tool/CI spend + human_minutes × agreed_hourly_rate / 60
```

Do not report cost per token as the decision metric. A cheaper model can cost more per accepted task when retries or review increase.

## Role routing decision

- Keep a low-cost model on `scout` and `tester` when it locates evidence and runs checks reliably.
- Keep implementation (`coder`, `worker`) on the lowest-cost model that achieves the acceptance and regression threshold. Raise reasoning before replacing the model when the failure is incomplete reasoning rather than missing ability.
- Use frontier models for planning, review, architecture, auth, permissions, migrations, data integrity, ambiguous requirements, or repeated failure.
- Keep `oracle` exceptional and advisory. Do not make it part of routine chains.
- Use `fresh` context by default. Pass a concise handoff when it prevents rediscovery; do not copy an entire transcript by habit.

Never make a global/default change solely because a frontier model tops a benchmark. Prefer a role-scoped override and a rollback path.

## Report and change process

Produce a concise report with:

1. Decision and current profile.
2. Evidence table: source type, exact model/settings, relevant result, uncertainty, and link.
3. Local evaluation results and cost per accepted task.
4. Recommendation by role, including which roles stay unchanged.
5. A proposed `config/settings.json` diff, migration/rollback instruction, and validation command.
6. Risks, evidence gaps, and the date or condition that should trigger the next review.

Do not change the configuration unless the user asks. If authorized, back up the current settings, apply only the scoped role changes, run the repository tests, and report the exact rollback path.

## Review cadence

Run a light review when a provider changes price/model availability, the task mix changes, the acceptance rate drops, or repeated agent failures appear. Run the full local evaluation before changing the default model, `worker`, `planner`, or `reviewer`.
