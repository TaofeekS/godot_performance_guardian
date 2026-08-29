# Godot Performance Budget Guardian

## 1. Project overview

Godot Performance Budget Guardian is a synthetic Godot 4.5 benchmark that detects CPU-time and node-growth regressions in repeatable scenarios, preserves raw per-frame evidence, and validates calculated results so developers can investigate changes instead of relying on a visual impression of performance.

## 2. Current status

| Status | Capability |
| --- | --- |
| Implemented and verified | Deterministic `healthy`, `node_leak`, and `cpu_spike` scenarios; headless metric collection; atomic JSON output; three isolated runs per scenario; standard-library Python validation; a locally tested, read-only investigator that gates its reasoning on that validator. |
| Partially implemented | Performance budgets are embedded as controller tolerances and validator assertions. There is no standalone, user-editable budget file or stored golden baseline. |
| Unverified | The investigator's live OpenAI API execution and the usefulness of its model-generated investigation report have not been exercised with a valid key. |
| Planned | Configurable budgets, ten evaluation fixtures, a reusable Godot editor dock/plugin, experimental repair and verification, categorized result packages, and the final hackathon submission workflow. |

This repository is a fresh synthetic project for the Micro1 Agentic Workflows Hackathon. It does not use unrelated private source code, private assets, or proprietary telemetry.

## 3. Intended user and problem

The intended user is a Godot developer or team maintaining a project where small code changes can gradually add per-frame work or leave objects alive. These regressions are difficult to notice manually: frame timing is noisy, leaks accumulate slowly, and a short interactive play session may still feel normal.

Repeatable scenarios and explicit limits make the same work measurable before and after a change. This complements Godot's profiler rather than replacing it. The profiler is an interactive inspection tool; this baseline produces machine-readable evidence and an objective process exit status that can eventually be used in automation.

## 4. Current baseline

The current baseline:

- Runs three deterministic synthetic scenarios with a fixed seed and fixed frame counts.
- Collects raw timing, memory, object, node, and scenario-owned measurements.
- Compares a multi-run result set against embedded cleanup, growth, and relative CPU thresholds.
- Reports pass or fail through the validator's output and exit code.
- Does not load configurable budgets. An optional investigator can validate stored evidence and produce constrained hypotheses, but it cannot prove root causes or modify the project.

It is a benchmark, evaluator, and initial read-only reasoning layer, not yet the complete editor plugin or automated repair product.

## 5. Repository structure

```text
.
|-- README.md
|-- AGENT_TRAJECTORY.md
|-- IMPROVEMENT_CHANGELOG.md
|-- requirements-agent.txt
|-- agent/
|   |-- __init__.py
|   `-- investigator.py
|-- tests/
|   `-- test_investigator.py
|-- .agents/
|   `-- skills/
|       `-- godot-performance-guardian-docs/
|           |-- SKILL.md
|           |-- agents/openai.yaml
|           `-- references/readme-requirements.md
|-- demo_project/
|   |-- project.godot
|   |-- main.tscn
|   |-- run_benchmarks.ps1
|   |-- scripts/
|   |   |-- benchmark_controller.gd
|   |   `-- test_actor.gd
|   `-- results/                 # Generated locally; ignored by Git
`-- tools/
    `-- validate_results.py
```

- [`demo_project/project.godot`](demo_project/project.godot) defines the Godot 4.5 project and main scene.
- [`demo_project/scripts/benchmark_controller.gd`](demo_project/scripts/benchmark_controller.gd) implements scenario execution, measurement, summaries, cleanup, and atomic output.
- [`demo_project/scripts/test_actor.gd`](demo_project/scripts/test_actor.gd) implements the lightweight deterministic `Node2D` actors.
- [`demo_project/run_benchmarks.ps1`](demo_project/run_benchmarks.ps1) launches three isolated runs of each scenario and calls the validator.
- [`tools/validate_results.py`](tools/validate_results.py) validates schemas, calculations, cleanup evidence, leak growth, and relative CPU cost using only the Python standard library.
- [`agent/investigator.py`](agent/investigator.py) defines the read-only OpenAI Agents SDK investigator and its sole restricted validator tool.
- [`tests/test_investigator.py`](tests/test_investigator.py) verifies the tool boundary, path containment, subprocess failures, configuration, and no-key behavior without an API request.
- [`requirements-agent.txt`](requirements-agent.txt) pins the optional investigator dependency to the installed SDK version.
- [`AGENT_TRAJECTORY.md`](AGENT_TRAJECTORY.md) records the evidence-based history of the documentation task.
- [`IMPROVEMENT_CHANGELOG.md`](IMPROVEMENT_CHANGELOG.md) is the append-only product experiment record, beginning with the accepted current-state baseline.
- [`.agents/skills/godot-performance-guardian-docs/SKILL.md`](.agents/skills/godot-performance-guardian-docs/SKILL.md) defines the repository-local documentation workflow.

Godot-generated `.uid` files are present beside the GDScript sources. The `.godot/` cache and generated result JSON files are intentionally ignored.

## 6. Requirements

| Requirement | Current evidence |
| --- | --- |
| Godot | Exactly tested with `4.5.1.stable.official.f62fdbde1`. Other 4.5.x builds have not been verified. |
| Python | Python 3.14.6 was used successfully. The validator uses only the standard library; other Python versions have not been verified in this repository. |
| PowerShell | PowerShell 7.6.4 was used successfully for the batch harness. |
| Operating system | Windows 10.0.26200 is the only verified platform. Linux and macOS are unverified, and the supplied batch harness is PowerShell-specific. |
| Debug build | Not required for scenario execution. `Performance.MEMORY_STATIC` is accepted only when a debug build reports a positive value; otherwise memory samples are `null` and explicitly marked unavailable. |
| External dependencies | The benchmark needs only Godot, PowerShell for the batch harness, and Python's standard library for validation. The optional investigator pins `openai-agents==0.22.0`. |
| Network or API key | Benchmarking and deterministic validation need neither. A live investigator run requires network access and `OPENAI_API_KEY`; local investigator tests do not. |

## 7. Quick start

Clone the configured `origin` repository:

```powershell
git clone https://github.com/TaofeekS/godot_performance_guardian.git
Set-Location .\godot_performance_guardian
```

If the repository is already checked out, open PowerShell at its root. Assign the installed Godot executable without committing a machine-specific path:

```powershell
$Godot = "C:\path\to\Godot_v4.5.1-stable_win64.exe"
```

Open the synthetic project in the editor:

```powershell
& $Godot --editor --path .\demo_project
```

Run one headless scenario:

```powershell
& $Godot --headless --path .\demo_project -- --scenario=healthy
& $Godot --headless --path .\demo_project -- --scenario=node_leak
& $Godot --headless --path .\demo_project -- --scenario=cpu_spike
```

Each direct run accepts optional `--run-id=<id>` and `--output=<file-or-directory>` arguments after `--`. Without them, the controller creates a unique run ID and writes beneath `demo_project/results/`.

Run the complete three-by-three suite and its evaluation:

```powershell
.\demo_project\run_benchmarks.ps1 `
  -GodotExecutable $Godot `
  -PythonExecutable python
```

Validate an existing result directory independently:

```powershell
python .\tools\validate_results.py .\demo_project\results
```

Generated files are in `demo_project/results/`. They are local evidence and are ignored by Git.

To install and run the optional read-only investigator in the repository virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements-agent.txt
$env:OPENAI_API_KEY = "<newly-issued-api-key>"
$env:OPENAI_MODEL = "gpt-4.1-mini" # Optional; this is the default.
.\.venv\Scripts\python.exe -m agent.investigator demo_project\results
```

The key is read only from the process environment. Do not place it in source files, command logs, `.env` files intended for commit, or documentation. The argument must be a repository-relative directory containing result JSON files. Absolute paths, missing directories, paths outside the repository, and directories without JSON results are rejected before any API request.

### Investigator troubleshooting

The investigator exits nonzero when it cannot obtain a model response. Its messages intentionally omit the API key, prompt, raw exception, response body, and general response headers.

| Symptom | Meaning and next action |
| --- | --- |
| `OPENAI_API_KEY is not configured` | The variable is absent from the process running Python. Set a newly issued key in that same PowerShell session. |
| `AuthenticationError` | The API rejected the credential. Replace or correct the environment value; never paste it into source or documentation. |
| HTTP 429 with `code=insufficient_quota` or `type=insufficient_quota` | The API project has no available quota. Check its API billing, credits, and project usage limits. Repeating the command will not repair this condition. |
| Other HTTP 429 | The request was throttled. The message includes a numeric retry delay when the server provides one. Wait before retrying and inspect the API project's rate limits if it persists. |
| `PermissionDeniedError` or `NotFoundError` for the selected model | Verify that the API project can access `OPENAI_MODEL`. Do not switch models unless the error evidence indicates model-specific access or limits. |

The installed OpenAI Python client already retries HTTP 429 twice. The investigator deliberately does not wrap the entire agent run in another retry loop, which avoids duplicate tool execution and additional requests when quota is exhausted. A request ID is printed when available so it can support diagnosis without exposing request content.

## 8. Benchmark methodology

- **Random seed:** `1337` initializes actor positions and velocities.
- **Actors:** every scenario measures 64 lightweight `Node2D` actors using deterministic fixed-step calculations rather than wall-clock delta.
- **Warmup:** 120 frames execute without recording samples. Warmup-only transient state is cleared before the measurement baseline.
- **Measurement:** 600 frames are sampled at an interval of one frame. Each frame's workload runs before its sample is captured.
- **Repeated runs:** the PowerShell harness launches each scenario three times in a separate Godot process, producing nine files.
- **Lifecycle:** normal actors are released during evidence cleanup. Intentional leak nodes survive the post-cleanup snapshot and JSON write, then final teardown releases them before exit.
- **Direct workload timing:** `Time.get_ticks_usec()` surrounds the scenario workload and produces `workload_time_usec`.
- **Godot monitors:** process time, physics-process time, static memory, object count, node count, and orphan-node count come from `Performance.get_monitor(...)`. Scenario-owned actor and retained-node counts are recorded separately.
- **Statistics:** each run stores mean, p50, p95, and maximum timing. Percentiles use nearest rank: sort ascending and select one-based rank `ceil(p * N)`, clamped to `1..N`.
- **Cross-run comparison:** the validator compares the median of the three per-run p95 workload times for CPU spike and healthy.
- **Duration:** measurement duration covers the 600 measured frames. Total scenario duration begins before setup and ends after evidence cleanup but before final teardown.
- **Raw evidence:** all 600 samples are retained so summaries can be independently recalculated and trends or outliers can be examined later.

The workload is deterministic, but elapsed timings and engine-wide memory/object readings are still affected by the host system.

## 9. Scenarios

### Healthy

Maintains the fixed actor population and performs predictable arithmetic. Evidence cleanup must leave zero scenario-owned actors and zero retained nodes. Small engine-wide object or memory changes are tolerated because Godot and its allocator may perform bookkeeping outside scenario ownership.

### Node leak

Creates a temporary node every measured frame and intentionally retains one every five frames. The final measured frame and post-cleanup snapshot must contain exactly 120 scenario-owned retained nodes. Global node and object monitors should increase, while ordinary actors are still cleaned up. The retained nodes are freed only during final teardown.

### CPU spike

Runs the healthy actor lifecycle plus a fixed `240 x 240` nested numerical calculation every frame. Scenario-owned node counts must remain stable and no nodes may be retained. Its median per-run p95 `workload_time_usec` must be at least twice the healthy median; process time and total duration are supporting evidence.

## 10. Performance budgets

There is no configurable budget file yet. Current limits are embedded in two places:

- `benchmark_controller.gd` records a healthy object-growth tolerance of 32 and a memory-growth tolerance equal to the greater of 1 MiB or 2% of baseline memory.
- `validate_results.py` requires healthy cleanup, exactly 120 retained leak nodes, increasing global node/object evidence, stable CPU-spike ownership, at least three unique runs per scenario, and a CPU-spike median p95 workload time at least 2× healthy.

Each JSON result records the controller tolerances using the implemented schema:

```json
{
  "tolerances": {
    "healthy_object_count_growth": 32,
    "healthy_memory_growth_bytes": 1048576,
    "memory_absolute_floor_bytes": 1048576,
    "memory_relative_fraction": 0.02
  }
}
```

When static memory is unavailable, `healthy_memory_growth_bytes` is `null` and memory validation is skipped explicitly. Changing the present thresholds requires coordinated edits to the controller and validator; a single configurable schema is roadmap work.

Limits should be calibrated from repeated healthy runs on the target environment. Results from different machines, operating systems, power modes, background loads, or Godot builds should not be compared as though they share one performance budget.

## 11. Output format

Every run writes one JSON document atomically through a temporary sibling file. Existing final paths are not overwritten. This abbreviated example is taken from a verified CPU-spike result; the actual file contains 600 samples and complete summaries:

```json
{
  "schema_version": 1,
  "scenario": "cpu_spike",
  "run_id": "cpu_spike-20260828T193246205Z-run-01",
  "godot_version": "4.5.1-stable (official)",
  "seed": 1337,
  "warmup_frames": 120,
  "sample_frames": 600,
  "sampling_interval_frames": 1,
  "metric_availability": {
    "memory_static_bytes": {
      "available": true,
      "debug_only": true
    }
  },
  "samples": [
    {
      "frame": 1,
      "workload_time_usec": 10544,
      "process_time_ms": 14.354,
      "memory_static_bytes": 21918494,
      "object_count": 1460,
      "node_count": 69,
      "owned_actor_count": 64,
      "retained_node_count": 0
    }
  ],
  "summary": {
    "retained_nodes": 0,
    "scenario_duration_ms": 8470.381
  },
  "p95_process_time_ms": 16.636,
  "p95_workload_time_usec": 14732.0,
  "peak_node_count": 69.0,
  "retained_nodes": 0
}
```

The full document also includes engine and execution-environment metadata, physics time, orphan-node counts, baseline and post-cleanup snapshots, mean/p50/p95/max timing, initial/final/peak/delta count summaries, measurement duration, and a workload checksum.

There is currently no `budget_results` or structured `errors` property in an individual JSON result. Budget-style evaluation happens when the Python validator reads a result set. Invalid arguments, output failures, and validation failures are written to stderr and produce a nonzero exit code.

## 12. Evaluation

[`tools/validate_results.py`](tools/validate_results.py) objectively checks:

- JSON schema, metadata, declared metric availability, and all 600 sequential samples.
- Summary calculations recomputed from raw values using the declared nearest-rank rule.
- Unique run IDs and at least three runs for every scenario.
- Healthy cleanup and bounded engine-wide growth.
- Exactly 120 retained nodes plus increasing node/object evidence in the leak scenario.
- Stable scenario-owned nodes in the CPU-spike scenario.
- A CPU-spike median p95 direct-workload time at least twice healthy.
- Successful atomic output with no leftover temporary files.

Verified output from the successful nine-run Windows suite on 2026-08-28:

```text
INFO: median p95 workload: healthy=185.000 usec, cpu_spike=12725.000 usec, ratio=68.78x
INFO: supporting evidence: process p95 healthy=0.605000 ms, cpu_spike=15.075000 ms; duration healthy=4976.010 ms, cpu_spike=7992.353 ms
Validated 9 result files successfully.
Benchmark suite passed.
```

This is evidence from one machine, not a portable performance promise. The same scenarios and validator logic are deterministic enough for controlled comparisons, while timing values remain noisy.

The optional investigator exposes that same program as its only function tool, `validate_benchmark_results`. SDK configuration requires the tool on the first model turn and then allows a five-section report: Validation status, Verified facts, Possible explanations, Recommended next investigation, and Remaining uncertainty. A validator pass means only that the configured assertions passed; it is not proof that the project has no other performance issue.

Local investigator verification on 2026-08-29 ran 20 standard-library unit tests with no API request and passed all 21 JSON files then present in `demo_project/results/`. The tests include safe classification of exhausted quota and transient 429 responses, numeric retry-delay handling, request-ID reporting, sensitive-content exclusion, and confirmation that application code does not retry the agent run. The validator command reported a 57.76× CPU-spike/healthy median-p95 workload ratio across that expanded result set. This 21-file safety check does not replace or revise the accepted nine-file Baseline 0 because it uses a different run set. Live model output remains unverified.

## 13. Reproducibility notes

- Use unchanged scenarios for baseline and final comparisons.
- Run both sides on the same hardware, OS configuration, Godot build, power mode, and comparable background load.
- Preserve the fixed seed, warmup, measurement length, sampling interval, and repeated-run count.
- Prefer the direct workload timer for CPU comparisons; use engine process time and total duration as supporting evidence.
- Expect timing and allocation noise. Warmup and three isolated runs reduce, but do not eliminate, that noise.
- Headless runs do not produce meaningful rendering or GPU measurements.
- Keep the recorded Godot version and environment metadata with every result.
- Generated results are ignored by default, so deliberately copy selected evidence into a future versioned evidence package when required.

## 14. Known limitations

- Only synthetic scenarios are implemented; no real-game workload is included.
- Only the exact installed Godot 4.5.1 official build has been verified.
- The benchmark implementation is GDScript-focused.
- `MEMORY_STATIC` is debug-sensitive and can be unavailable.
- Evidence focuses on CPU work and object/node growth, not rendering or GPU performance.
- Thresholds are duplicated in code rather than loaded from a configurable budget file.
- There is no committed golden baseline or baseline/iteration/final result organization.
- There is no reusable editor dock or repair workflow. The investigator produces evidence-constrained hypotheses only; it has no source-reading tool and cannot establish root cause by itself.
- Live investigator execution and report quality have not yet been evaluated with a valid API key.
- Windows is the only verified operating system; the harness is PowerShell-specific.
- Individual result JSON does not contain a consolidated budget verdict or structured error object.

## 15. Roadmap

| Stage | Status | Intended outcome |
| --- | --- | --- |
| 1. Deterministic baseline | Completed | Three synthetic scenarios, raw samples, summaries, repeated runs, and objective validation. |
| 2. Configurable budgets | Partial/planned | Replace embedded thresholds with a single documented budget schema and explicit per-run verdicts. |
| 3. Ten evaluation fixtures | Planned | Add a broader, objective regression fixture set. |
| 4. Reusable Godot editor dock | Planned | Run and inspect budgets from a reusable editor plugin. |
| 5. Agent-assisted investigation | Partial | A read-only, validator-gated command-line investigator is implemented and locally tested; live report quality is unverified. |
| 6. Temporary experimental fixes and verification | Planned | Apply isolated candidate changes and rerun the same evidence. |
| 7. Final baseline comparison and submission package | Planned | Package selected baseline, iteration, and final evidence with hackathon documentation. |

## 16. Hackathon evidence

- [`AGENT_TRAJECTORY.md`](AGENT_TRAJECTORY.md) is the chronological audit of documentation and investigator implementation tasks: requests, decisions, inspections, edits, issues, and verification.
- [`IMPROVEMENT_CHANGELOG.md`](IMPROVEMENT_CHANGELOG.md) is the append-only product experiment record. It establishes Baseline 0 and records the first post-baseline investigator experiment.
- Generated benchmark evidence currently exists locally beneath `demo_project/results/` and is ignored by Git.
- Dedicated versioned baseline, iteration, and final result packages are planned and do not yet exist.

The trajectory explains how an agent performed work. The improvement changelog explains how the product changes across evidence-backed experiments, including unsuccessful or removed approaches.

### Documentation skill

The repository-local [`godot-performance-guardian-docs`](.agents/skills/godot-performance-guardian-docs/SKILL.md) skill instructs Codex to keep this README, `AGENT_TRAJECTORY.md`, and `IMPROVEMENT_CHANGELOG.md` synchronized with repository evidence. It is documentation tooling, not part of the runtime benchmark or planned investigation agent.

## 17. License

No license has been selected. Until a license is added, do not assume that the repository is distributed under MIT or another standard open-source license.
