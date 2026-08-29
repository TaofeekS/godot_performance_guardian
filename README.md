# Godot Performance Budget Guardian

## 1. Project overview

Godot Performance Budget Guardian combines a synthetic Godot 4.5 regression benchmark with a copyable runtime capture addon. It preserves raw per-frame evidence, validates calculated results, and applies project-specific budgets so developers can investigate changes instead of relying on a visual impression of performance.

## 2. Current status

| Status | Capability |
| --- | --- |
| Implemented and verified | Deterministic synthetic scenarios; a copyable `PerformanceBudgetProbe`; headless atomic JSON capture in an independent Godot 4.5.1 project; schema-specific deterministic validation; v1 scenario and v2 profile budgets; and a read-only investigator whose generic validation, grounding rejection, and deterministic fallback have been exercised locally and through live API requests. |
| Partially implemented | Generic policy covers seven aggregate engine metrics and has one tracked live fixture. Synthetic integrity assertions remain embedded in code, and the broader ten-fixture evaluation set is incomplete. |
| Unverified | No evaluated model has yet produced a generic report accepted directly by the grounding gate; live `gpt-4.1-mini`, `gpt-5.6-terra`, and `gpt-5.6-sol` responses all required deterministic fallback. Synthetic fallback behavior remains locally verified but not live-tested. |
| Planned | Nine additional evaluation fixtures, broader budget coverage, an editor dock, experimental repair and verification, categorized result packages, and the final hackathon submission workflow. |

This repository is a fresh synthetic project for the Micro1 Agentic Workflows Hackathon. It does not use unrelated private source code, private assets, or proprietary telemetry.

## 3. Intended user and problem

The intended user is a Godot developer or team maintaining a project where small code changes can gradually add per-frame work or leave objects alive. These regressions are difficult to notice manually: frame timing is noisy, leaks accumulate slowly, and a short interactive play session may still feel normal.

Repeatable scenarios and explicit limits make the same work measurable before and after a change. This complements Godot's profiler rather than replacing it. The profiler is an interactive inspection tool; this baseline produces machine-readable evidence and an objective process exit status that can eventually be used in automation.

## 4. Current baseline

The current baseline:

- Runs three deterministic synthetic scenarios with a fixed seed and fixed frame counts.
- Collects raw timing, memory, object, node, and scenario-owned measurements.
- Compares a multi-run result set against embedded data-integrity, cleanup, growth, and relative CPU assertions.
- Applies optional versioned project policy from `budgets/example_budgets.json` after deterministic validation, with a separate pass/fail exit status.
- Allows an unrelated project to copy `addons/performance_budget_guardian/`, add a probe node, capture generic engine metrics, validate them, and apply profile-based v2 budgets.
- Offers an optional investigator that can validate stored evidence and cite opaque IDs selected through semantic packet fields. A deterministic local gate blocks reports that violate its grounding contract and substitutes a fully cited fallback without another API request, but the investigator cannot prove root causes or modify the project.

It is a benchmark, portable capture/evaluation layer, and initial read-only reasoning layer, not yet the planned editor dock or automated repair product.

## 5. Repository structure

```text
.
|-- README.md
|-- AGENT_TRAJECTORY.md
|-- IMPROVEMENT_CHANGELOG.md
|-- requirements-agent.txt
|-- addons/
|   `-- performance_budget_guardian/
|       |-- plugin.cfg
|       |-- plugin.gd
|       |-- performance_probe.gd
|       `-- README.md
|-- budgets/
|   `-- example_budgets.json
|-- agent/
|   |-- __init__.py
|   `-- investigator.py
|-- tests/
|   |-- fixtures/
|   |   |-- generic_results/main_scene.json
|   |   |-- investigator/evidence_packet.json
|   |   `-- investigator/generic_evidence_packet.json
|   |-- test_check_budgets.py
|   |-- test_investigator.py
|   `-- test_portable_addon.py
|-- examples/
|   |-- fixtures/main_scene-godot-4.5.1.json
|   `-- minimal_project/
|       |-- budgets/performance_budgets.json
|       |-- project.godot
|       |-- main.tscn
|       |-- main.gd
|       `-- test_probe.gd
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
    |-- check_budgets.py
    `-- validate_results.py
```

- [`demo_project/project.godot`](demo_project/project.godot) defines the Godot 4.5 project and main scene.
- [`demo_project/scripts/benchmark_controller.gd`](demo_project/scripts/benchmark_controller.gd) implements scenario execution, measurement, summaries, cleanup, and atomic output.
- [`demo_project/scripts/test_actor.gd`](demo_project/scripts/test_actor.gd) implements the lightweight deterministic `Node2D` actors.
- [`demo_project/run_benchmarks.ps1`](demo_project/run_benchmarks.ps1) launches three isolated runs of each scenario and calls the validator.
- [`tools/validate_results.py`](tools/validate_results.py) validates schemas, calculations, cleanup evidence, leak growth, and relative CPU cost using only the Python standard library.
- [`tools/check_budgets.py`](tools/check_budgets.py) evaluates validated semantic evidence against a versioned project policy without AI or third-party packages.
- [`addons/performance_budget_guardian/performance_probe.gd`](addons/performance_budget_guardian/performance_probe.gd) is the reusable runtime capture node.
- [`examples/minimal_project/project.godot`](examples/minimal_project/project.godot) is the independent consumer project; it intentionally requires copying the addon into its ignored `addons/` directory.
- [`examples/fixtures/main_scene-godot-4.5.1.json`](examples/fixtures/main_scene-godot-4.5.1.json) is the sanitized canonical live capture.
- [`budgets/example_budgets.json`](budgets/example_budgets.json) demonstrates two passing limits and two intentionally failing regression limits.
- [`agent/investigator.py`](agent/investigator.py) defines the read-only OpenAI Agents SDK investigator and its sole restricted validator tool.
- [`tests/test_investigator.py`](tests/test_investigator.py) verifies the tool boundary, path containment, subprocess failures, configuration, and no-key behavior without an API request.
- [`tests/test_check_budgets.py`](tests/test_check_budgets.py) uses fixed evidence fixtures to verify configuration, semantic matching, deterministic output, and exit behavior.
- [`tests/test_portable_addon.py`](tests/test_portable_addon.py) verifies the addon contract, generic schema, evidence, and v2 budgets against tracked test fixtures.
- [`tests/fixtures/generic_results/main_scene.json`](tests/fixtures/generic_results/main_scene.json), [`tests/fixtures/investigator/evidence_packet.json`](tests/fixtures/investigator/evidence_packet.json), and [`tests/fixtures/investigator/generic_evidence_packet.json`](tests/fixtures/investigator/generic_evidence_packet.json) are small deterministic fixtures used by the default test suite.
- [`requirements-agent.txt`](requirements-agent.txt) pins the optional investigator and OpenAI SDK versions used by the clean test environment.
- [`AGENT_TRAJECTORY.md`](AGENT_TRAJECTORY.md) records the evidence-based history of the documentation task.
- [`IMPROVEMENT_CHANGELOG.md`](IMPROVEMENT_CHANGELOG.md) is the append-only product experiment record, beginning with the accepted current-state baseline.
- [`.agents/skills/godot-performance-guardian-docs/SKILL.md`](.agents/skills/godot-performance-guardian-docs/SKILL.md) defines the repository-local documentation workflow.

Godot-generated `.uid` files are present beside the GDScript sources. The `.godot/` cache and generated result JSON files are intentionally ignored.

## 6. Requirements

| Requirement | Current evidence |
| --- | --- |
| Godot | Exactly tested with `4.5.1.stable.official.f62fdbde1`. Other 4.5.x builds have not been verified. |
| Python | Python 3.14.6 was used successfully. The validator and budget checker use only the standard library; other Python versions have not been verified in this repository. |
| PowerShell | PowerShell 7.6.4 was used successfully for the batch harness. |
| Operating system | Windows 10.0.26200 is the only verified platform. Linux and macOS are unverified, and the supplied batch harness is PowerShell-specific. |
| Debug build | Not required for scenario execution. `Performance.MEMORY_STATIC` is accepted only when a debug build reports a positive value; otherwise memory samples are `null` and explicitly marked unavailable. |
| External dependencies | The benchmark needs only Godot, PowerShell for the batch harness, and Python's standard library for validation and budget policy. The optional investigator pins `openai-agents==0.22.0` and `openai==3.6.0`; OpenAI installs `httpx2` transitively, but repository tests do not import that transport package directly. |
| Network or API key | Benchmarking, addon capture, deterministic validation, and budget checking need neither. A live investigator run requires network access and `OPENAI_API_KEY`; local investigator tests do not. |

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

Emit the same validated set as the deterministic investigator evidence packet:

```powershell
python .\tools\validate_results.py --evidence-json .\demo_project\results
```

Apply the example project budget in human-readable mode:

```powershell
.\.venv\Scripts\python.exe .\tools\check_budgets.py `
  .\demo_project\results `
  .\budgets\example_budgets.json
```

Use canonical JSON output for CI or another deterministic consumer:

```powershell
.\.venv\Scripts\python.exe .\tools\check_budgets.py `
  --json `
  .\demo_project\results `
  .\budgets\example_budgets.json
```

The example intentionally returns exit code `1`: its healthy limits pass, while its CPU-spike and node-leak limits demonstrate policy failures. Exit code `0` means every configured budget passed; `1` means validation succeeded but at least one budget failed; `2` means configuration, evidence, validation, or execution was invalid.

Generated files are in `demo_project/results/`. They are local evidence and are ignored by Git.

### Portable addon example

Copy the canonical addon into the independent consumer project, then run its preconfigured probe:

```powershell
$GodotExe = "C:\path\to\Godot_v4.5.1-stable_win64.exe"
$RunId = "portable-" + (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssfffZ")

New-Item -ItemType Directory -Force .\examples\minimal_project\addons | Out-Null
Copy-Item -Recurse `
  .\addons\performance_budget_guardian `
  .\examples\minimal_project\addons\performance_budget_guardian

& $GodotExe `
  --headless `
  --path .\examples\minimal_project `
  -- `
  --pbg-profile=main_scene `
  --pbg-run-id=$RunId `
  --pbg-output=res://results `
  --pbg-auto-quit
```

The probe also accepts `--pbg-warmup-frames=<n>`, `--pbg-measured-frames=<n>`, `--pbg-sampling-interval=<n>`, and `--pbg-source-revision=<revision>`. Exported properties provide the same settings for editor use. Unknown addon arguments, unsafe profile/run IDs, invalid numbers, and paths outside `res://` are rejected. An existing explicit run ID is preserved and returns exit `3`; supply a new ID rather than deleting or overwriting evidence.

Validate and enforce the example's profile policy:

```powershell
.\.venv\Scripts\python.exe .\tools\validate_results.py `
  ".\examples\minimal_project\results\$RunId.json"

.\.venv\Scripts\python.exe .\tools\check_budgets.py `
  ".\examples\minimal_project\results\$RunId.json" `
  .\examples\minimal_project\budgets\performance_budgets.json
```

Capture files are versioned evidence. If validation reports an older addon version, copy the current addon and create a fresh capture with a new run ID; do not edit, delete, or overwrite the earlier JSON. Keep the same `$RunId` variable in the PowerShell session for capture, validation, and budget checking.

To use the addon elsewhere, copy the same directory to the target project's `res://addons/performance_budget_guardian/`, enable **Performance Budget Guardian** under Project Settings > Plugins, and add a `PerformanceBudgetProbe` node. To remove it, remove probe nodes, disable the plugin, and delete only that addon directory. The included example installation copy is ignored and can be removed with:

```powershell
Remove-Item -Recurse `
  .\examples\minimal_project\addons\performance_budget_guardian
```

Create a clean environment and run the complete default suite without generated benchmark results:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\requirements-agent.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

All default tests use tracked fixtures under `tests/fixtures/` or temporary directories. They do not read the ignored `demo_project/results/` directory. The 49 locally retained historical results are optional integration evidence and can be checked separately when present:

```powershell
.\.venv\Scripts\python.exe .\tools\validate_results.py .\demo_project\results
.\.venv\Scripts\python.exe .\tools\check_budgets.py `
  .\demo_project\results `
  .\budgets\example_budgets.json
```

The second command intentionally returns `1` for the two demonstration regressions. To install and run the optional read-only investigator in that environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements-agent.txt
$env:OPENAI_API_KEY = "<newly-issued-api-key>"
$env:OPENAI_MODEL = "gpt-4.1-mini" # Optional; this is the default.
.\.venv\Scripts\python.exe -m agent.investigator demo_project\results
```

Investigate portable generic captures with the same command and a profile-result directory. This tracked example performs the real deterministic validator step before the optional model response:

```powershell
.\.venv\Scripts\python.exe -m agent.investigator tests\fixtures\generic_results
```

The packet declares `evidence_kind` as `synthetic`, `generic`, or `failed`. Synthetic evidence uses `scenario`; generic evidence uses `profile`. The reserved generic profile `all` is validation-count metadata and is never reported as a project profile. Generic reports cite the packet's opaque IDs, such as `[G2]`, rather than depending on a fixed number.

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
| `WARNING: model output failed grounding (...)` | The API returned a report that violated one or more grounding rules. The rejected text is not printed; a deterministic cited fallback follows without another API request. |

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

The portable probe uses the same nearest-rank summaries and atomic output pattern but has a deliberately narrower meaning. It waits for configurable warmup and measurement frames, samples at the configured interval plus the final frame, and records only process time, physics time, static memory availability, and global object/node/orphan counts. It does not label probe overhead as workload time and does not claim scenario-owned cleanup evidence.

## 9. Scenarios

### Healthy

Maintains the fixed actor population and performs predictable arithmetic. Evidence cleanup must leave zero scenario-owned actors and zero retained nodes. Small engine-wide object or memory changes are tolerated because Godot and its allocator may perform bookkeeping outside scenario ownership.

### Node leak

Creates a temporary node every measured frame and intentionally retains one every five frames. The final measured frame and post-cleanup snapshot must contain exactly 120 scenario-owned retained nodes. Global node and object monitors should increase, while ordinary actors are still cleaned up. The retained nodes are freed only during final teardown.

### CPU spike

Runs the healthy actor lifecycle plus a fixed `240 x 240` nested numerical calculation every frame. Scenario-owned node counts must remain stable and no nodes may be retained. Its median per-run p95 `workload_time_usec` must be at least twice the healthy median; process time and total duration are supporting evidence.

### Generic project profiles

Addon captures use safe project-defined names such as `main_scene`, `battle_scene`, or `inventory_screen`; they are not synthetic scenarios. Generic validation checks metadata, sample ordering, units, and recalculated summaries without applying the demo's actor, leak, cleanup, or CPU-ratio assertions. Input directories may not mix generic and synthetic result types.

## 10. Performance budgets

Performance policy is stored in the versioned [`budgets/example_budgets.json`](budgets/example_budgets.json) schema. [`tools/check_budgets.py`](tools/check_budgets.py) first invokes the validator's structured mode through a fixed subprocess command, then matches evidence by metric, scenario, source type, and unit. Evidence IDs such as `E3` remain opaque traceability labels rather than configuration keys.

Each schema-version-1 rule has exactly `id`, `scenario`, `metric`, `maximum`, `unit`, and `description`. IDs must be unique and safe, descriptions must be nonempty, and limits must be finite nonnegative numbers. A measured value passes when it is equal to or below `maximum`.

| Metric | Scenarios | Unit |
| --- | --- | --- |
| `median_p95_workload_time` | `healthy`, `cpu_spike` | `usec` |
| `median_p95_process_time` | `healthy`, `cpu_spike` | `ms` |
| `median_scenario_duration` | `healthy`, `cpu_spike` | `ms` |
| `post_cleanup_retained_nodes` | `healthy`, `node_leak`, `cpu_spike` | `nodes` |

The included example has four rules. Its healthy process and cleanup rules are expected to pass the current evidence. Its CPU-spike workload and node-leak cleanup rules deliberately set limits that the regression scenarios exceed, demonstrating deterministic failure output. The absolute timing limits are examples for this machine, not universal Godot recommendations.

Budget schema v2 replaces `scenario` with `profile` and accepts only generic capture evidence. [`examples/minimal_project/budgets/performance_budgets.json`](examples/minimal_project/budgets/performance_budgets.json) contains the verified `main_scene` policy.

| Generic metric | Unit |
| --- | --- |
| `median_p95_process_time` | `ms` |
| `median_p95_physics_process_time` | `ms` |
| `median_measurement_duration` | `ms` |
| `median_peak_memory_static_bytes` | `bytes` |
| `median_peak_object_count` | `objects` |
| `median_peak_node_count` | `nodes` |
| `median_peak_orphan_node_count` | `nodes` |

The live example measured `0.529 ms` process p95 and three peak global nodes. Its timing maximum is `1.1 ms`, following the documented twice-observed, upward-rounded calibration rule; its node maximum is `3`. Both passed, but one machine and one run do not establish broadly reusable limits.

Because the probe accumulates raw samples during capture, static-memory growth includes probe storage overhead and cannot by itself prove a project memory leak. A `median_peak_memory_static_bytes` budget can flag a regression between comparable captures, but the captures should use identical measured-frame counts and sampling intervals.

Configurable policy is separate from benchmark validity. The following safety and integrity limits remain embedded in two places and are not overridden by a budget file:

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

When static memory is unavailable, `healthy_memory_growth_bytes` is `null` and memory validation is skipped explicitly. Changing these integrity assertions still requires coordinated controller and validator edits; the versioned policy checker intentionally consumes only evidence that already passed them.

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

Generic captures are explicitly distinguished. This abbreviated example comes from the tracked live fixture:

```json
{
  "result_type": "performance_budget_guardian_capture",
  "schema_version": 1,
  "addon": {"name": "Performance Budget Guardian", "version": "1.0.1"},
  "profile": "main_scene",
  "project_name": "Portable Performance Probe Example",
  "run_id": "portable-run-001",
  "source_revision": null,
  "headless": true,
  "warmup_frames": 120,
  "measured_frames": 600,
  "sampling_interval_frames": 1,
  "samples": [
    {
      "sample_index": 1,
      "measured_frame": 1,
      "process_time_ms": 0.0,
      "node_count": 3
    }
  ],
  "summary": {
    "measurement_duration_ms": 4140.02,
    "capture_duration_ms": 4949.63
  }
}
```

Its complete form includes UTC timestamps, sanitized configuration, memory availability, every global count, all 600 samples, timing/count summaries, environment metadata, and limitations. Because no revision was supplied, it explicitly states that the exact source revision is unknown.

Individual Godot result files are unchanged and contain no `budget_results` or structured `errors` property. The separate checker emits a deterministic result document in `--json` mode containing its schema version, overall status, validator metadata, per-rule measured and maximum values, matched opaque evidence IDs, summary counts, and preserved validator limitations. Human mode reports the same evaluation. Invalid arguments and operational errors go to stderr; policy failures remain valid output and return exit code `1`.

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

The optional investigator exposes that same program as its only function tool, `validate_benchmark_results`. The tool invokes the validator's `--evidence-json` mode, which returns a deterministic JSON-compatible packet containing explicit evidence kind, validation status, a repository-relative result directory, opaque evidence IDs, and explicit limitations. Synthetic packets contain scenario comparisons, cleanup evidence, and allowlisted controller behavior. Generic packets contain profile-scoped engine aggregates plus memory and source-revision availability. The normal validator command and human-readable output remain unchanged.

SDK configuration requires the tool on the first model turn and then allows a five-section report: Validation status, Verified facts, Possible explanations, Recommended next investigation, and Remaining uncertainty. Verified statements cite opaque packet IDs. Synthetic matching uses metric, scenario, source type, unit, and value shape. Generic matching uses metric, profile, source type, unit, and availability state. IDs may be renumbered without changing selection; missing, duplicate, mixed-identity, or malformed matches fail safely.

After generation, the schema-specific local gate checks section order, evidence references, supported numeric values, scenario or profile coverage, causal language, required limitations, the root-cause uncertainty statement, and read-only evidence-linked recommendations. Generic grounding additionally rejects invented unavailable-memory values, synthetic-only claims, revision values or equality claims, and private paths. When model output fails, the rejected text is not printed or stored. The CLI emits safe rule IDs and a five-section report beginning with:

```text
Report source: Deterministic fallback generated after model output failed grounding.
```

The fallback is generated only from the validated packet, is checked by the same gate, and does not cause another API request. It returns success when deterministic validation passed; validator failure remains nonzero. A validator pass means only that the configured assertions passed, not that the project has no other performance issue.

For generic profiles, the fallback covers process and physics-process p95, measurement duration, peak object/node/orphan counts, and peak static memory when available. It says `unavailable` or `mixed` when memory cannot support an aggregate. Revision metadata is reported only as `present`, `unknown`, or `mixed`: present means every contributing capture supplied some value, unknown means none did, and mixed means only some did. Revision values are never emitted, compared, or claimed equal. Every generic limitation is preserved, including global-monitor ownership, engine/probe timing overhead, headless GPU limits, and probe sample-storage memory overhead.

Experiment 3 local verification on 2026-08-29 ran 32 standard-library unit tests without an API request and passed all 21 JSON files in `demo_project/results/`. The deterministic packet records healthy and CPU-spike median p95 workload times of 148 µs and 8,549 µs, a 57.76× ratio, process medians of 0.408 ms and 12.5885 ms, median durations of 4,976.010 ms and 6,406.270 ms, and a correctly calculated duration increase of approximately 28.7%. It also records 120 retained nodes in every node-leak run and zero in every healthy and CPU-spike run.

The expanded result directory contains nine healthy runs, six node-leak runs, and six CPU-spike runs. Its CPU-spike files mix three historical `160 x 160` runs with three `240 x 240` runs. The packet therefore labels the 21-file aggregate as descriptive rather than a single controlled-configuration comparison. Stored result files also lack a source revision/hash, so current allowlisted controller evidence cannot prove the exact source revision used for every historical file. This safety check does not replace or revise the accepted nine-file Baseline 0.

The pre-Experiment-3 live report was useful enough to reproduce the principal timing measurements, but it omitted node-leak evidence, misstated the duration increase as about 25%, and introduced unsupported possible causes. Those observations are the “before” evaluation. Because no API key was configured during the implementation verification, the new grounding behavior has been exercised through fixed report fixtures and mocks only; post-change live report quality remains unverified.

Experiment 4 followed a real post-change live rejection containing `G03`, `G04`, `G07`, `G08`, `G11`, and `G13`. Local verification ran 39 tests without an API request. The tests prove that renumbered evidence still passes, unrelated evidence is ignored, missing or duplicate semantic evidence fails safely, rejected model text is never emitted, the SDK runner is called once, and a grounded fallback is returned successfully when validation passed.

At Experiment 4 verification time, the result directory contained 31 validated files: 13 healthy, nine node-leak, and nine CPU-spike runs. That aggregate was healthy/CPU-spike median p95 workload of 163 µs/11,510 µs (70.61×), process p95 of 0.605 ms/12.537 ms, and duration of 4,976.010 ms/7,285.752 ms. Every leak run retained 120 nodes; healthy and CPU-spike retained zero. The CPU results mixed three `160 x 160` and six `240 x 240` configurations, so it remained a regression-safety set rather than a new controlled baseline.

Experiment 5 added configurable policy without changing those stored results or validator calculations. Local verification ran 57 standard-library tests. The unchanged validator passed the current 40-file directory. The example policy produced exactly two passes (`healthy-process-p95`, `healthy-retained-nodes`) and two intentional failures (`cpu-spike-workload-p95`, `node-leak-retained-nodes`), returned exit code `1`, and produced byte-identical canonical JSON in two invocations. This 40-file aggregate mixes historical configurations and is integration evidence, not a replacement for Baseline 0.

Experiment 6 verification finished with 66 passing tests and exercised Godot `4.5.1.stable.official.f62fdbde1`. The addon copy parsed and its helper tests returned `0`; one live `main_scene` capture produced 600 samples and validated with exit `0`. Its two calibrated v2 budgets passed with exit `0`. An explicit collision returned `3` and left the capture byte-identical. All 49 historical synthetic results still validated with exit `0`, while the unchanged Experiment 5 policy returned its expected `1`. Generic evidence and budget JSON were byte-identical across repeated invocations.

After addon `1.0.1` made the raw-sample memory limitation mandatory, the earlier ignored `1.0.0` runtime file correctly failed with an actionable recapture diagnostic. A new uniquely identified `1.0.1` capture produced 600 samples, process p95 `0.951 ms`, and three peak nodes; it validated and passed both existing v2 budgets. The complete suite then passed 68 tests. The earlier file remained byte-identical, demonstrating that upgrades preserve historical evidence rather than rewriting it.

The clean-environment audit exported only the staged Git index into a temporary directory, created a fresh Python 3.14 virtual environment, installed only `requirements-agent.txt`, and confirmed `pip check` plus all 68 tests passed. The export contained neither the repository `.venv` nor ignored `demo_project/results/` files. The tracked canonical portable fixture was reevaluated separately: process p95 `0.529 ms <= 1.1 ms` and peak nodes `3 <= 3`, so validation and both v2 budgets returned `0`. As an optional local integration check, all 49 ignored historical results validated, while the Experiment 5 demonstration policy returned its expected `1` with only the CPU-spike workload and node-leak retention rules failing.

Experiment 7 locally verified synthetic/generic packet dispatch, multi-profile grounding, reserved-`all` exclusion, unavailable and mixed memory, all three revision-availability states, opaque-ID renumbering, deterministic fallback, rejected-output suppression, and one-runner-call behavior. The complete suite passed 86 tests. The tracked generic packet was byte-identical across two generations, both synthetic and generic fallback fixtures passed their respective gates, the canonical v2 budgets remained `0.529 ms <= 1.1 ms` and `3 <= 3`, and all 49 historical synthetic results retained their prior outcomes.

Experiment 8 then used the same tracked `main_scene` fixture for one live `gpt-5.6-terra` evaluation and, after Terra failed direct grounding, one conditional `gpt-5.6-sol` evaluation. Terra failed six grounding rules and Sol failed seven; each CLI run returned `0` only after suppressing the rejected model text and producing a grounded deterministic fallback without another application invocation. Neither candidate met the one-clean-pass adoption rule, so `gpt-4.1-mini` remains the default and `OPENAI_MODEL` remains the explicit override. The post-evaluation local suite passed all 86 tests. These two observations compare single nondeterministic responses, not general model quality.

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
- Portable-probe static-memory growth includes the probe's accumulating raw-sample storage and cannot by itself prove a project memory leak.
- Evidence focuses on CPU work and object/node growth, not rendering or GPU performance.
- Configurable policy supports four synthetic metrics and seven generic engine metrics; the validator's synthetic integrity assertions and controller tolerances remain embedded in code.
- There is no committed golden baseline or baseline/iteration/final result organization.
- There is no reusable editor dock or repair workflow. The investigator receives only validator-produced synthetic or generic evidence and cannot establish root cause by itself.
- Live generic responses from `gpt-4.1-mini`, `gpt-5.6-terra`, and `gpt-5.6-sol` were rejected by the gate; the deterministic generic fallback recovered each invocation. One response per candidate is insufficient to rank general model quality.
- The current 49-file aggregate mixes historical `160 x 160` and `240 x 240` CPU workloads, and stored results do not identify their source revision.
- Portable capture is verified only for the included independent project on Godot 4.5.1. One tracked capture and its calibrated policy do not prove universal project, platform, or timing compatibility.
- Windows is the only verified operating system; the harness is PowerShell-specific.
- Individual result JSON does not contain a consolidated budget verdict or structured error object.

## 15. Roadmap

| Stage | Status | Intended outcome |
| --- | --- | --- |
| 1. Deterministic baseline | Completed | Three synthetic scenarios, raw samples, summaries, repeated runs, and objective validation. |
| 2. Configurable budgets | Completed (v1/v2) | Apply scenario or profile policies to validated evidence with deterministic human/JSON output and CI exit codes. |
| 3. Ten evaluation fixtures | Partial | One sanitized live generic fixture is tracked; nine broader objective fixtures remain planned. |
| 4. Reusable Godot editor dock | Partial | A copyable runtime probe and editor-registered node exist; an interactive dock is still planned. |
| 5. Agent-assisted investigation | Partial | A read-only command-line investigator handles synthetic scenarios and generic profiles, blocks ungrounded reports, and has recovered live generic failures with deterministic fallbacks; no tested model has yet passed generic grounding directly. |
| 6. Temporary experimental fixes and verification | Planned | Apply isolated candidate changes and rerun the same evidence. |
| 7. Final baseline comparison and submission package | Planned | Package selected baseline, iteration, and final evidence with hackathon documentation. |

## 16. Hackathon evidence

- [`AGENT_TRAJECTORY.md`](AGENT_TRAJECTORY.md) is the chronological audit of documentation and investigator implementation tasks: requests, decisions, inspections, edits, issues, and verification.
- [`IMPROVEMENT_CHANGELOG.md`](IMPROVEMENT_CHANGELOG.md) is the append-only product experiment record. It establishes Baseline 0 and records the investigator, configurable-budget, portable-capture, generic-investigator, and model-upgrade experiments.
- Generated benchmark evidence currently exists locally beneath `demo_project/results/` and is ignored by Git.
- The sanitized [`main_scene` generic capture](examples/fixtures/main_scene-godot-4.5.1.json) is tracked as the first portable integration fixture.
- Dedicated versioned baseline, iteration, and final result packages are planned and do not yet exist.

The trajectory explains how an agent performed work. The improvement changelog explains how the product changes across evidence-backed experiments, including unsuccessful or removed approaches.

### Documentation skill

The repository-local [`godot-performance-guardian-docs`](.agents/skills/godot-performance-guardian-docs/SKILL.md) skill instructs Codex to keep this README, `AGENT_TRAJECTORY.md`, and `IMPROVEMENT_CHANGELOG.md` synchronized with repository evidence. It is documentation tooling, not part of the runtime benchmark or planned investigation agent.

## 17. License

No license has been selected. Until a license is added, do not assume that the repository is distributed under MIT or another standard open-source license.
