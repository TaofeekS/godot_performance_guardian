# Improvement Changelog

This append-only record starts from the repository state accepted as the performance baseline on 2026-08-28. Every later product experiment should keep its own entry, including approaches that fail, are reverted, or are removed, so the evidence and lessons remain visible.

## 2026-08-28 — Baseline 0: Current deterministic benchmark

**Status:** Accepted baseline

### What and why

The current implementation was frozen as the starting point for future improvements. It provides deterministic `healthy`, `node_leak`, and `cpu_spike` scenarios, preserves 600 raw samples per run, and evaluates three isolated runs of every scenario with the same Python validator.

Establishing this state first makes later experiments comparable without treating undocumented implementation history as an improvement timeline.

### Evaluation method

The accepted suite used seed 1337, 120 warmup frames, 600 measured frames, one sample per frame, and three separate processes per scenario. The nine existing JSON files were evaluated together with `tools/validate_results.py` on the recorded Windows and Godot 4.5.1 environment.

### Verified result

| Evidence | Baseline result |
| --- | ---: |
| Healthy median p95 workload time | 185 µs |
| CPU-spike median p95 workload time | 12,725 µs |
| CPU-spike / healthy workload ratio | 68.78× |
| Healthy median p95 process time | 0.605 ms |
| CPU-spike median p95 process time | 15.075 ms |
| Healthy median scenario duration | 4,976.010 ms |
| CPU-spike median scenario duration | 7,992.353 ms |
| Node-leak retained nodes | 120 in every run |
| Healthy and CPU-spike retained nodes | 0 in every run |
| Validator outcome | 9 files validated successfully |

### Decision and next step

Accept this result as Baseline 0. Future experiments should reuse the same evaluation method and environment whenever possible, report deviations before making comparisons, and remain in this file even if later removed.

The next planned product stage is a configurable budget schema. It has not been implemented or evaluated yet.

## 2026-08-29 — Experiment 1: Validator-gated read-only investigator

**Status:** Retained; local boundary verified, live report unverified

### Hypothesis and reason

A reasoning layer can add a concise investigation narrative without weakening deterministic evaluation if it must call the existing validator first and receives no general shell, filesystem, or write capability. This was tried to begin the agent-assisted investigation stage while keeping `tools/validate_results.py` as the pass/fail authority.

### Change

Added a command-line OpenAI Agents SDK agent named `Godot Performance Investigator`. Its only function tool wraps the existing validator through a fixed repository-resolved path, accepts only repository-contained result directories, captures structured evidence, and handles validator failure, timeout, and operating-system errors. The agent is instructed to separate verified facts from possible explanations and to state remaining uncertainty. It cannot inspect arbitrary source files or modify the project.

### Evaluation method

The implementation was evaluated without an OpenAI API request. Sixteen standard-library unit tests exercised path containment, the real stored-result validator invocation, nonzero output, timeout and subprocess errors, evidence fields, exact agent/tool configuration, import behavior, and missing-key behavior.

The unchanged validator was also run over every JSON file currently in `demo_project/results/`. This reused the baseline scenarios, seed, warmup, sample length, validator, and recorded environment, but the set had expanded from nine to 21 files. Therefore its aggregate timings are a regression-safety check, not a like-for-like performance comparison with Baseline 0.

### Observed result

```text
Ran 16 tests in 0.270s
OK
```

```text
INFO: median p95 workload: healthy=148.000 usec, cpu_spike=8549.000 usec, ratio=57.76x
INFO: supporting evidence: process p95 healthy=0.408000 ms, cpu_spike=12.588500 ms; duration healthy=4976.010 ms, cpu_spike=6406.270 ms
Validated 21 result files successfully.
```

The command-line entrypoint was also invoked without `OPENAI_API_KEY`. It exited before calling the SDK runner and reported that configuration was missing. No live model output was produced or assessed.

### Decision and next step

Retain the single-tool, read-only boundary. It adds the intended investigation interface without changing the Godot scenarios or deterministic validator, and its local failure paths are covered.

The next experiment should use a newly issued environment-only API key to run the investigator against a fixed result set, then score whether all five report sections remain evidence-grounded and useful. Until that happens, the SDK-backed execution and report quality remain unverified.

## 2026-08-29 — Experiment 2: Actionable, secret-safe API rate-limit diagnosis

**Status:** Retained; mocked failure behavior verified, live recovery unverified

### Hypothesis and reason

The investigator could not explain a real `RateLimitError` because its generic exception handler printed only the exception class. A dedicated, allowlisted diagnostic should distinguish exhausted quota from temporary throttling without exposing API credentials, prompts, response bodies, or raw headers.

### Change

Added a rate-limit formatter and a dedicated CLI exception branch. It reports only HTTP 429, validated error code/type, validated request ID, and a numeric retry delay when present. `insufficient_quota` receives billing, credit, and project-limit guidance; other 429 responses receive throttling guidance. No application-level retry or automatic model fallback was added because the installed OpenAI client already retries 429 responses twice and quota exhaustion cannot be repaired by retrying.

### Evaluation method

The existing standard-library suite was expanded from 16 to 20 tests. New mocked cases cover insufficient quota, transient throttling with `Retry-After`, missing optional metadata, request-ID reporting, exclusion of raw sensitive content, and exactly one SDK-runner invocation. No OpenAI API request was made.

The unchanged deterministic validator was also rerun across the 21 stored benchmark files as a regression-safety check. As in Experiment 1, this expanded set is not a like-for-like replacement for the accepted nine-file baseline.

### Observed result

```text
Ran 20 tests in 0.298s
OK
```

```text
INFO: median p95 workload: healthy=148.000 usec, cpu_spike=8549.000 usec, ratio=57.76x
INFO: supporting evidence: process p95 healthy=0.408000 ms, cpu_spike=12.588500 ms; duration healthy=4976.010 ms, cpu_spike=6406.270 ms
Validated 21 result files successfully.
```

### Decision and next step

Retain the allowlisted 429 diagnostics and the no-extra-retry policy. The change makes the next failure actionable while preserving the investigator's credential and evidence boundaries.

The next step is to revoke the previously exposed credential, configure a newly issued environment-only key whose API project has available quota and model access, and rerun the investigator. A successful live response and the quality of its five-section report remain unverified.

## 2026-08-29 — Experiment 3: Deterministic evidence grounding

**Status:** Retained; deterministic grounding verified locally, post-change live quality unverified

### Hypothesis and reason

The original agent produced an apparently useful but partly speculative report. Experiment 3 adds deterministic evidence citations and automatically blocks ungrounded reports.

The first successful live report was retained as this experiment's “before” result rather than counted as a separate experiment. It reproduced the main measurements but did not connect the CPU-spike timing to the intentional nested workload, omitted node-leak evidence, introduced unsupported thermal, scheduling, locking, and contention explanations, and described the duration increase as approximately 25% instead of the calculated 28.7%.

### Change

The validator gained an optional deterministic `--evidence-json` interface while preserving its normal human-readable CLI and all existing assertions. The packet contains stable evidence IDs for validation status, workload/process/duration comparisons, ratios and percentage changes, cleanup results for every scenario, stored workload configurations, narrowly allowlisted controller behavior, and explicit limitations.

The investigator still has exactly one function tool and no general filesystem or shell access. Its instructions now require `[E#]` citations, all-scenario coverage, evidence-supported causal language, read-only evidence-linked recommendations, and the exact statement `The available evidence does not establish the root cause.` A local post-generation gate rejects invalid headings, unknown or missing citations, unsupported numbers or causes, omitted scenarios, unsafe recommendations, and false validation-success language. Rejected model text is not printed and the application does not retry.

### Evaluation method

The same 21 stored JSON files and unchanged validator assertions used by Experiments 1 and 2 were reused; Godot was not rerun. Packet generation was repeated and compared using canonical JSON serialization. Standard-library tests used fixed good and bad reports, subprocess mocks, and the real validator wrapper without contacting the OpenAI API.

This expanded set contains nine healthy, six node-leak, and six CPU-spike runs. Its CPU-spike results mix three `160 x 160` and three `240 x 240` historical workloads, so it remains a regression-safety set rather than a controlled replacement for Baseline 0.

### Observed result

```text
Ran 32 tests in 1.087s
OK
```

```text
INFO: median p95 workload: healthy=148.000 usec, cpu_spike=8549.000 usec, ratio=57.76x
INFO: supporting evidence: process p95 healthy=0.408000 ms, cpu_spike=12.588500 ms; duration healthy=4976.010 ms, cpu_spike=6406.270 ms
Validated 21 result files successfully.
```

The evidence packet calculated a 28.7431% median-duration increase. It recorded 120 retained nodes in every node-leak run and zero retained nodes in every healthy and CPU-spike run. A fixed grounded five-section report passed, while a “before-like” fixture containing the incorrect 25% value and an unsupported thermal explanation was rejected. Validation failures, timeouts, malformed packets, and operational errors produced no verified evidence.

No `OPENAI_API_KEY` was configured after local checks, so no post-change live request occurred. The target of a grounded live report covering all scenarios with zero unsupported causes therefore remains unverified.

### Decision and next step

Retain the deterministic packet and local grounding gate. They make unsupported output fail closed without expanding the tool boundary, weakening validation, or adding retries.

The next experiment should run exactly one post-change live evaluation with a newly issued environment-only key and a fixed, uniform benchmark result set. Score it against the original 4/4 report-quality rubric, verify all three scenarios are included, and require zero unsupported causal claims.

## 2026-08-29 — Experiment 4: Schema-driven deterministic fallback

**Status:** Retained; fallback verified locally, live fallback unverified

### Hypothesis and reason

Before Experiment 4, rejected model output produced no usable investigation. After Experiment 4, the same failure produces a deterministic, fully cited report without another API request.

The user observed a live report rejected with `G03_REQUIRED_EVIDENCE_MISSING`, `G04_SCENARIO_COVERAGE`, `G07_UNSUPPORTED_NUMBER`, `G08_REQUIRED_UNCERTAINTY`, `G11_UNCITED_RECOMMENDATION`, and `G13_UNTESTABLE_RECOMMENDATION`. The gate protected the evidence boundary, but returning only rule IDs made a completed validation and API request operationally unhelpful.

### Change

Added a deterministic five-section fallback that uses only the validator packet and is checked by the same grounding gate before it is printed. Rejected model text is neither printed nor stored, the SDK runner is not retried, and successful deterministic validation produces a successful CLI result. Validator failure still returns nonzero.

Evidence selection no longer depends on the current `E1` through `E22` numbering. Required facts are resolved uniquely by metric, scenario, source type, unit, and value shape; packet IDs are treated as opaque labels and carried into citations only. Renumbered evidence and unrelated additions are supported, while missing, duplicate, or malformed required semantic evidence fails safely.

Every fallback begins with:

```text
Report source: Deterministic fallback generated after model output failed grounding.
```

### Evaluation method

No Godot or OpenAI API request was made. Standard-library tests used the real stored-result validator, mocked SDK results, renumbered packets, unrelated evidence, missing and duplicate semantic items, grounded and rejected report fixtures, and validation-failure packets. Canonical structured validator output was generated twice and compared.

The current directory had expanded to 31 validated files: 13 healthy, nine node-leak, and nine CPU-spike. Its CPU results contain three `160 x 160` and six `240 x 240` workloads, so the aggregate is regression-safety evidence rather than a controlled comparison with Baseline 0.

### Observed result

```text
Ran 39 tests in 1.319s
OK
```

```text
INFO: median p95 workload: healthy=163.000 usec, cpu_spike=11510.000 usec, ratio=70.61x
INFO: supporting evidence: process p95 healthy=0.605000 ms, cpu_spike=12.537000 ms; duration healthy=4976.010 ms, cpu_spike=7285.752 ms
Validated 31 result files successfully.
```

The fallback passed the same grounding gate after every ID was renumbered, used the new IDs automatically, and remained unchanged when unrelated evidence was added. Missing and duplicate semantic matches failed safely. The observed rejection path returned a fully cited report, did not emit the rejected sentinel text, invoked the SDK runner once, and returned success because validation had passed. Both generated structured packets were identical.

The first implementation test run exposed five failures: historical assertions still assumed the earlier 21-file result set and the pre-fallback exit behavior. Replacing those fixed counts with calculations from the current packet removed another form of accidental coupling.

### Decision and next step

Retain the schema-driven matcher and fallback. Strict grounding remains the first choice, while deterministic evidence rendering makes rejection useful without weakening validation or spending another API request.

The next experiment should repeat one live investigator request against a fixed result directory and confirm that either the model report passes directly or the exact fallback disclosure and fully cited report are returned. Live fallback behavior remains unverified.

## 2026-08-29 — Experiment 5: Configurable performance budgets

**Status:** Retained; deterministic local and CI policy verified

### Hypothesis and reason

A small versioned budget file can turn already validated benchmark evidence into project-specific pass/fail policy without copying benchmark calculations, involving AI, or weakening the validator. This was tried because the earlier baseline had only embedded integrity assertions: changing project policy required code edits and could not produce a separate CI verdict.

### Change

Added `budgets/example_budgets.json` with four schema-version-1 demonstration rules and a standard-library-only `tools/check_budgets.py`. The checker validates the exact configuration shape, invokes the unchanged validator's structured mode through a fixed subprocess boundary, and matches facts semantically by metric, scenario, source type, and unit. Matched evidence IDs are preserved only for traceability.

Rules pass at or below their configured maximum. Human and canonical JSON modes report budget results in stable budget-ID order and preserve validator limitations. Exit code `0` means all rules passed, `1` means valid evidence produced at least one policy failure, and `2` identifies invalid configuration, evidence, validation, or execution.

The example intentionally tests healthy process time and cleanup as passing controls while using CPU-spike workload and node-leak cleanup as failing regression demonstrations. Its absolute timing thresholds are examples for the verified machine, not universal Godot guidance.

### Evaluation method

No Godot run, API request, validator edit, investigator edit, or stored-result change was made. Fixed synthetic packets and mocks tested configuration validation, semantic evidence selection, equality, ordering, output modes, subprocess safety, limitations, and all exit classes independently of the changing local result directory. The unchanged validator and example checker were then run against the complete existing result directory as an integration check.

### Observed result

The first complete test run found one presentation mismatch: human output used `PASSED` and `FAILED` while the fixed output contract expected `PASS` and `FAIL`. The labels were corrected without changing evaluation behavior. That suite reported:

```text
Ran 57 tests in 1.579s

OK
```

A final schema review then found that the implementation treated `description` as optional despite the approved exact rule shape. It was made required and covered by a missing-field case. The final 57-test suite still passed in 1.601 seconds.

The unchanged validator then reported:

```text
INFO: median p95 workload: healthy=166.000 usec, cpu_spike=11771.500 usec, ratio=70.91x
INFO: supporting evidence: process p95 healthy=0.811500 ms, cpu_spike=13.112000 ms; duration healthy=4976.008 ms, cpu_spike=7577.426 ms
Validated 40 result files successfully.
```

The example policy produced the intended outcome:

```text
Budgets: FAILED (2 passed, 2 failed, 4 total)
FAIL: cpu-spike-workload-p95
PASS: healthy-process-p95
PASS: healthy-retained-nodes
FAIL: node-leak-retained-nodes
```

The checker returned `1`, correctly distinguishing policy failure from invalid evidence. Two JSON-mode invocations were byte-identical and identified only `cpu-spike-workload-p95` and `node-leak-retained-nodes` as failures. A later verification script initially asserted the wrong JSON field names (`id`/`fail` instead of the implemented `budget_id`/`failed`); inspecting the documented schema corrected the harness, and the repeated-output check then passed.

### Decision and next step

Retain the versioned budget checker as the deterministic policy layer between validation and optional AI investigation. The separation is now explicit: the validator establishes evidence integrity, the budget file defines project limits, and the investigator may explain only validated evidence.

The next planned experiment is the ten-fixture evaluation set. It should exercise each supported metric and error class with versioned fixed inputs before expanding the budget schema or integrating the checker into an editor dock.

## 2026-08-29 — Experiment 6: Portable Godot 4.5 performance capture

**Status:** Retained; portability verified in one independent Godot 4.5.1 project

### Hypothesis and reason

The existing benchmark could validate and budget synthetic results, but measurement remained tied to its controller and three scenario names. The experiment tested whether the reusable monitor, summary, and atomic-output behavior could become a copyable addon without assigning synthetic workload or cleanup meaning to an unrelated project.

### Change

Added the `PerformanceBudgetProbe` runtime node and lightweight editor registration. The probe accepts project-defined profiles, configurable frame counts and output, optional source revision, automatic capture, and headless exit. It records only generic engine metrics, writes schema-identified JSON atomically under `res://`, and refuses collisions.

The validator now dispatches explicit synthetic and generic schemas through separate assertions. Synthetic behavior remains unchanged; generic evidence is keyed by profile and never claims actor ownership, retained nodes, cleanup, or workload time. Budget schema v2 adds profile-based rules for seven generic aggregate metrics while preserving v1 scenario policy.

An independent primitive-only project receives a copied addon during verification. One sanitized live capture is retained as `examples/fixtures/main_scene-godot-4.5.1.json`; the installation copy and runtime result remain ignored.

### Evaluation method

Fixed Python fixtures covered schema dispatch, unsafe values, sample ordering, recalculated summaries, source revisions, generic evidence, v2 budgets, mixed-type rejection, and all earlier tests. Godot then parsed the copied addon, ran GDScript helper and collision tests, and performed exactly one 120-warmup/600-measured-frame capture of `main_scene`. The live result, canonical fixture, 49 historical results, both policies, and repeated canonical JSON were checked through the same validator/checker entrypoints.

### Observed result

The live capture contained 600 samples covering frames 1 through 600. Its process-time p95 was `0.529 ms`, peak global node count was `3`, measurement duration was `4140.02 ms`, and total capture duration was `4949.63 ms`. No source revision was supplied, and the result states that the exact revision is unknown.

The calibrated v2 limits were `1.1 ms` and `3 nodes`; both passed. Generic validation and budget checking returned `0`. Reusing the explicit run ID returned `3` before measurement and left the original capture byte-identical.

All 49 historical synthetic files still validated with exit `0`. The unchanged Experiment 5 policy still returned `1` with only its CPU-spike and node-leak demonstration failures. Repeated generic evidence and budget JSON were byte-identical.

The final complete standard-library suite passed all 66 tests in 2.232 seconds, including validation and budget enforcement against the tracked canonical live fixture.

The addon was copied into the included independent Godot 4.5.1 project, produced valid performance measurements and successfully enforced a project-specific budget.

Two implementation lessons were retained. Godot plugin manifest scripts are addon-relative, so `res://.../plugin.gd` incorrectly doubled the path and was replaced with `plugin.gd`. A relative custom log path also triggered a Windows Godot logging crash before project verification; subsequent runs used normal process output and explicit exit codes.

### Decision and next step

Retain the explicit generic schema and profile-budget path. The proof establishes portability only for the included project on Godot `4.5.1.stable.official.f62fdbde1`, not universal addon or timing compatibility.

The next experiment should expand the tracked evaluation set toward ten fixtures, covering additional profiles, unavailable memory, non-unit sampling intervals, malformed captures, and expected budget failures before an editor dock is added.

### Experiment 6 clarification: probe memory overhead

The portable probe retains each raw sample in memory until it serializes the result. Consequently, observed static-memory growth includes probe storage overhead and cannot by itself prove a project memory leak. Addon version `1.0.1` makes this limitation explicit in every capture, and generic validation requires it. Memory budgets remain useful for comparable regression checks, provided both captures use identical measured-frame counts and sampling intervals. This clarification changes evidence interpretation, not the recorded Experiment 6 measurements or portability result.

The same evaluation entrypoints confirmed the correction: all 67 Python tests passed, the updated canonical generic fixture validated, its two calibrated v2 budgets passed, all 49 historical synthetic results still validated, and the Experiment 5 demonstration policy retained exactly its two intentional failures. No new Godot capture was made, so the original timing measurements remain unchanged.

A subsequent real-world validation attempt used the still-present ignored `1.0.0` runtime result and correctly failed the new `1.0.1` contract. The validator diagnostic was made actionable, and the README now uses one UTC-derived run-ID variable through capture, validation, and budget checking. The old file remained byte-identical. Exactly one fresh `1.0.1` capture then recorded 600 sequential samples, process p95 `0.951 ms`, peak node count `3`, measurement duration `4139.238 ms`, capture duration `4953.588 ms`, and all six required limitations. Generic validation and both calibrated budgets passed; the complete suite passed 68 tests. This retained result confirms the decision to require recapture instead of relabeling historical evidence.

## 2026-08-29 — Experiment 7: Portable generic-capture investigator integration

**Status:** Retained; generic grounding and fallback verified locally, live generic response unverified

### Hypothesis and reason

A schema-aware investigator can interpret validated portable captures by project-defined profile without weakening the established synthetic evidence boundary. This was tried because the portable probe, generic validator, and profile budgets already worked, but the investigator's instructions, semantic requirements, gate, and fallback still assumed `healthy`, `node_leak`, and `cpu_spike`.

### Change

The evidence packet now declares `evidence_kind` as `synthetic`, `generic`, or `failed`. As a pre-release schema-v1 correction, generic evidence uses `profile` exclusively; the reserved `all` profile carries only the global validation count. Profile discovery uses only profile-scoped metric and availability evidence.

Generic packets add memory and source-revision availability. Revision status is `present` when every contributing capture supplied a value, `unknown` when none did, and `mixed` when only some did. Revision values are never copied into evidence, compared, or reported.

The investigator now dispatches through the explicit packet kind. Its generic branch covers all profiles and available engine aggregates, preserves limitations, rejects unsupported numbers, invented memory, synthetic claims, causal conclusions, revision values or equality claims, unsafe recommendations, and sensitive paths. Rejected model output produces a deterministic generic fallback from semantic packet fields without another request. The synthetic path and one-tool read-only boundary remain intact.

### Evaluation method

Tracked synthetic and generic evidence fixtures, the real tracked generic capture, temporary variants, and SDK mocks exercised packet dispatch, reserved-profile exclusion, multiple profiles, available/unavailable/mixed memory, all revision states, citations, semantic ambiguity, grounding rejection, fallback determinism, and exactly one runner call. No test used ignored generated results or contacted the OpenAI API.

The existing generic validator and v2 policy were rerun against the canonical fixture. The 49 ignored historical synthetic results and Experiment 5 demonstration policy were checked separately as integration evidence. Godot was not rerun.

### Observed result

```text
Ran 86 tests in 1.760s

OK
```

Two structured generic packet generations were byte-identical. The tracked generic packet declared `evidence_kind: generic`, exposed `main_scene` as its only reportable profile, and kept `all` reserved for validation count. Both generic and synthetic deterministic reports passed their gates.

The canonical portable policy again passed process p95 `0.529 ms <= 1.1 ms` and peak nodes `3 <= 3`. All 49 historical synthetic files validated, while Experiment 5 retained exit `1` with only its CPU-spike workload and node-leak retention demonstration rules failing.

No `OPENAI_API_KEY` was configured, so no live request occurred. Generic model-response quality and live generic fallback behavior remain unverified.

### Decision and next step

Retain the explicit schema-kind dispatch and generic fallback. The change completes the offline-to-optional-investigator workflow without moving credentials or SDK code into Godot and without merging deterministic budgets into the agent.

The next iteration should make exactly one live generic request with a valid environment-only key, then expand tracked generic fixtures to cover additional real profiles and comparable multi-capture aggregates.

## 2026-08-29 — Experiment 8: Grounded model upgrade evaluation

**Status:** Retained as a negative comparison; no default-model change

### Hypothesis and reason

A stronger current model might follow the investigator's strict generic evidence contract closely enough to pass the deterministic grounding gate without fallback. The experiment evaluated balanced `gpt-5.6-terra` first and reserved flagship `gpt-5.6-sol` for the conditional case where Terra failed.

### Change

No product code changed during the comparison. Each candidate was supplied through the existing process-scoped `OPENAI_MODEL` override, preserving the one-tool read-only boundary, the tracked fixture, the prompt, the validator packet, and the gate. The acceptance rule was one exit-`0` five-section model report with no grounding warning or fallback.

### Evaluation method

The environment was checked only for API-key presence. Terra was invoked exactly once against `tests/fixtures/generic_results`. Because its direct response failed grounding, Sol was then invoked exactly once against the same fixture. No application-level retry, second call per model, fixture change, benchmark run, or rejected-text capture was added.

### Observed result

Terra's direct response failed six rules: `G14_UNCITED_VERIFIED_FACT`, `G18_MEMORY_AVAILABILITY`, `G19_REVISION_AVAILABILITY`, `G21_GENERIC_LIMITATION_MISSING`, `G23_UNSUPPORTED_GENERIC_CAUSE`, and `G24_REVISION_VALUE_OR_EQUALITY`.

Sol's direct response failed seven rules: `G13_UNTESTABLE_RECOMMENDATION`, `G14_UNCITED_VERIFIED_FACT`, `G18_MEMORY_AVAILABILITY`, `G19_REVISION_AVAILABILITY`, `G21_GENERIC_LIMITATION_MISSING`, `G23_UNSUPPORTED_GENERIC_CAUSE`, and `G24_REVISION_VALUE_OR_EQUALITY`.

Both commands returned `0` because the investigator suppressed the rejected response, generated the deterministic five-section fallback from the validated packet, and accepted that fallback. The live fallback reported the same tracked fixture values, including `0.5 ms` process p95 and three peak nodes. Neither model met the direct-grounding acceptance rule. These are single nondeterministic observations and do not establish a general quality ranking.

After the comparison, `pip check` reported no broken requirements, all 86 tests passed in 0.449 seconds, and byte compilation completed successfully. The documentation skill, links, headings, credential-pattern scan, and whitespace checks also passed.

### Decision and next step

Keep `gpt-4.1-mini` as the default and retain `OPENAI_MODEL` for explicit experiments. The stronger model alone did not resolve the format mismatch, so the next experiment should improve the model-facing report contract or generate a structured intermediate response while keeping the existing deterministic gate unchanged.

## 2026-08-29 — Experiment 9: Typed model contribution with deterministic rendering

**Status:** Retained; `gpt-4.1-mini` qualified first and remains the default

### Hypothesis and reason

The model can contribute useful investigation choices more reliably if it selects bounded enum actions and evidence IDs instead of reproducing the complete Markdown evidence contract. This was tried because Experiment 8 showed that both Terra and Sol omitted or altered deterministic report requirements when asked to author the full report directly.

### Change

The investigator now requests a strict typed contribution after the required validator call. It permits zero to three short hypotheses and requires one to three recommendations selected from a seven-value read-only action enum. Every item carries one to four unique opaque evidence IDs. Local validation rejects unsupported IDs, causal claims, measurements, Markdown, paths, citations, and sensitive text; invalid hypotheses may be discarded, but at least one recommendation must survive.

Local code renders all headings, verified facts, measurements, availability statements, limitations, citations, and canonical recommendation wording. The unchanged grounding gate checks the completed report. A run hook retains one safely validated tool packet so typed-output failure can use deterministic fallback without another request; absence of a recoverable packet remains a hard failure.

### Evaluation method

Fixed synthetic and generic fixtures plus SDK mocks exercised schema bounds, enum actions, optional hypotheses, mandatory recommendations, unique IDs, item filtering, deterministic rendering, packet recovery, hard failure, fallback, and one-runner-call behavior. The complete local suite, byte compilation, both tracked generic validations, canonical v2 policy, 49-file optional historical validation, and Experiment 5 demonstration policy were rerun before live evaluation.

The live order was `gpt-4.1-mini`, then Terra only if Mini failed, then Sol only if both earlier candidates failed. Qualification required exit `0`, no fallback, at least one accepted recommendation, a surviving model-authored item, and a report accepted by the unchanged grounding gate.

### Observed result

All 94 tests passed in 0.538 seconds. Both tracked generic validations returned `0`; the canonical portable policy again passed `0.529 ms <= 1.1 ms` and `3 <= 3`. All 49 historical results validated, and the Experiment 5 policy retained exactly its two intentional failures.

The single live `gpt-4.1-mini` invocation returned `0` without fallback. Local validation discarded one optional hypothesis under `C03_HYPOTHESIS_TEXT` and accepted two recommendations: one `profile` selection and one `compare` selection. The locally rendered report passed the existing grounding gate and preserved all generic facts and limitations. Because Mini qualified first, Terra and Sol were not called.

### Decision and next step

Keep `gpt-4.1-mini` as the default and retain the typed contribution plus deterministic rendering boundary. The result shows that one Mini response satisfied the new contract; it does not establish a general model-quality ranking or long-run reliability. A future evaluation should repeat the same acceptance test across several tracked profiles and multiple calls before considering a default change.

## Removed-experiment status

No experiment has been removed or reverted. Documentation-only changes remain in `AGENT_TRAJECTORY.md` rather than being presented as product experiments.

## 2026-08-29 — Experiment 10: CI performance gate with optional AI investigation

**Status:** Retained; deterministic local gate verified, GitHub-hosted execution unverified

### Hypothesis and reason

A single standard-library command can make validation and configurable budgets safe for CI while keeping optional AI interpretation strictly downstream of the authoritative decision. This was tried because the validator, budget checker, and investigator already worked independently, but callers had to compose their ordering, exit handling, and credential behavior themselves.

### Change

`tools/run_guardian.py` now validates repository-contained inputs, loads budget configuration first, invokes the existing structured validator once through the budget checker, and applies the existing budget evaluator without recalculating metrics. It preserves deterministic exits: `0` for passing policy, `1` for validated budget failures, and `2` for configuration, evidence, validation, or operational errors.

Optional modes are `never`, `on-failure`, and `always`. The investigator runs in one fixed subprocess only when the policy requires it and an environment key is present. Accepted typed reports and deterministic fallback are recognized by their established disclosures; malformed output is suppressed. Missing credentials, API failures, and investigation outcomes cannot change the authoritative deterministic exit.

A Windows GitHub Actions workflow now runs the complete suite and tracked fixture/policy gate on pull requests to `main`; pull requests never invoke AI. Manual dispatch exposes the three modes, scopes the API secret to the manual step, preserves the Python exit, and uploads canonical JSON even when the gate fails.

### Evaluation method

Twenty-six focused tests cover configuration-before-subprocess ordering, exits `0`/`1`/`2`, path and simulated symlink containment, every investigation mode, one-process limits, missing-key and API-error safety, accepted/fallback classification, rejected-output suppression, canonical JSON, import safety, and workflow structure. The complete repository suite, byte compilation, tracked generic validator and v2 policy, repeated canonical output, and optional 49-file synthetic integration were then rerun without Godot.

After all local checks passed, exactly one process-scoped `gpt-4.1-mini` invocation ran through the unified command in `always` mode against the same tracked generic fixture.

### Observed result

```text
Ran 120 tests in 0.629s

OK
```

The tracked fixture validated with exit `0`. Its budgets passed process p95 `0.5 ms <= 1.1 ms` and peak nodes `3 <= 3`; the unified runner returned authoritative exit `0`. Validator, budget, and unified canonical JSON were each identical across two invocations.

All 49 optional historical synthetic files validated. The Experiment 5 demonstration policy returned its expected `1`, with only `cpu-spike-workload-p95` and `node-leak-retained-nodes` failing.

The one live unified Mini request returned a directly accepted locally rendered report with three evidence-linked recommendations and no fallback. The optional investigation outcome was `accepted`; deterministic validation and both budgets still supplied the authoritative exit `0`. This one response does not establish long-run model reliability.

### Decision and next step

Retain the unified command and workflow. The implementation preserves the governing boundary: **The deterministic tools decide; the agent explains.**

The next step is to exercise the workflow through a pull request and a manual dispatch, inspect the uploaded artifacts, and then broaden the tracked profile/policy fixture set before treating hosted CI behavior as verified.

## 2026-08-29 — Experiment 11: Turnkey consumer-project performance CI

**Status:** Retained; independent local consumer proof passed, hosted reusable invocation unverified

### Hypothesis and reason

A consumer should be able to turn a committed probe and v2 policy into a repeatable performance gate with one small reusable-workflow job. This was tried because Experiment 10 automated Guardian's tracked fixture, but another Godot repository still had to install Godot, orchestrate fresh captures, validate external paths, preserve evidence, and handle deterministic exits itself.

### Change

A standard-library capture helper now accepts an explicit consumer workspace and repository-relative project configuration. It preflights the project, committed addon, measured scene, automatically starting probe, identifiers, frame settings, output path, and symlink containment. By default it launches three isolated Godot processes with collision-safe IDs, a 300-second timeout, revision-presence metadata, sanitized per-run logs, and a canonical manifest. It never deletes or overwrites existing captures and stops at the first failed process.

The validator, budget checker, unified runner, and investigator boundary now support `--workspace-root`. Inputs remain relative to the resolved consumer root, evidence stores only relative paths, and external workspaces accept generic captures only. A reusable Windows workflow checks out caller and matching Guardian revisions separately, installs Godot through an immutable setup-action pin, captures and gates the consumer project, optionally investigates downstream, and uploads evidence even when the authoritative gate fails. The project also adopted the MIT license.

### Evaluation method

Fixed tests exercised path containment, simulated symlink escape handling, command arguments, three-process isolation, optional scenes, revision metadata, timeouts, collision preservation, stop-on-failure, missing outputs, sanitized logs/manifests, external generic validation, and the workflow contract. Existing repository-root commands and investigator behavior remained in the complete regression suite.

For the portability proof, the included minimal project and canonical addon were copied into a temporary independent consumer directory. Exactly three Godot `4.5.1.stable.official.f62fdbde1` processes ran with seed-backed project activity, 120 warmup frames, 600 measured frames, sampling interval 1, and the existing calibrated v2 policy. No AI request or synthetic benchmark rerun was made.

### Observed result

All three fresh captures completed with 600 samples and supplied revision metadata. Their process-time p95 values were `0.364 ms`, `0.344 ms`, and `0.334 ms`; the cross-run median was `0.344 ms`, passing the unchanged `1.1 ms` maximum. Every capture peaked at three nodes, so the median peak-node result passed equality at `3 <= 3`.

The generic validator accepted all three files, the budget checker returned `0`, and the unified `never` gate returned authoritative exit `0`. The evidence contained no consumer absolute path, no temporary output remained, and investigation attempted zero API calls. Two earlier sandboxed attempts stopped safely on the first Godot crash and taught that the local executable needed explicit permission in this execution environment; the same helper then passed when the headless subprocess was allowed. Those failed outputs were not treated as measurements.

The complete post-change suite passed 129 tests. The reusable workflow itself is structurally tested but has not yet run on a GitHub-hosted caller.

### Decision and next step

Retain the reusable workflow, external-workspace boundary, capture helper, and MIT license. Addon installation and CI activation remain explicit separate steps, and the deterministic tools remain authoritative.

Next, merge the workflow and call it from an actual consumer repository at an immutable Guardian commit SHA. Inspect the hosted artifact and timing behavior before describing GitHub-hosted portability as verified.

### Experiment 11 clarification — invalid hosted workflow definitions

The first pushes containing Experiments 10 and 11 produced failed GitHub Actions records even though no `push` trigger was intended. Public run metadata showed three `push` failures with zero scheduled jobs. GitHub identified two definition errors: the repository workflow used the step-only `runner` context in job-level environment configuration, and the reusable workflow contained an unquoted colon in an input description.

The repository workflow now uses Windows' built-in `%RUNNER_TEMP%` inside command steps and retains `${{ runner.temp }}` only in the artifact step. The reusable description is quoted. Regression tests preserve pull-request/manual versus `workflow_call` triggers, reject accidental push triggers, prevent unsupported job-level context use, and detect the unquoted-description pattern.

Local evaluation passed all 130 tests, byte compilation, dependency consistency, and whitespace checks. This corrects the workflow-definition layer without changing capture, validation, budgets, investigation, or the Experiment 11 local Godot measurements. GitHub acceptance and a real hosted consumer call remain separate checks; the latter is still unverified.

After commit `a672eda` was pushed to `main`, GitHub reported both `Performance Guardian` and `Reusable Performance Guardian` as active. The corrected push produced no Actions run, which is the expected result because neither definition has a direct `push` trigger. The three earlier zero-job failures remain historical evidence. Definition acceptance is now verified; repository-job execution and a real hosted consumer call remain unverified.

### Experiment 11 clarification — setup-provided Godot executable

A separate consumer repository provided the first hosted reusable-workflow execution evidence. Checkout, Python setup, Godot setup, optional investigator dependency installation, and artifact upload completed, but the capture helper reported `Godot executable was not found`. The capture step appeared successful because evidence preservation uses `continue-on-error`; its recorded outcome was failure, so the authoritative gate correctly refused to evaluate incomplete captures.

Inspection showed that `setup-godot` supplied a `GODOT` executable path, while the reusable workflow passed the unresolved literal `godot` to the capture helper. The workflow now validates that `GODOT` is a file and passes that exact path. Regression coverage requires the setup-provided path and rejects restoration of the literal command.

The focused workflow tests and complete 130-test suite passed, and byte compilation succeeded. This corrects the hosted executable handoff without changing capture calculations, budgets, deterministic exit authority, or optional investigation. A successful hosted consumer capture remains unverified until the caller updates to the corrected immutable Guardian commit and reruns. The consumer's separately observed budget path must also match its committed file location.

Commit `580606bcf603bb0279d90a957c6498947d366182` was pushed to `origin/main`. GitHub's public metadata reported both workflow definitions active, and the reusable workflow blob at that commit matched the locally verified file. This verifies delivery and definition acceptance, not a successful hosted capture; the next evidence must come from a consumer rerun pinned to this corrected commit.

### Experiment 11 clarification — preserve dot-directory evidence

The consumer rerun at the executable-path correction succeeded: three captures completed, all three generic files validated, and the two project budgets passed at `0.093 ms <= 2 ms` process p95 and `12 <= 100` peak nodes. The authoritative exit was `0`, and `never` correctly made no investigation request.

Inspection of the downloaded artifact found only `_temp/capture-manifest.json` and `_temp/guardian-report.json`. The manifest listed three raw capture JSON files and three Godot logs beneath `.performance-guardian/`, but none appeared in the ZIP. The artifact action excludes dot-prefixed paths by default, so the workflow's promise to preserve raw evidence was not yet met even though measurement and policy evaluation succeeded.

The upload step now sets `include-hidden-files: true` while retaining an explicit path list limited to the consumer evidence directory and the two runner-temporary reports. Regression coverage requires the hidden-file input and exact paths and rejects the tooling checkout, workspace-wide upload, and API secret from that step. All 130 tests passed, byte compilation succeeded, and dependencies remained consistent. The change is retained; a new hosted `never` artifact must contain three capture JSON files, three logs, the manifest, and the gate report before raw hosted evidence preservation is called verified.

Commit `0cd6a573d21b5ddd1ffd624be2782d0e9979e3ab` was pushed to `origin/main`. GitHub reported the reusable workflow active, and its remote workflow blob matched the locally verified file. This verifies delivery and definition acceptance; the contents of a new consumer artifact remain the next required check.

### Experiment 11 clarification — hosted evidence bundle verified

The next consumer rerun produced `performance-guardian-main_scene-33277282941-1.zip`. Read-only inspection found all nine expected entries: three 600-sample capture JSON files, three Godot logs, the internal capture manifest, the runner manifest, and the canonical Guardian report. The report recorded three validated files, passing process and node budgets, `investigate: never`, and authoritative exit `0`. No private path or credential-shaped pattern was detected. This closes Experiment 11's pending hidden-directory artifact claim; optional hosted AI and paired comparison remain separate questions.

## 2026-08-29 — Experiment 12: Baseline-aware pull-request regression gate

**Status:** Retained; local deterministic and six-capture consumer evaluation passed, hosted paired execution unverified

### Hypothesis and reason

Absolute limits can miss a meaningful slowdown that remains below a generous ceiling. A protected-base paired gate should catch that regression without allowing a pull request to weaken its own policy, while preserving existing absolute-only commands.

### Change

Budget schema v3 adds `maximum_increase_percent` to each generic profile rule. The checker and unified runner accept optional `--baseline-results`, validate baseline and candidate independently, match semantic aggregates rather than evidence IDs, and require absolute plus relative limits. Comparison evidence uses packet schema v2 and omits revision values. The reusable workflow adds opt-in `compare-with-base`; on pull requests it reads policy from `github.event.pull_request.base.sha`, captures baseline then candidate with identical settings, preserves both evidence sets, and keeps optional AI downstream of deterministic policy.

### Evaluation method and observed result

Tracked fixtures cover an unchanged pair and a deliberate process regression. The regression candidate passed its absolute process limit at `0.61 ms <= 1.1 ms` but failed the relative rule because its increase was `22% > 20%`. Peak nodes remained unchanged. The complete local suite passed 146 tests.

A temporary independent consumer workspace used Godot `4.5.1.stable.official.f62fdbde1` for three baseline plus three unchanged-candidate runs. Every capture contained 600 samples. Baseline median process p95 was `0.531 ms`; candidate was `0.526 ms`, a `-0.942%` improvement. Peak nodes remained `3` to `3`. Both the 20% process rule and 0% node-growth rule passed, and the unified gate returned authoritative exit `0` without AI.

Exactly one authorized live comparison request was attempted after local checks. It reached deterministic fallback with `C06_VALIDATION_FAILED` because the investigator subprocess command appended the candidate directory twice. The model therefore received no authoritative comparison evidence and this was an operational integration failure, not a model-grounding result. The duplicate argument was removed, a regression test now requires each contained input exactly once, and local packet generation plus fallback grounding passed. The request was not retried, preserving the one-request limit; live comparison interpretation remains unverified.

### Decision and next step

Retain schema v3 and opt-in protected-base comparison. Merge the v3 policy first with comparison disabled, then enable comparison in a later pull request so the protected base controls policy. Sequential same-runner capture reduces environmental variation but does not prove identical thermal, scheduling, or system-load conditions. The next step is one real hosted consumer pull request and artifact inspection; hosted comparison-aware AI also remains unverified.

### Experiment 12 clarification — normalize hosted artifact paths

A consumer manual run supplied the first hosted evidence after Experiment 12. Candidate capture and the authoritative performance gate completed successfully, while protected-base checkout and capture were correctly skipped because comparison was not requested. The final upload nevertheless failed before creating an artifact with `Invalid pattern '.performance-guardian-base-source/./.performance-guardian'`: the workflow interpolated `project-path: .` into a baseline path even in absolute-only mode, and `actions/upload-artifact@v7` rejects explicit `.` and `..` relative path segments.

The workflow now resolves the consumer and optional protected-base project roots, verifies their containment, and stages a narrow evidence set beneath a fixed runner-temporary directory. Absolute-only runs stage candidate evidence and available reports. Comparison runs additionally stage baseline evidence and its manifest. The artifact action receives only the fixed staging path, so neither root nor nested consumer project paths become upload patterns. It still enables hidden files, runs unconditionally, and excludes source checkouts, `.git`, tooling, environment files, and credentials.

This correction changes artifact preservation only; it does not reinterpret the already green deterministic gate or alter capture, validation, budgets, or optional investigation. Local verification and delivery evidence are recorded in `AGENT_TRAJECTORY.md`. Hosted absolute-only staging and hosted paired artifact preservation require a consumer rerun pinned to the corrected immutable revision before either new path is described as hosted-verified.

## 2026-08-30 — Experiment 13: Valid object counts with always-on AI investigation

**Status:** Retained; local and hosted comparison plus one accepted AI contribution verified

### Hypothesis and reason

Object and node comparisons are meaningful only when the intended scene scripts loaded. The earlier hosted comparison appeared green, but both revisions logged `performance_visual.gd` parse failures while the independent probe continued. It therefore measured an inactive scene at 12 nodes and 1,418 objects rather than the intended 2,000-versus-25,000 shape populations.

### Change and consistent evaluation

The capture helper now treats Godot script parse/load diagnostics as capture failure even when Godot returns `0` and writes JSON. It preserves sanitized diagnostics, records `godot_script_error`, stops after the first invalid run, and exposes zero completed captures to deterministic validation or budgets. Fixed tests reproduce the successful-process-plus-JSON failure mode in both stdout and stderr.

PluginTest will remove its clean-checkout dependency on a cached custom global type, use seed `1337`, name `res://main.tscn` explicitly, and calibrate node/object ceilings from three valid 2,000-shape hosted runs. The later 25,000-shape comparison will use the same 120/600/1 settings and three runs per side. Process p95 retains its 2 ms absolute and 20% relative limits; node and object counts will use a 10% baseline-derived absolute ceiling and 5% relative limit.

### Observed result, decision, and next step

The focused Guardian tests reject the previously accepted failure shape with exit `2`, no authoritative capture entries, and a sanitized log. The invalid 12-node/1,418-object values are retained only as a lesson and were not used for policy calibration.

A clean local PluginTest checkout passed Godot 4.5.1 parsing and produced three baseline plus three candidate captures with 600 samples each and zero script/load errors. The 2,000-shape baseline median peaks were 2,280 nodes and 5,584 objects; the 25,000-shape candidate reached 26,357 nodes and 49,513 objects. The relative increases were approximately 1,056% and 787%, so both 5% count rules failed. Candidate process p95 also rose from 10.246 ms to 216.101 ms. This establishes that the corrected comparison sees the intended population difference, while the absolute 2 ms process rule remains deliberately unchanged and fails on this local machine.

Retain the script-integrity boundary and object policy. PluginTest `main` now contains the corrected deterministic 2,000-shape baseline with comparison disabled. Its first valid hosted comparison calibrated count ceilings from 2,320 median peak nodes and 5,891 objects to `ceil(baseline × 1.10)`: 2,552 and 6,481. The final PR rerun preserved six 600-sample captures and six clean logs. Median nodes increased from 2,289 to 26,366 (`1,051.857%`), objects from 5,608 to 49,511 (`782.864%`), and process p95 from 14.169 ms to 224.999 ms (`1,487.967%`). The deterministic gate returned `1` as intended.

Exactly one `gpt-4.1-mini` invocation occurred in the final run. Its typed contribution was accepted without fallback; one unsafe hypothesis was discarded under `C03_HYPOTHESIS_TEXT`, while three evidence-linked recommendations survived. Local rendering covered baseline/candidate values for process, node, and object rules, preserved every limitation and the exact root-cause uncertainty sentence, revealed no revision value, and made no unsupported causal claim. The 17-entry artifact contained all baseline/candidate captures and logs, both internal manifests, both runner manifests, and the canonical report, with no detected private path or credential pattern.

The experiment demonstrates that script-integrity enforcement changes an apparently green inactive-scene comparison into a valid, deterministic object-growth failure and a grounded explanatory report. Next, evaluate whether the 2 ms process ceiling is appropriate for this deliberately large project profile on its chosen CI hardware; do not relax it as part of this object-count experiment.

## 2026-08-30 — Experiment 14: Actionable GitHub Actions failure reporting

**Status:** Retained; local and hosted failure presentation verified, direct signed-in summary-body inspection pending

### Hypothesis and reason

A correct exit code is insufficient customer feedback when the failed Actions step shows only `Process completed with exit code 1`. The canonical artifact contained the observed `11.58 ms` process p95 and `2 ms` threshold, but users had to download and inspect JSON to learn which policy failed. The experiment tests whether a presentation-only layer can expose the same deterministic evidence immediately without changing policy authority or trusting model-authored prose.

### Change and consistent evaluation

`tools/render_action_report.py` validates Guardian report schema v1 or v2, prints every absolute and paired result, appends a structured Markdown job summary, and emits one escaped error annotation per failed deterministic rule. Absolute and relative failures for one rule are combined. Evaluation failures receive one safe annotation. Accepted and deterministic-fallback investigations may appear only under a non-authoritative heading; unsafe or rejected text is suppressed.

Both workflows save `run_guardian.py`'s exit before invoking the renderer. Renderer failure produces a warning but the workflow still exits with the saved deterministic `0`, `1`, or `2`. The canonical JSON, captures, logs, and manifests remain unchanged artifact evidence.

### Observed result, decision, and next step

The initial local evaluation passed all 160 tests and byte compilation. A fixed reproduction of the observed failure rendered `11.58 ms > 2 ms` and exactly one rule annotation. A real tracked v2 pass rendered `0.5 ms <= 1.1 ms` and `3 nodes <= 3 nodes` with gate/renderer exits `0`/`0`. A real tracked v3 regression retained authoritative exit `1`, reported baseline `0.5 ms`, candidate `0.61 ms`, delta `0.11 ms`, and `22% > 20%`, while the renderer returned `0` and did not alter the verdict.

Retain the presentation layer because it makes deterministic evidence visible at the failure point without duplicating calculations. The next step is the approved single PluginTest `on-failure` dispatch pinned to the delivered Guardian commit. Acceptance requires hosted log details, a failed-rule annotation, a job summary with the authority boundary and accepted/fallback AI when available, and an artifact that still contains canonical JSON plus raw evidence. No retry will be made if optional AI is inconclusive.

Guardian commit `7622997bd3a9c5d166703e578af943b7e25f61ba` and PluginTest caller commit `f3ca43995e3ed9780cc99e0f68182cb7ae25fe90` were pushed. Exactly one manual `on-failure` run (`33286227714`) completed. Three clean 600-sample captures validated; peak-node and object budgets passed, while process p95 failed at `11.619 ms > 2 ms`, preserving authoritative exit `1`. The step printed the measurement and threshold, and GitHub exposed one named `main-scene-process-p95` annotation in addition to its generic exit annotation.

The optional `gpt-4.1-mini` request was attempted once and accepted; no fallback or retry occurred. Its five-section report retained the required uncertainty statement and contained no detected private path, revision value, or credential pattern. Renderer completion without a presentation warning establishes that the summary file was appended before the log was printed. The public API and unsigned Actions view did not expose the custom Markdown body, so its direct signed-in visual inspection remains pending rather than inferred as a UI claim.

The nine-entry artifact retained three capture JSON files, three clean Godot logs, the internal and runner manifests, and canonical Guardian JSON. All capture files contained 600 samples and addon version `1.0.1`; generic validation passed, and artifact scans found no private absolute path or credential pattern. This meets the actionable log, annotation, AI separation, and evidence-retention goals without changing the unchanged `2 ms` project policy. A future signed-in inspection can close only the visual-summary evidence gap; it does not require another performance or AI run.

## 2026-08-30 — Experiment 15: Budget calibration assistant

**Status:** Retained; deterministic local and hosted proposal generation verified

### Hypothesis and reason

Customers should not have to invent initial timing and global-count thresholds by hand. A deterministic assistant can turn repeated validated captures into a conservative, reviewable policy without weakening the separation between evidence, policy, and optional AI.

### Change and evaluation method

`tools/calibrate_budgets.py` invokes the existing structured validator once, requires passed generic evidence with at least three contributing captures per profile, and discovers aggregate facts semantically. Its balanced preset proposes process p95 at 150% of the observed median rounded upward to `0.1 ms`, peak nodes and objects at 110% rounded upward to integers, and relative allowances of 20%, 5%, and 5%. Outputs are deterministic, atomically written, collision-refusing schema-v3 policy and calibration-report files. The separate apply mode revalidates the proposal and requires `--replace` before changing an existing target.

The reusable workflow adds opt-in `mode: calibrate`, defaulting to five runs. Calibration is restricted to manual dispatch on the consumer default branch, forbids protected-base comparison and AI investigation, skips enforcement, and uploads proposal evidence. Existing `enforce` behavior remains the default.

The consistent local evaluation used the included independent Godot `4.5.1.stable.official.f62fdbde1` project with seed 1337, 120 warmup frames, 600 measured frames, sampling interval 1, and five isolated processes. The existing synthetic benchmark was not rerun and OpenAI was not called.

### Observed result, decision, and next step

All five fresh captures validated. Their aggregate medians were `0.421 ms` process p95, `3` peak nodes, and `1,393` peak objects. The assistant proposed `0.7 ms`, `4` nodes, and `1,533` objects. Applying the proposal to a temporary contained policy succeeded, and the same five captures passed all three absolute limits. The initial complete suite passed 173 tests.

Retain proposal-only calibration. The measurements and thresholds are host-specific and global node/object counts are not project-owned; headless capture does not measure GPU performance. The proposal has no authority until reviewed and committed.

Guardian commit `a1d0cfd02cffbc626884454cdcd4341dd1c2bd24` and PluginTest caller commit `5dde4ee3b4614d1d9aa208ecddbc29fcd9b16c72` were pushed. Exactly one PluginTest default-branch calibration ran as Actions run `33288045948`. Optional investigator installation, enforcement, comparison, and AI were all skipped. Five clean 600-sample captures validated and yielded medians of `11.62 ms`, `2,281` peak nodes, and `5,580` peak objects; the proposal was `17.5 ms`, `2,510` nodes, and `6,138` objects. Evaluating the proposal against the same captures passed all three absolute rules.

The artifact contained the expected fourteen files: five captures, five sanitized logs, the internal and runner manifests, calibration report, and proposed policy. Scans found no private path or credential-shaped value. The proposal remains unapplied in PluginTest. The next step is customer review of that policy, followed by an explicit commit with comparison disabled; enabling protected-base comparison remains a later pull request.
