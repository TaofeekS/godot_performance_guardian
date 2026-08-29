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
