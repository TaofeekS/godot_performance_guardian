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

## Removed-experiment status

No experiment has been removed or reverted. Documentation-only changes remain in `AGENT_TRAJECTORY.md` rather than being presented as product experiments.
