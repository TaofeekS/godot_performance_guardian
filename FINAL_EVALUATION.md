# Final Evaluation: Godot Performance Budget Guardian

## Intended user and bottleneck

The intended user is a Godot developer or team that needs to detect performance regressions before they become difficult to isolate. Raw engine measurements are noisy and incomplete on their own: a developer must determine whether evidence is valid, decide which limits apply, compare revisions fairly, identify the failed rule, and preserve enough context for another person to reproduce the decision.

Baseline 0 could validate one fixed synthetic benchmark suite. The final product retains that validator and adds portable capture schemas, configurable policy, protected-base comparison, calibration, actionable reporting, a reusable CI workflow, a read-only editor workspace, and optional evidence-grounded investigation.

## Predefined success criterion

The primary metric is **correct actionable outcomes** across ten fixed cases. A case counts only when:

1. The process exit and outcome category match the predefined oracle.
2. Every required fact is present and numerically correct.
3. A policy failure names its rule, measured value, and threshold.
4. A comparison failure includes baseline, candidate, delta, and relative limit.
5. A validation error exposes a safe diagnostic category rather than raw private output.
6. Calibration provides observed values, margins, and proposed thresholds.
7. The normalized result contains no credential, private absolute path, capture source-revision value, or unsupported causal claim.

Success was defined before the final run as all ten final-solution cases passing their oracle, including the challenging relative-only regression. Baseline and final are scored with the same [`case manifest`](evaluation/cases.json).

## Compared implementations

| Side | Revision | Available interface |
| --- | --- | --- |
| Baseline 0 | `22af3b44962517b0f1d7ac0b7499f724f2e2cb34` | Synthetic scenario capture plus `validate_results.py` only. |
| Final product | `2bf5ff6efbedb44a8ac0370b686554a5a4ac4e40` | Synthetic and generic validation, v1/v2/v3 policy, unified gate, protected-base comparison, and calibration. Optional AI is excluded from the primary evaluation. |

The historical validator is preserved in [`evaluation/baseline/`](evaluation/baseline/) with its source revision and SHA-256 integrity metadata. The accepted nine Baseline 0 files are tracked under [`evaluation/fixtures/synthetic/`](evaluation/fixtures/synthetic/). This makes the comparison runnable without depending on ignored local results or reachable Git history.

The resource difference is deliberate and disclosed: later cases exercise customer needs that Baseline 0 did not support. Unsupported baseline capabilities are recorded as `unsupported`; they are not simulated, converted into false tool failures, or credited as correct outcomes. The resulting percentage measures expanded correct workflow coverage, not faster Godot frame performance.

## Evaluation command

From the repository root after creating `.venv` as described in the README:

```powershell
.\.venv\Scripts\python.exe .\tools\run_submission_evaluation.py --json
```

The evaluator uses Python's standard library, fixed repository-contained inputs, bounded argument-list subprocesses with `shell=False`, and no network or API call. Exit `0` means every final-solution oracle passed, exit `1` means the evaluation completed but at least one final oracle failed, and exit `2` means fixture integrity, configuration, or execution failed.

## Complete results

| # | Fixed case | Expected outcome | Baseline 0 | Final product |
| ---: | --- | --- | --- | --- |
| 1 | Accepted nine-run synthetic suite | Validate nine files and reproduce the 68.78× CPU/healthy workload ratio | Correct | Correct |
| 2 | Portable generic capture | Validate one generic profile with 0.5 ms process p95 and three peak nodes | Unsupported | Correct |
| 3 | Passing v2 policy | Pass 0.5 ms <= 1.1 ms and 3 nodes <= 3 | Unsupported | Correct |
| 4 | Absolute process failure | Fail the named process rule at 0.5 ms > 0.4 ms | Unsupported | Correct |
| 5 | Absolute node failure | Fail the named node rule at 3 > 2 nodes | Unsupported | Correct |
| 6 | Multiple policy failures | Preserve and report both failed rules | Unsupported | Correct |
| 7 | Unchanged v3 comparison | Pass equal baseline/candidate measurements | Unsupported | Correct |
| 8 | Relative-only process regression | Pass the absolute limit but fail 22% > 20% | Unsupported | Correct |
| 9 | Malformed generic evidence | Reject safely with a missing-schema diagnostic | Unsupported | Correct |
| 10 | Three-capture calibration | Propose 0.8 ms, four nodes, and 24 objects | Unsupported | Correct |

| Primary result | Baseline 0 | Final product | Change |
| --- | ---: | ---: | ---: |
| Correct actionable outcomes | 1/10 | 10/10 | +9 cases |
| Coverage | 10% | 100% | **+90 percentage points** |

The canonical [`final-evaluation.json`](evaluation/results/final-evaluation.json) contains each normalized case result, score inputs, failures, limitations, and both implementation revisions. Two consecutive evaluations produced byte-identical output with SHA-256 `d88261711f9fa836903137d5a9099a5102691a08ff7e2b59cb29518119d2e453`.

## Challenging case

The relative-only regression is intentionally difficult because an absolute-only gate would accept it. Baseline process p95 was `0.5 ms`; the candidate was `0.61 ms`. The candidate remained below the absolute `1.1 ms` maximum, but its `0.11 ms` increase was `22%`, exceeding the protected-base allowance of `20%`. The final gate returned policy-failure exit `1` and preserved the baseline value, candidate value, delta, percentage, absolute pass, and relative failure. Baseline 0 had no paired-comparison or configurable-policy interface.

This case shows the main practical contribution: the product does not merely collect more numbers. It turns validated evidence and project-owned policy into a reproducible decision that identifies exactly which constraint failed.

## Runtime, cost, and reproducibility

- One observed complete evaluator run on the verified Windows/Python environment took `3.515` seconds.
- Deterministic API cost was `$0`; no API key was read and no network request was made.
- Human review time was not measured and is not estimated.
- Fixed fixtures make tool outcomes repeatable, but they do not replace fresh captures on customer hardware.
- The comparison measures workflow coverage and evidence quality, not rendering speed, GPU performance, universal threshold quality, or project-owned object counts.

## Supporting AI evidence

AI behavior is deliberately excluded from the primary score because model responses are nondeterministic and depend on external access and quota. Existing experiments remain useful supporting evidence:

- Experiment 8: one Terra response and one Sol response each failed direct grounding and were replaced by deterministic cited fallback without a second application request.
- Experiment 9: one `gpt-4.1-mini` typed contribution supplied two accepted evidence-linked recommendations without fallback; an invalid optional hypothesis was discarded locally.
- Experiment 10: one live unified Mini run supplied three accepted recommendations while the deterministic gate remained authoritative.
- Experiment 13: one hosted paired comparison produced an accepted Mini contribution covering all three failed rules, limitations, and read-only next steps without a causal claim.

These are individual observations, not a model ranking or long-run reliability estimate. Full experiment evidence remains in [`IMPROVEMENT_CHANGELOG.md`](IMPROVEMENT_CHANGELOG.md).

## Failed or removed direction and lesson

Experiment 8 tested stronger free-form models as a possible quality improvement. Neither response met the grounding contract, so neither model was adopted. The lesson was that model size alone did not make an unconstrained report dependable. Experiment 9 retained a smaller model but narrowed its role to typed evidence selection while local code rendered and checked the report.

## Main failure mode and hot take

The remaining failure mode is mistaking engine-global, headless, fixed-fixture evidence for proof of a project-specific root cause. The probe cannot attribute every object or byte to game code, static-memory growth includes probe sample storage, and headless captures do not establish GPU behavior. The optional investigator can recommend a next measurement, but it cannot prove a leak or bottleneck from the current packet.

**Hot take:** a useful performance agent should not be trusted to decide whether the build passes. Deterministic tools should decide; calibration should propose; the agent should explain only what validated evidence supports.

## Conclusion

The final product met the predefined competition target: all ten fixed cases produced the required safe, evidence-complete outcome, compared with one case for Baseline 0. The measured gain is 90 percentage points of correct actionable workflow coverage. This does not claim that game performance became 90% faster or that all Godot projects are covered. It demonstrates that the project evolved from one synthetic validator into a reproducible performance gate that can validate portable evidence, enforce absolute and relative policy, reject malformed inputs, and propose reviewable budgets.

The next submission deliverable is the five-minute solution video. It should use this report as its factual source rather than introducing new measurements or claims.
