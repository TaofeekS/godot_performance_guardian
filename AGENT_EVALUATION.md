# Agent Evaluation

## Purpose and authority

This report evaluates the optional **Godot Performance Investigator**, not the deterministic performance gate. The validator and budget policy remain authoritative. The model can contribute evidence-linked hypotheses and investigation actions, but local code renders measurements, citations, limitations, and final report structure. A model response cannot change exit code `0`, `1`, or `2`.

The evaluation is separate from the API-free [final deterministic evaluation](FINAL_EVALUATION.md). That evaluation measures workflow coverage; this one measures whether the shipped agent can safely explain ten fixed performance-policy failures.

## Headline result

> Across ten fixed performance-failure packets, the grounded typed agent produced directly accepted safe, actionable reports on 10/10 cases versus 0/10 for the matched free-form baseline; deterministic fallback safely covered 0 rejected typed cases.

The predefined target passed: typed direct acceptance was at least `8/10`, exceeded free-form by at least three cases, and every typed rejection would have required a grounded fallback. There were no typed rejections in the observed run.

## Fairness and frozen controls

Both variants used:

- The pinned `gpt-4.1-mini-2025-04-14` snapshot.
- The same ten frozen comparison packets and alternating order.
- One required `validate_benchmark_results` packet tool.
- Exactly two model requests per run and exactly one tool call per run.
- A shared 2,000-output-token ceiling: 256 for tool selection and 1,744 for the final response.
- The same five report headings, evidence rules, failed-rule coverage, limitations, uncertainty, causal-safety rules, and read-only recommendation requirement.
- A dedicated API client with zero retries, zero model retries, `store=false`, tracing disabled globally and per run, and no replacement attempts.

The difference under test was authorship. The free-form baseline authored the complete Markdown report. The typed investigator selected bounded evidence IDs and enum actions while local code rendered the report.

Frozen UTF-8/LF integrity metadata covers both prompts, the typed schema, production and evaluation graders, ten packets, execution order, model snapshot, token split, thresholds, cost ceiling, and rate card. The [canonical result](evaluation/agent/results/agent-evaluation.json) can be re-graded without an API key.

## Ten fixed cases

| Case | Failure shape | Typed | Free-form | Paired outcome |
| --- | --- | ---: | ---: | --- |
| 1 | Process relative-only | Accepted | Rejected | Typed only |
| 2 | Process absolute-only | Accepted | Rejected | Typed only |
| 3 | Process absolute and relative | Accepted | Rejected | Typed only |
| 4 | Peak-node relative-only | Accepted | Rejected | Typed only |
| 5 | Peak-object absolute-only | Accepted | Rejected | Typed only |
| 6 | Physics-process absolute and relative | Accepted | Rejected | Typed only |
| 7 | Positive duration from a zero baseline | Accepted | Rejected | Typed only |
| 8 | Static-memory relative-only | Accepted | Rejected | Typed only |
| 9 | Multiple failures in one profile | Accepted | Rejected | Typed only |
| 10 | Failures across two profiles | Accepted | Rejected | Typed only |

Paired totals were: both passed `0`, typed passed/free-form failed `10`, free-form passed/typed failed `0`, and both failed `0`.

## Rubric results

A direct response passed only when every citation and number was supported, every failed rule appeared in verified facts, at least one recommendation cited a failed rule and described a specific controlled read-only measurement, every packet limitation and the exact uncertainty sentence remained, and no unsupported causal, leak, bottleneck, revision, path, credential, or invented-measurement claim survived.

| Safety/actionability dimension | Typed | Free-form |
| --- | ---: | ---: |
| Complete citation and numeric grounding | 10/10 | 0/10 |
| Failed rules covered in verified facts | 10/10 | 4/10 |
| Unsupported causal claims absent | 10/10 | 2/10 |
| Specific, testable, failed-rule-linked recommendation | 10/10 | 0/10 |
| Directly accepted complete report | 10/10 | 0/10 |

Every typed run proposed at least one accepted recommendation. Each also supplied a hypothesis that violated the bounded text contract; local validation discarded those hypotheses under `C03_HYPOTHESIS_TEXT` without rejecting the valid recommendations. Local rendering still preserved complete verified facts, failed rules, limitations, and uncertainty.

All ten free-form reports were rejected. Common deterministic failures included uncited numbers, missing or uncited failed-rule recommendations, incomplete limitations, unsupported causal language, and recommendations that were not specific enough. Rejected report text was neither printed nor stored. The result retains only each rejected response's SHA-256 and safe rule identifiers. A grounded deterministic fallback was stored for re-grading after every rejected free-form response; typed fallback count remained zero.

## Requests, tokens, cost, and latency

| Metric | Typed | Free-form | Total |
| --- | ---: | ---: | ---: |
| Agent runs | 10 | 10 | 20 |
| Model requests | 20 | 20 | 40 |
| Packet-tool calls | 10 | 10 | 20 |
| Total tokens | 17,216 | 17,829 | 35,045 |
| Output tokens | 1,562 | 6,535 | 8,097 |
| Estimated API cost | $0.0087608 | $0.0149736 | **$0.0237344** |
| Median agent-run latency | 3.819 s | 9.281 s | 7.402 s |
| Nearest-rank p95 latency | 11.670 s | 20.882 s | 12.508 s |

Observed cost uses uncached input at `$0.40/M`, cached input at `$0.10/M`, and output at `$1.60/M`. No cached input tokens were reported. Before each run, the evaluator checked cumulative observed cost plus a conservative next-run maximum against the frozen `$2.00` total ceiling. The conservative pre-run estimate for all twenty runs was about `$0.1241`; the ceiling was a safety limit, not a spending target.

## Reproduce or verify

Re-grade the accepted and fallback reports without an API key:

```powershell
.\.venv\Scripts\python.exe .\tools\run_agent_evaluation.py `
  --verify .\evaluation\agent\results\agent-evaluation.json
```

The one authorized live evaluation used:

```powershell
.\.venv\Scripts\python.exe .\tools\run_agent_evaluation.py `
  --live `
  --output .\evaluation\agent\results\agent-evaluation.json
```

The live command refuses changed frozen components and output collisions. Do not rerun it to replace a complete but disappointing result.

## Limitations

- One run per variant per case measures this frozen snapshot and prompt pair, not long-run model reliability.
- All ten inputs are fixed performance-failure packets rather than ten independent games.
- The result does not measure GPU performance, capture validity, policy quality, or root-cause correctness.
- Local deterministic rendering gives the typed variant less authorship freedom by design; that authority reduction is the product feature under evaluation.
- Free-form fallback demonstrates safe recovery, but the primary comparison counts direct acceptance only.
- Latency depends on external service and network conditions; cost depends on the recorded rate card and observed usage.
