# Godot Performance Budget Guardian

## 1. Project overview

Godot Performance Budget Guardian combines a synthetic Godot 4.5 regression benchmark with a copyable runtime capture addon and read-only editor evidence workspace. It preserves raw per-frame evidence, validates calculated results, and applies project-specific budgets so developers can investigate changes instead of relying on a visual impression of performance.

## Judge reproduction

This is the shortest verified path for reproducing the project's deterministic gate and main synthetic benchmark from a clean Windows checkout. The more detailed setup and usage instructions remain in the numbered sections below.

### 1. Required software

- Git.
- Godot `4.5.1.stable.official.f62fdbde1`.
- Python `3.14.6`.
- PowerShell `7.6.4`.
- Windows `10.0.26200`. Other operating systems have not been verified for this repository.

Clone the public repository and enter it:

```powershell
git clone https://github.com/TaofeekS/godot_performance_guardian.git
Set-Location .\godot_performance_guardian
```

### 2. Create the Python environment

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\requirements-agent.txt
.\.venv\Scripts\python.exe -m pip check
```

Package installation requires internet access. The deterministic gate, tests, and benchmark below do not require an OpenAI API key and incur no API cost.

### 3. Demonstrate a passing gate

```powershell
.\.venv\Scripts\python.exe .\tools\run_guardian.py `
  --json `
  --investigate never `
  .\tests\fixtures\generic_results `
  .\examples\minimal_project\budgets\performance_budgets.json
```

Expected result: exit `0`, `deterministic_status` is `passed`, and both tracked budgets pass (`0.5 ms <= 1.1 ms` process p95 and `3 <= 3` peak nodes).

### 4. Reproduce the final baseline comparison

```powershell
.\.venv\Scripts\python.exe .\tools\run_submission_evaluation.py --json
```

Expected result: exit `0`, Baseline 0 completes `1/10` correct actionable outcomes, the final product completes `10/10`, and the recorded change is `+90` percentage points. See [`FINAL_EVALUATION.md`](FINAL_EVALUATION.md) for the rubric, complete case table, fairness statement, and limitations.

The integrity manifest hashes canonical UTF-8 text after normalizing CRLF and lone CR line endings to LF. This preserves substantive SHA-256 integrity checks while making the command independent of Git's checkout line-ending policy.

### 5. Run all tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected result: exit `0` after running 223 tests. Two environment-dependent directory-symlink tests may be reported as skipped when Windows does not permit symlink creation.

### 6. Produce fresh Godot measurements

Point `$Godot` at the downloaded Godot 4.5.1 executable, then run the complete benchmark harness:

```powershell
$Godot = "C:\path\to\Godot_v4.5.1-stable_win64.exe"

.\demo_project\run_benchmarks.ps1 `
  -GodotExecutable $Godot `
  -PythonExecutable .\.venv\Scripts\python.exe
```

The harness runs `healthy`, `node_leak`, and `cpu_spike` three times each, writes nine fresh JSON files under `demo_project/results/`, and validates exactly those files. A successful run exits `0` after printing `Validating 9 result files` and `Benchmark suite passed`. Allow approximately one minute on hardware comparable to the verified machine; timing varies by host.

For deterministic policy commands, exit `0` means validation and all applicable budgets passed, exit `1` means valid evidence failed at least one budget, and exit `2` means configuration, validation, evidence, or operational failure.

For a real consumer integration, see the public [PluginTest example](https://github.com/TaofeekS/PluginTest), including its Godot scene, project policy, and reusable-workflow caller.

## 2. Current status

| Status | Capability |
| --- | --- |
| Implemented and verified | Deterministic synthetic scenarios; a copyable `PerformanceBudgetProbe`; a read-only Godot main-screen evidence workspace verified through Godot 4.5.1 helper/editor-lifecycle checks and a user-completed PluginTest visual walkthrough; repeated headless capture in local and GitHub-hosted consumer workspaces; schema-specific deterministic validation; v1 scenario, v2 profile, and v3 paired-comparison budgets; a deterministic five-run calibration assistant verified locally; a unified standard-library gate; a reusable consumer workflow; actionable GitHub log/annotation rendering plus successful hosted summary-file writing; a ten-case Baseline 0/final evaluation package; and a read-only investigator whose typed contribution, grounding, and fallback paths have been exercised locally and through live API requests. |
| Partially implemented | Generic policy covers seven aggregate engine metrics and has one tracked live capture. The ten-case competition evaluation covers deterministic workflow behavior with fixed fixtures, not ten independent real games or GPU workloads, and synthetic integrity assertions remain embedded in code. |
| Unverified | Direct visual inspection of the hosted custom job-summary body remains unavailable from the current automation environment. Synthetic fallback behavior remains locally verified but not live-tested. |
| Planned | Broader real-project, multi-scene, and GPU evaluation; experimental repair and verification; and final submission assembly. |

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
- Runs validation and budget policy through one deterministic `run_guardian.py` command suitable for local use or CI, with optional post-decision AI explanation.
- Provides a reusable Windows workflow that installs Godot, captures a consumer scene three times, validates fresh generic evidence, enforces a v2 or v3 policy, and always uploads the evidence bundle.
- Optionally compares three protected-base captures with three pull-request candidate captures under a base-controlled schema-v3 policy on the same runner.
- Generates a reviewable schema-v3 proposal from at least three validated generic captures; hosted calibration defaults to five and never edits or enforces policy automatically.
- Allows an unrelated project to copy `addons/performance_budget_guardian/`, add a probe node, capture generic engine metrics, validate them, and apply profile-based v2 budgets.
- Adds a read-only Godot main-screen workspace that reports active-scene probe readiness, presents recent project-contained captures and canonical reports, and lists deterministic failed rules without running or reimplementing the gate.
- Offers an optional investigator that can validate stored evidence and cite opaque IDs selected through semantic packet fields. A deterministic local gate blocks reports that violate its grounding contract and substitutes a fully cited fallback without another API request, but the investigator cannot prove root causes or modify the project.

It is a benchmark, portable capture/evaluation layer, read-only editor evidence surface, and initial read-only reasoning layer, not an automated repair product.

## 5. Repository structure

```text
.
|-- .github/workflows/performance-guardian.yml
|-- .github/workflows/reusable-performance-guardian.yml
|-- LICENSE
|-- README.md
|-- FINAL_EVALUATION.md
|-- AGENT_EVALUATION.md
|-- AGENT_TRAJECTORY.md
|-- IMPROVEMENT_CHANGELOG.md
|-- requirements-agent.txt
|-- addons/
|   `-- performance_budget_guardian/
|       |-- plugin.cfg
|       |-- plugin.gd
|       |-- evidence_reader.gd
|       |-- performance_guardian_main_screen.gd
|       |-- performance_probe.gd
|       `-- README.md
|-- budgets/
|   `-- example_budgets.json
|-- evaluation/
|   |-- baseline/validate_results.py
|   |-- agent/{config,cases,integrity,packets,prompts,results}/
|   |-- fixtures/{synthetic,generic,comparison,malformed,budgets}/
|   |-- cases.json
|   |-- integrity.json
|   `-- results/final-evaluation.json
|-- agent/
|   |-- __init__.py
|   `-- investigator.py
|-- tests/
|   |-- fixtures/
|   |   |-- comparison/{baseline,candidate,regression}/main_scene.json
|   |   |-- comparison/performance_budgets.json
|   |   |-- generic_results/main_scene.json
|   |   |-- editor_dock/*.json
|   |   |-- investigator/evidence_packet.json
|   |   |-- investigator/generic_evidence_packet.json
|   |   `-- investigator/comparison_evidence_packet.json
|   |-- test_comparison.py
|   |-- test_editor_main_screen.py
|   |-- test_calibrate_budgets.py
|   |-- test_check_budgets.py
|   |-- test_investigator.py
|   |-- test_portable_addon.py
|   |-- test_action_report.py
|   |-- test_run_guardian.py
|   |-- test_submission_evaluation.py
|   |-- test_agent_evaluation.py
|   `-- test_capture_project.py
|-- examples/
|   |-- fixtures/main_scene-godot-4.5.1.json
|   `-- minimal_project/
|       |-- budgets/performance_budgets.json
|       |-- budgets/comparison_budgets.json
|       |-- project.godot
|       |-- main.tscn
|       |-- main.gd
|       |-- test_probe.gd
|       `-- test_editor_main_screen.gd
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
    |-- capture_project.py
    |-- calibrate_budgets.py
    |-- check_budgets.py
    |-- comparison_evidence.py
    |-- render_action_report.py
    |-- run_guardian.py
    |-- run_agent_evaluation.py
    |-- run_submission_evaluation.py
    |-- validate_results.py
    `-- workspace_paths.py
```

- [`demo_project/project.godot`](demo_project/project.godot) defines the Godot 4.5 project and main scene.
- [`demo_project/scripts/benchmark_controller.gd`](demo_project/scripts/benchmark_controller.gd) implements scenario execution, measurement, summaries, cleanup, and atomic output.
- [`demo_project/scripts/test_actor.gd`](demo_project/scripts/test_actor.gd) implements the lightweight deterministic `Node2D` actors.
- [`demo_project/run_benchmarks.ps1`](demo_project/run_benchmarks.ps1) launches three isolated runs of each scenario and calls the validator.
- [`tools/validate_results.py`](tools/validate_results.py) validates schemas, calculations, cleanup evidence, leak growth, and relative CPU cost using only the Python standard library.
- [`tools/check_budgets.py`](tools/check_budgets.py) evaluates validated semantic evidence against a versioned project policy without AI or third-party packages.
- [`tools/calibrate_budgets.py`](tools/calibrate_budgets.py) turns repeated validated generic captures into a deterministic schema-v3 proposal and applies it only through a separate explicit command.
- [`tools/comparison_evidence.py`](tools/comparison_evidence.py) emits schema-v2 comparison evidence for the optional investigator without exposing revision values.
- [`tools/render_action_report.py`](tools/render_action_report.py) turns canonical gate JSON into safe GitHub logs, annotations, and a Markdown job summary without changing the verdict.
- [`tools/run_guardian.py`](tools/run_guardian.py) loads policy, runs one validator call for absolute mode or exactly two for paired mode, applies existing budget semantics, and optionally launches the investigator without changing deterministic exits.
- [`tools/run_submission_evaluation.py`](tools/run_submission_evaluation.py) verifies canonical UTF-8/LF hashes for the frozen evaluation package and scores Baseline 0 and the final product against the same ten deterministic case oracles.
- [`tools/run_agent_evaluation.py`](tools/run_agent_evaluation.py) runs or locally re-grades the frozen twenty-run typed-versus-free-form investigator evaluation with a total cost ceiling, zero retries, disabled tracing, and rejected-text suppression.
- [`tools/capture_project.py`](tools/capture_project.py) preflights a consumer project and runs isolated, collision-safe Godot captures with sanitized logs and a canonical manifest.
- [`tools/workspace_paths.py`](tools/workspace_paths.py) centralizes symlink-aware containment for explicit consumer workspaces.
- [`.github/workflows/performance-guardian.yml`](.github/workflows/performance-guardian.yml) runs the tracked fixture and policy on pull requests to `main` and through manual dispatch.
- [`.github/workflows/reusable-performance-guardian.yml`](.github/workflows/reusable-performance-guardian.yml) is the callable consumer-project capture and gate workflow.
- [`addons/performance_budget_guardian/performance_probe.gd`](addons/performance_budget_guardian/performance_probe.gd) is the reusable runtime capture node.
- [`addons/performance_budget_guardian/performance_guardian_main_screen.gd`](addons/performance_budget_guardian/performance_guardian_main_screen.gd) implements the read-only probe/evidence workspace; [`evidence_reader.gd`](addons/performance_budget_guardian/evidence_reader.gd) supplies bounded, schema-specific parsing and ordering.
- [`examples/minimal_project/project.godot`](examples/minimal_project/project.godot) is the independent consumer project; it intentionally requires copying the addon into its ignored `addons/` directory.
- [`examples/fixtures/main_scene-godot-4.5.1.json`](examples/fixtures/main_scene-godot-4.5.1.json) is the sanitized canonical live capture.
- [`budgets/example_budgets.json`](budgets/example_budgets.json) demonstrates two passing limits and two intentionally failing regression limits.
- [`agent/investigator.py`](agent/investigator.py) defines the read-only OpenAI Agents SDK investigator and its sole restricted validator tool.
- [`tests/test_investigator.py`](tests/test_investigator.py) verifies the tool boundary, path containment, subprocess failures, configuration, and no-key behavior without an API request.
- [`tests/test_check_budgets.py`](tests/test_check_budgets.py) uses fixed evidence fixtures to verify configuration, semantic matching, deterministic output, and exit behavior.
- [`tests/test_portable_addon.py`](tests/test_portable_addon.py) verifies the addon contract, generic schema, evidence, and v2 budgets against tracked test fixtures.
- [`tests/test_editor_main_screen.py`](tests/test_editor_main_screen.py) verifies the exact Godot 4.5 main-screen lifecycle, read-only boundary, evidence fixtures, containment, and timestamp policy.
- [`tests/test_run_guardian.py`](tests/test_run_guardian.py) verifies orchestration, containment, exit preservation, output stability, optional-investigation safety, and the workflow contract without an API request.
- [`tests/test_submission_evaluation.py`](tests/test_submission_evaluation.py) verifies frozen-fixture integrity, all ten case oracles, score recomputation, subprocess safety, canonical stability, and evaluator exits.
- [`tests/test_agent_evaluation.py`](tests/test_agent_evaluation.py) verifies frozen agent packets, cost accounting, the two-turn token boundary, failed-rule grading, fallbacks, atomic output, and API-free result re-grading.
- [`tests/test_capture_project.py`](tests/test_capture_project.py) verifies isolated capture commands, collisions, stop-on-failure, sanitized manifests/logs, and the reusable workflow contract.
- [`tests/test_calibrate_budgets.py`](tests/test_calibrate_budgets.py) verifies calibration formulas, semantic evidence, safe IDs, atomic output, explicit replacement, and deterministic reports.
- [`tests/test_comparison.py`](tests/test_comparison.py) verifies schema v3, paired semantic matching, zero baselines, deterministic comparison evidence, and exits.
- [`tests/fixtures/generic_results/main_scene.json`](tests/fixtures/generic_results/main_scene.json), [`tests/fixtures/investigator/evidence_packet.json`](tests/fixtures/investigator/evidence_packet.json), and [`tests/fixtures/investigator/generic_evidence_packet.json`](tests/fixtures/investigator/generic_evidence_packet.json) are small deterministic fixtures used by the default test suite.
- [`requirements-agent.txt`](requirements-agent.txt) pins the optional investigator and OpenAI SDK versions used by the clean test environment.
- [`AGENT_TRAJECTORY.md`](AGENT_TRAJECTORY.md) records the evidence-based history of the documentation task.
- [`IMPROVEMENT_CHANGELOG.md`](IMPROVEMENT_CHANGELOG.md) is the append-only product experiment record, beginning with the accepted current-state baseline.
- [`FINAL_EVALUATION.md`](FINAL_EVALUATION.md) is the judge-facing Baseline 0/final comparison, backed by the tracked [`evaluation/results/final-evaluation.json`](evaluation/results/final-evaluation.json) result.
- [`AGENT_EVALUATION.md`](AGENT_EVALUATION.md) is the controlled ten-packet comparison of the shipped grounded typed investigator with a matched free-form baseline, backed by the tracked [`agent-evaluation.json`](evaluation/agent/results/agent-evaluation.json).
- [`.agents/skills/godot-performance-guardian-docs/SKILL.md`](.agents/skills/godot-performance-guardian-docs/SKILL.md) defines the repository-local documentation workflow.

Godot-generated `.uid` files are present beside the GDScript sources. The `.godot/` cache and generated result JSON files are intentionally ignored.

## 6. Requirements

| Requirement | Current evidence |
| --- | --- |
| Godot | Exactly tested with `4.5.1.stable.official.f62fdbde1`. Other 4.5.x builds have not been verified. |
| Python | Python 3.14.6 was used successfully. The validator, budget checker, and unified runner use only the standard library; other Python versions have not been verified in this repository. |
| PowerShell | PowerShell 7.6.4 was used successfully for the batch harness. |
| Operating system | Windows 10.0.26200 is the only verified platform. Linux and macOS are unverified, and the supplied batch harness is PowerShell-specific. |
| Debug build | Not required for scenario execution. `Performance.MEMORY_STATIC` is accepted only when a debug build reports a positive value; otherwise memory samples are `null` and explicitly marked unavailable. |
| External dependencies | The benchmark needs only Godot, PowerShell for the batch harness, and Python's standard library for validation and budget policy. The optional investigator pins `openai-agents==0.22.0` and `openai==3.6.0`; OpenAI installs `httpx2` transitively, but repository tests do not import that transport package directly. |
| Network or API key | Benchmarking, addon capture, deterministic validation, and budget checking need neither. GitHub Actions needs network access to obtain actions and Godot. A live investigator run additionally requires `OPENAI_API_KEY`; local investigator tests do not. |

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

Run the tracked generic fixture through the unified local/CI gate:

```powershell
.\.venv\Scripts\python.exe .\tools\run_guardian.py `
  --investigate never `
  .\tests\fixtures\generic_results `
  .\examples\minimal_project\budgets\performance_budgets.json
```

Add `--json` for canonical compact JSON. Investigation defaults to `never`; `on-failure` runs the investigator once only after valid evidence exceeds a budget, and `always` runs it once after any successful deterministic validation. A missing key, API failure, timeout, malformed report, accepted report, or deterministic fallback never changes the authoritative deterministic exit. Configuration or validator failure returns `2` and never launches the investigator.

Human output has four sections: `Validation result`, `Budget result`, `Optional investigator explanation`, and `Final authoritative exit reason`. JSON records the validator counts, budget summary and evidence-linked rule results, investigation mode/outcome, optional safe report, and `authoritative_exit_code`. Only a recognized grounded typed report or recognized deterministic fallback can populate the report field; rejected model output is suppressed.

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

### Editor evidence workspace

Addon `1.2.0` adds a **Guardian** button beside Godot's 2D, 3D, Script, Game, and AssetLib workspaces when the editor plugin is enabled. Select it to open the full central **Performance Guardian** evidence page; switching back restores the normal editor workspace and leaves the Inspector, Node, and FileSystem docks untouched. It is deliberately read-only: it does not run a capture, Python, validation, budgets, GitHub Actions, network access, or AI. It shows all probe nodes in the active scene, their frame/output configuration and readiness, the latest matching capture, up to 20 recent recognized evidence files, invalid-file warnings, deterministic failed rules, and calibration proposals labeled as non-authoritative.

The workspace scans each probe's configured `res://` output, `res://results`, and `res://.performance-guardian`. **Add evidence** can include another JSON file for the current editor session, but the file must remain under `res://`; absolute paths, traversal, and traversed links are rejected. **Locate** selects visible evidence in Godot's FileSystem dock, while **Copy res:// path** copies only the portable project path.

Evidence time is schema-specific. Generic capture schema v1 requires canonical `ended_at_utc` and is ordered newest first by that field. Guardian report schemas v1/v2 and calibration report schema v1 currently contain no canonical report-generation timestamp, so the workspace never substitutes filesystem modification time: those valid reports follow timestamped captures and sort by report type plus normalized `res://` path. A capture with a missing or invalid `ended_at_utc` is invalid. Failed rules are displayed only from canonical Guardian reports; raw captures remain **Not evaluated**, and the workspace never duplicates policy calculation.

Historical `1.0.1` and `1.1.0` captures remain compatible because their capture schema and mandatory memory limitation are unchanged. New captures identify addon `1.2.0`; version `1.0.0` remains unsupported and requires a fresh capture rather than metadata editing.

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

The validator packet declares `evidence_kind` as `synthetic`, `generic`, or `failed`; paired policy evaluation produces packet schema v2 with `evidence_kind: comparison`. Synthetic evidence uses `scenario`; generic and comparison evidence use `profile`. The reserved generic profile `all` is validation-count metadata and is never reported as a project profile. Reports cite opaque packet IDs rather than depending on fixed numbering. Comparison packets contain semantic baseline/candidate values and policy status but never reveal or compare source-revision values.

The key is read only from the process environment. Do not place it in source files, command logs, `.env` files intended for commit, or documentation. The argument must be a repository-relative directory containing result JSON files. Absolute paths, missing directories, paths outside the repository, and directories without JSON results are rejected before any API request.

### GitHub Actions gate

The `Performance Guardian` workflow runs on pull requests targeting `main` and on manual dispatch. Its independent `repository-tests` job installs `requirements-agent.txt`, runs `pip check`, and runs the complete suite. Its separate `performance-guardian` job evaluates the tracked generic fixture and v2 policy through `run_guardian.py`, so a test failure cannot suppress the deterministic report. Pull requests always use `--investigate never`, so they need no credential and make no API request.

Manual dispatch exposes `never`, `on-failure`, and `always`. To enable the optional modes, configure an Actions repository secret named `OPENAI_API_KEY`; an optional repository variable named `OPENAI_MODEL` overrides the default `gpt-4.1-mini`. The secret is scoped only to the manual gate step. The workflow writes canonical JSON beneath the runner's temporary directory, preserves the Python exit status, and uploads `performance-guardian-report` with `if: always()`, including deterministic failures. [Hosted run 33336400657](https://github.com/TaofeekS/godot_performance_guardian/actions/runs/33336400657) verified both independent jobs and the report artifact on Windows for commit `fe72c6083c44a5323523d066e0ef9a7f4b308caf`.

### Turnkey CI for another Godot project

Installing the addon does not automatically enable CI. A consumer repository must commit `addons/performance_budget_guardian/`, add an automatically starting `PerformanceBudgetProbe` to the measured scene, commit a schema-v2 or schema-v3 profile budget, ignore `.performance-guardian/`, and add a small caller workflow. Pin the Guardian reusable workflow to an immutable commit SHA:

```yaml
name: Game performance

on:
  pull_request:

jobs:
  performance:
    uses: TaofeekS/godot_performance_guardian/.github/workflows/reusable-performance-guardian.yml@fe72c6083c44a5323523d066e0ef9a7f4b308caf
    with:
      project-path: .
      profile: main_scene
      budget-file: budgets/performance_budgets.json
```

`project-path` and `profile` are always required. `budget-file` is optional in the reusable-workflow schema only because calibration does not enforce a policy; it remains required in the default `enforce` mode. Other inputs are:

| Input | Default | Meaning |
| --- | --- | --- |
| `mode` | `enforce` | `enforce` applies policy; `calibrate` creates a proposal only. |
| `budget-file` | Empty | Required for `enforce`; unused by `calibrate`. |
| `scene-path` | Project main scene | Optional `res://` scene containing the probe. |
| `godot-version` | `4.5.1` | Godot version installed by the pinned setup action. |
| `use-dotnet` | `false` | Select the .NET Godot build. |
| `warmup-frames` | `120` | Frames before measurement. |
| `measured-frames` | `600` | Measured frames per run. |
| `sampling-interval` | `1` | Frames between samples; the final frame is always sampled. |
| `capture-runs` | `3` | Isolated Godot processes. |
| `calibration-runs` | `5` | Isolated captures used only in `calibrate` mode. |
| `compare-with-base` | `false` | On a pull request, capture and compare the protected base under its schema-v3 policy. |
| `investigate` | `never` | `never`, `on-failure`, or `always`. |
| `openai-model` | `gpt-4.1-mini` | Optional investigator override. |

The optional reusable-workflow secret is `openai-api-key`. Pass it only when AI is requested:

```yaml
    secrets:
      openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

Mode `never` does not install the Agents SDK, inspect the key, or launch the investigator. The workflow checks out Guardian tooling at `job.workflow_repository` and `job.workflow_sha`, matching the exact called workflow revision. Godot installation uses `chickensoft-games/setup-godot` pinned to commit `f166999204a4f2722c6fe042fbaa3b3ea0d9c789` (`v2.4.1`).

### Calibrate a consumer budget

Calibration is deliberately separate from enforcement. It validates repeated generic captures, proposes three schema-v3 rules, and exits `0` only after safely writing both proposal files. It does not invoke AI, decide a build verdict, edit an existing policy, or enable comparison.

Local generation requires at least three captures:

```powershell
python tools/calibrate_budgets.py `
  --workspace-root . `
  --json `
  --policy-output .performance-guardian/proposed-performance-budgets.json `
  --report-output .performance-guardian/calibration-report.json `
  .performance-guardian/main_scene/<run-prefix>/captures
```

The balanced preset proposes:

- Process p95: observed median multiplied by `1.50`, rounded upward to `0.1 ms`, with a `20%` comparison allowance.
- Peak global nodes: observed median multiplied by `1.10` and rounded upward to an integer, with a `5%` comparison allowance.
- Peak global objects: the same `1.10` integer ceiling and `5%` comparison allowance.

Review the generated JSON before applying it. A missing target may be created directly; replacing an existing policy requires the additional `--replace` acknowledgement:

```powershell
python tools/calibrate_budgets.py `
  --workspace-root . `
  --apply-proposal .performance-guardian/proposed-performance-budgets.json `
  --budget-file budgets/performance_budgets.json `
  --replace
```

For hosted calibration, expose a manual job that passes `mode: calibrate`, `calibration-runs: 5`, `compare-with-base: false`, and `investigate: never`. The reusable workflow accepts calibration only on `workflow_dispatch` for the consumer repository's default branch. It does not install investigator dependencies or receive `openai-api-key`. The artifact contains five captures, five sanitized logs, both manifests, the canonical calibration report, and the proposed v3 policy. The job summary labels the output **proposal only—not an enforced verdict**.

Safe migration remains explicit:

1. Run calibration on the default branch.
2. Download and review the proposal.
3. Apply it explicitly.
4. Commit the v3 policy while `compare-with-base` remains `false`.
5. Enable protected-base comparison in a later pull request.

The capture helper creates collision-safe run IDs, uses the caller SHA as opaque revision metadata, applies a 300-second timeout per process, and stores only workspace-relative paths. The validator, checker, unified runner, and investigator accept `--workspace-root <consumer-root>`; every results, scene, project, and budget input remains relative to that resolved root. Symlink escapes are rejected, and external workspaces may contain generic captures only—not Guardian's synthetic controller evidence.

Capture validity also requires a clean Godot script-load log. `capture_project.py` rejects `SCRIPT ERROR:` and failed-script-load diagnostics even if Godot exits `0` and the independent probe wrote JSON. It preserves the sanitized log and a failed manifest with `godot_script_error`, stops subsequent runs, and keeps that result set out of validation and policy evaluation. This prevents an inactive or partially loaded scene from becoming apparently valid performance evidence.

The job uploads raw captures, sanitized Godot logs, the capture manifest, and canonical gate JSON even on failure, with 14-day retention. Before upload, it resolves the configured project beneath the consumer workspace and copies only the applicable evidence into a fixed runner-temporary staging directory. Absolute-only runs stage candidate evidence and reports; comparison runs additionally stage protected-base evidence and its manifest. This prevents `project-path: .` or a nested project path from producing artifact patterns containing `.` or `..`. The upload explicitly enables hidden files and does not include the full workspace, protected-base source checkout, `.git`, Guardian tooling checkout, environment files, or credentials. Exit `0` means capture, validation, and every budget passed; `1` means valid captures exceeded policy; `2` means capture, configuration, validation, evidence, or operational failure. Optional AI cannot change that exit.

GitHub Actions presents that unchanged canonical report in three immediate places:

- The gate step log lists validation status, every measured value and absolute threshold, and baseline/candidate delta plus relative threshold when comparison is enabled.
- The check run receives one escaped error annotation per failed deterministic rule. A rule that fails both absolute and relative limits produces one combined annotation. Validation or configuration failures receive one safe evaluation-error annotation.
- The job summary contains the deterministic table, authority disclaimer, evidence-artifact guidance, and—only when accepted by the grounding boundary—the optional report under **Optional AI explanation — non-authoritative**.

`tools/render_action_report.py` is presentation-only. Each workflow saves the gate exit before invoking it, so renderer failure produces a warning and cannot alter deterministic exit `0`, `1`, or `2`. Canonical JSON and raw evidence remain the deeper inspection source in the artifact. Rejected model text, credentials, private paths, raw exceptions, and revision values are not presented.

Experiment 14's hosted PluginTest run verified the failure path at `11.619 ms > 2 ms`: the step printed all three budget results, GitHub created the named process-rule annotation, accepted AI was reported as non-authoritative, and artifact upload succeeded. The renderer emitted no presentation warning; because it appends the summary before printing the log, this proves the summary-file write completed. GitHub's public REST/check-run response and unsigned web view did not expose the custom Markdown body, so direct visual inspection of that body remains pending from a signed-in Actions UI.

A separate hosted consumer `never` run completed all three 600-sample captures, validated all three files, and passed both configured budgets at `0.093 ms <= 2 ms` process p95 and `12 <= 100` peak nodes, returning authoritative exit `0`. The later corrected artifact contained nine entries: three capture JSON files, three sanitized Godot logs, the internal capture manifest, the runner manifest, and canonical Guardian report. Experiment 13 subsequently verified the paired path through PluginTest PR #2: three protected-base and three candidate captures validated, count/process budgets failed as intended, the 17-entry artifact preserved both sides, and one `gpt-4.1-mini` contribution was accepted. No private path or credential pattern was detected in either inspected artifact.

For pull-request regression comparison, use the safe two-step migration:

1. Merge a schema-v3 policy such as [`examples/minimal_project/budgets/comparison_budgets.json`](examples/minimal_project/budgets/comparison_budgets.json) while `compare-with-base: false`.
2. In a later pull request, set `compare-with-base: true` in the caller.

The workflow then reads the v3 policy exclusively from `github.event.pull_request.base.sha`, checks out that protected revision in an isolated directory, captures three baseline runs followed by three candidate runs with identical settings, and passes both directories to the deterministic gate. A non-pull-request comparison request fails with exit `2`. The paired mode doubles the configured Godot processes. Sequential same-runner execution reduces host variation; it does not prove identical thermal, scheduling, or system-load conditions.

Example caller after the v3 policy is present on `main`:

```yaml
name: Game performance comparison

on:
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  performance:
    uses: TaofeekS/godot_performance_guardian/.github/workflows/reusable-performance-guardian.yml@fe72c6083c44a5323523d066e0ef9a7f4b308caf
    with:
      project-path: .
      profile: main_scene
      budget-file: budgets/comparison_budgets.json
      compare-with-base: true
      investigate: never
```

The public [PluginTest consumer repository](https://github.com/TaofeekS/PluginTest) is the external integration example used to exercise this workflow. Its [`main.tscn` scene](https://github.com/TaofeekS/PluginTest/blob/main/main.tscn), [v3 comparison policy](https://github.com/TaofeekS/PluginTest/blob/main/budgets/comparison_budgets.json), and [baseline caller workflow](https://github.com/TaofeekS/PluginTest/blob/main/.github/workflows/performance-guardian.yml) show the consumer-side files together; the [high-load caller](https://github.com/TaofeekS/PluginTest/blob/codex/high-load-visual-performance/.github/workflows/performance-guardian.yml) deliberately requests `investigate: always` as an AI-quality evaluation. Guardian's general default remains `never`, and fork PRs without a secret remain deterministic-only. Earlier `12`-node/`1,418`-object comparison output is explicitly invalid because the scene controller failed to load on both revisions.

### Investigator troubleshooting

The investigator exits nonzero when it cannot obtain a model response. Its messages intentionally omit the API key, prompt, raw exception, response body, and general response headers.

| Symptom | Meaning and next action |
| --- | --- |
| `OPENAI_API_KEY is not configured` | The variable is absent from the process running Python. Set a newly issued key in that same PowerShell session. |
| `AuthenticationError` | The API rejected the credential. Replace or correct the environment value; never paste it into source or documentation. |
| HTTP 429 with `code=insufficient_quota` or `type=insufficient_quota` | The API project has no available quota. Check its API billing, credits, and project usage limits. Repeating the command will not repair this condition. |
| Other HTTP 429 | The request was throttled. The message includes a numeric retry delay when the server provides one. Wait before retrying and inspect the API project's rate limits if it persists. |
| `PermissionDeniedError` or `NotFoundError` for the selected model | Verify that the API project can access `OPENAI_MODEL`. Do not switch models unless the error evidence indicates model-specific access or limits. |
| `WARNING: model contribution failed (...)` | The typed contribution left no acceptable recommendation or violated a local rule. The rejected content is not printed; a deterministic cited fallback follows without another API request when a safe validator packet is available. |
| Unified outcome `skipped_no_key` | Investigation was requested, but the process had no `OPENAI_API_KEY`. Deterministic validation/budget output and exit remain authoritative. |
| Unified outcome `api_error` | The investigator timed out, could not launch, returned an API/model-access error, or emitted unrecognized output. Only a safe category is retained; deterministic exit is unchanged. |
| The gate ends with `Process completed with exit code 1` | Read the measured/threshold lines earlier in that step, select the failed-rule annotation, or open the job **Summary** tab. Download the named artifact for canonical JSON and raw captures. |
| Upload error reporting an invalid pattern such as `base-source/./.performance-guardian` | An older reusable-workflow revision interpolated `project-path: .` directly into the baseline artifact pattern. The green authoritative-gate step still records the deterministic verdict, but the job is incomplete because evidence preservation failed. Update the caller to a Guardian revision containing normalized artifact staging and rerun. |
| A Windows runner says a contained temporary path under `RUNNER~1` is outside the equivalent `runneradmin` workspace | Update the caller/tooling reference to `fe72c6083c44a5323523d066e0ef9a7f4b308caf` or later. Containment now compares filesystem identity for short/long aliases; customers do not need to rename paths or weaken traversal and symlink checks. |

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

Budget schema v3 preserves the v2 generic metrics and adds required `maximum_increase_percent` to every rule. Without `--baseline-results`, v3 applies the absolute `maximum` and records comparison as `not_requested`. With a baseline, the checker validates baseline and candidate independently, matches both aggregates by profile, metric, source type, and unit, and requires both the absolute and relative limits to pass. Supplying a baseline with v1 or v2 is configuration error exit `2`.

```powershell
.\.venv\Scripts\python.exe .\tools\run_guardian.py `
  --json `
  --investigate never `
  --baseline-results .\tests\fixtures\comparison\baseline `
  .\tests\fixtures\comparison\candidate `
  .\tests\fixtures\comparison\performance_budgets.json
```

Relative increase is `((candidate - baseline) / baseline) × 100`. Equality passes and a negative percentage is an improvement. Baseline and candidate both zero produce `0%`; a positive candidate from a zero baseline produces `null` and fails the relative rule. [`examples/minimal_project/budgets/comparison_budgets.json`](examples/minimal_project/budgets/comparison_budgets.json) demonstrates project-specific limits of 20% for process p95 and 0% for peak nodes; these are not universal Godot recommendations.

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

Experiment 15 exercised the assistant against five fresh captures from the independent Godot 4.5.1 project. The validated medians were `0.421 ms` process p95, `3` peak nodes, and `1,393` peak objects. The balanced preset proposed `0.7 ms`, `4` nodes, and `1,533` objects. An explicit apply to a temporary contained policy succeeded, and the same five captures passed all three absolute rules. These values describe that local host and capture configuration only; they were not copied into the repository's existing example budgets.

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

The tracked fixture is historical addon `1.0.1` evidence and remains unchanged. Current addon captures report version `1.2.0`; the JSON schema and measurements shown above are otherwise unchanged.

Its complete form includes UTC timestamps, sanitized configuration, memory availability, every global count, all 600 samples, timing/count summaries, environment metadata, and limitations. Because no revision was supplied, it explicitly states that the exact source revision is unknown.

Individual Godot result files are unchanged and contain no `budget_results` or structured `errors` property. The separate checker emits a deterministic result document in `--json` mode containing its schema version, overall status, validator metadata, per-rule measured and maximum values, matched opaque evidence IDs, summary counts, and preserved validator limitations. Human mode reports the same evaluation. Invalid arguments and operational errors go to stderr; policy failures remain valid output and return exit code `1`.

The unified runner wraps that existing evidence without recalculating metrics. Its canonical JSON has this shape (per-rule results and limitations abbreviated):

```json
{
  "schema_version": 1,
  "deterministic_status": "passed",
  "validator": {
    "status": "passed",
    "candidate_file_count": 1,
    "validated_file_count": 1,
    "results_directory": "tests/fixtures/generic_results"
  },
  "budget": {
    "status": "passed",
    "summary": {"failed": 0, "passed": 2, "total": 2},
    "results": [],
    "limitations": []
  },
  "investigation": {
    "mode": "never",
    "requested": false,
    "api_request_attempted": false,
    "outcome": "not_requested",
    "rule_ids": [],
    "error_category": null,
    "report": null
  },
  "authoritative_exit_code": 0,
  "authoritative_exit_reason": "Validation passed and every configured budget passed."
}
```

In real output, `results` and `limitations` are preserved rather than empty. Canonical mode sorts keys, uses compact separators, and ends with one newline.

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

The final competition evaluation freezes Baseline 0 from commit `22af3b44962517b0f1d7ac0b7499f724f2e2cb34` and compares it with product revision `2bf5ff6efbedb44a8ac0370b686554a5a4ac4e40` using the same ten-case manifest. A case counts only when its exit/status, required numerical evidence, and safe actionable detail match the predefined oracle. Baseline 0 completed `1/10` cases; the final deterministic product completed `10/10`, a gain of 90 percentage points of workflow coverage. The challenging case correctly passed an absolute process limit at `0.61 ms <= 1.1 ms` while failing the protected-base relative rule at `22% > 20%`. Two runs produced byte-identical canonical output. This comparison measures expanded workflow coverage and evidence quality, not faster game execution. See [`FINAL_EVALUATION.md`](FINAL_EVALUATION.md) and the canonical [`final-evaluation.json`](evaluation/results/final-evaluation.json).

The optional investigator exposes that same program as its only function tool, `validate_benchmark_results`. The tool invokes the validator's `--evidence-json` mode, which returns a deterministic JSON-compatible packet containing explicit evidence kind, validation status, a repository-relative result directory, opaque evidence IDs, and explicit limitations. Synthetic packets contain scenario comparisons, cleanup evidence, and allowlisted controller behavior. Generic packets contain profile-scoped engine aggregates plus memory and source-revision availability. The normal validator command and human-readable output remain unchanged.

SDK configuration requires the validator tool on the first model turn, followed by a strict typed contribution rather than model-authored Markdown. The model may return zero to three bounded non-causal hypotheses and must return one to five recommendations. Each item carries one to four unique opaque evidence IDs. Recommendation behavior is selected from the enum `compare`, `inspect`, `measure`, `profile`, `validate`, `capture`, or `repeat_capture`; the model cannot supply free-form action text. Local validation rejects unknown or duplicate IDs, causal conclusions, Markdown, newlines, measurements, paths, embedded citations, and credential-shaped text. Accepted actions are rendered into profile/metric-specific controlled investigations rather than generic advice.

Experiment 19 freezes ten performance-policy failure packets and compares this typed design with a matched free-form agent using the same pinned `gpt-4.1-mini-2025-04-14` snapshot, packet tool, requirements, 2,000-output-token allowance, and one paired run per case. The observed typed design was directly accepted on `10/10` cases; free-form was accepted on `0/10`. Every run used exactly one packet-tool call and two model requests. Total observed cost was `$0.0237344`; median run latency was `7.402 s` and nearest-rank p95 was `12.508 s`. No typed fallback was needed, while rejected free-form text was retained only as hashes and safe rule IDs. This is a controlled ten-packet result, not long-run model reliability. See [`AGENT_EVALUATION.md`](AGENT_EVALUATION.md) and the canonical [`agent-evaluation.json`](evaluation/agent/results/agent-evaluation.json).

Re-grade that stored result without an API key or model request:

```powershell
.\.venv\Scripts\python.exe .\tools\run_agent_evaluation.py `
  --verify .\evaluation\agent\results\agent-evaluation.json
```

Application code renders the five sections—Validation status, Verified facts, Possible explanations, Recommended next investigation, and Remaining uncertainty—from semantic packet evidence plus accepted model choices. Measurements, availability wording, limitations, citations, and recommendation sentences are local and deterministic. Synthetic matching uses metric, scenario, source type, unit, and value shape. Generic matching uses metric, profile, source type, unit, and availability state. IDs may be renumbered without changing selection; missing, duplicate, mixed-identity, or malformed matches fail safely. At least one model-selected recommendation must survive local validation before a report counts as model-contributed.

The schema-specific grounding gate still checks the completed report's section order, evidence references, supported numeric values, scenario or profile coverage, causal language, required limitations, root-cause uncertainty statement, and read-only evidence-linked recommendations. Generic grounding additionally rejects invented unavailable-memory values, synthetic-only claims, revision values or equality claims, and private paths. If typed final-output parsing fails, the SDK run hook may recover the already-completed validator packet; that packet is revalidated before fallback. No second model request is made. If no safe packet is recoverable, the command fails nonzero. Rejected typed content is never printed or stored. Deterministic fallback begins with:

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

Experiment 9 replaced free-form model reports with the typed contribution above while keeping deterministic rendering and the existing gate. Local verification passed all 94 tests. One live `gpt-4.1-mini` run against the tracked `main_scene` fixture returned two accepted enum recommendations, produced a grounded locally rendered report, and used no fallback. One optional hypothesis was discarded by the text policy. Mini therefore met the first-candidate adoption rule and remains the default; Terra and Sol were not called. This is one nondeterministic response, not a general reliability guarantee.

Experiment 10 added the unified deterministic gate and Windows workflow without changing validator calculations, budget semantics, fixtures, or investigator grounding. Local verification passed all 120 tests. The tracked fixture validated and its two budgets passed (`0.5 ms <= 1.1 ms`, `3 nodes <= 3`); validator, budget, and unified canonical JSON were each identical across two invocations. All 49 optional historical results still validated, and the Experiment 5 policy retained exactly its two intentional failures. One authorized live unified `gpt-4.1-mini` run in `always` mode returned a directly accepted locally rendered report with three evidence-linked recommendations, no fallback, and authoritative exit `0`. The GitHub-hosted workflow itself remains unverified until it runs on GitHub.

Experiment 12 added opt-in protected-base comparison. The tracked unchanged pair passes, while the tracked regression fixture proves an absolute pass (`0.61 ms <= 1.1 ms`) can still fail the relative process rule (`22% > 20%`). A temporary independent consumer workspace then ran three baseline plus three unchanged-candidate Godot `4.5.1` captures. All six files contained 600 samples and validated; baseline/candidate median process p95 was `0.531 ms`/`0.526 ms` (`-0.942%`), peak nodes stayed `3`/`3`, and the unchanged v3 policy returned authoritative exit `0`. The complete suite passed 146 tests. Its first authorized live comparison attempt exposed and fixed a duplicated candidate CLI argument; Experiment 13 later supplied the successful hosted paired and live interpretation evidence.

Experiment 13 corrected PluginTest's clean-checkout scene loading and made script/load errors fatal to capture authority. The final hosted PR produced three baseline and three candidate files with 600 samples each and clean logs. Median peak nodes rose from `2,289` to `26,366` (`1,051.857%`), objects from `5,608` to `49,511` (`782.864%`), and process p95 from `14.169 ms` to `224.999 ms` (`1,487.967%`). The deterministic gate returned `1`. Exactly one `gpt-4.1-mini` request produced an accepted locally rendered report with citations for all three rules, all limitations, no root-cause claim, and read-only recommendations; no fallback was used.

Experiment 14 added safe Actions presentation without changing calculations or canonical JSON. The complete local suite passed 160 tests. Hosted PluginTest run `33286227714` validated three clean 600-sample captures and returned the expected exit `1`: process p95 failed at `11.619 ms > 2 ms`, while peak nodes and objects passed. The log named the measurement and threshold, the check run contained one corresponding named rule annotation, optional `gpt-4.1-mini` investigation was accepted, and the nine-entry artifact retained three captures, three logs, two manifests, and canonical JSON with no detected private-path or credential pattern. No second workflow or model request was made.

Experiment 15 added deterministic budget calibration without changing validation, enforcement, or investigator authority. Five fresh independent-project captures validated, produced the local proposal described above, and passed after explicit application to a temporary policy. The complete implementation suite passed 173 tests. Hosted PluginTest run `33288045948` then completed calibration only: optional dependencies, enforcement, comparison, and AI were skipped. Its five clean 600-sample captures produced medians of `11.62 ms`, `2,281` nodes, and `5,580` objects and proposed `17.5 ms`, `2,510` nodes, and `6,138` objects. The fourteen-file artifact contained five captures, five logs, two manifests, the report, and policy; all captures validated, the proposal passed against them, and scans found no private-path or credential pattern. The hosted proposal was not applied.

Experiment 16 added the read-only editor dock without changing capture or report schemas. The focused suite passed 19 tests and the final complete suite passed 180 tests in 4.932 seconds with one environment-dependent symlink test skipped. A Godot `4.5.1.stable.official.f62fdbde1` helper verified capture timestamp ordering, untimestamped report ordering, failed-rule merging, proposal labeling, and path rejection, then produced a synchronized `passed` marker. A three-second headless editor lifecycle exited `0` with no script parse/load diagnostic. The dock's rendered visual layout and interactive usability were not directly observed, so they remain unverified rather than inferred from the lifecycle check.

Experiment 17 replaced that side dock with a Godot main-screen plugin named **Guardian**. The implementation uses `_has_main_screen()`, `_make_visible()`, `_get_plugin_name()`, `_get_plugin_icon()`, and `EditorInterface.get_editor_main_screen()` and contains no dock-slot registration or automatic workspace selection. The focused 19-test suite and complete 180-test suite passed; byte compilation and both tracked generic validations succeeded. The Godot 4.5.1 helper and a three-second editor lifecycle each exited `0` without script/load diagnostics. After PluginTest received addon `1.2.0`, the user manually confirmed that the **Guardian** workspace appears and works without consuming the Inspector and Node dock area.

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
- Paired comparison doubles capture work. Same-runner sequential execution reduces variation but does not guarantee identical thermal, scheduling, or system-load conditions.
- The committed final-evaluation package uses fixed synthetic and small generic fixtures. It is reproducible evidence of deterministic tool behavior, not ten independent customer games or a universal performance baseline.
- The editor workspace is read-only: it cannot launch captures, calculate budgets, access CI artifacts that have not been copied under `res://`, show live capture progress, or repair a project. The investigator receives only validator-produced evidence and cannot establish root cause by itself.
- Calibration proposes host-specific thresholds from engine-global metrics; it does not identify project-owned objects, measure GPU work, edit policy automatically, or establish that a threshold is appropriate without human review.
- Live generic responses remain nondeterministic. Terra and Sol each required fallback in Experiment 8, while `gpt-4.1-mini` produced directly accepted typed contributions in Experiments 9 and 10. These few responses are insufficient to rank general model quality or establish long-run reliability.
- The repository workflow is hosted-verified on Windows with both independent jobs green. The reusable workflow's absolute-only nine-entry artifact, paired 17-entry PluginTest artifact, actionable hosted failure reporting, and the `fe72c608...` enforcement canary are verified. Direct visual reading of the custom job-summary body remains pending from a signed-in UI because public/API inspection does not expose it.
- The current 49-file aggregate mixes historical `160 x 160` and `240 x 240` CPU workloads, and stored results do not identify their source revision.
- Portable capture and calibration are verified only for the included independent project and PluginTest on Godot 4.5.1. These host-specific runs do not prove universal project, platform, or timing compatibility.
- Windows is the only verified operating system; the harness is PowerShell-specific.
- Individual result JSON does not contain a consolidated budget verdict or structured error object.

## 15. Roadmap

| Stage | Status | Intended outcome |
| --- | --- | --- |
| 1. Deterministic baseline | Completed | Three synthetic scenarios, raw samples, summaries, repeated runs, and objective validation. |
| 2. Configurable budgets | Completed (v1/v2/v3) | Apply scenario, profile, or protected-base comparison policies through deterministic human/JSON tools and a unified Windows CI gate with exit codes `0`/`1`/`2`. |
| 3. Ten evaluation fixtures | Completed (fixed workflow cases) | Ten tracked cases cover synthetic validation, generic evidence, passing and failing policy, protected-base comparison, malformed evidence, and calibration. Broader real-game coverage remains a limitation. |
| 4. Reusable Godot editor workspace | Completed (read-only v2) | The addon presents active-scene probe readiness, recent contained evidence, deterministic failed rules, safe details, and local evidence navigation in a selectable main-screen workspace without occupying a side dock. PluginTest placement and interaction were manually confirmed by the user. |
| 5. Agent-assisted investigation | Completed (controlled evaluation) | A read-only command-line investigator handles synthetic scenarios, generic profiles, and paired comparisons, filters typed model contributions, and recovers failures with deterministic fallback. In Experiment 19 it directly passed all ten frozen failure packets versus zero for the matched free-form baseline; broader real-project and repeated-run reliability remain limitations. |
| 6. Temporary experimental fixes and verification | Planned | Apply isolated candidate changes and rerun the same evidence. |
| 7. Final baseline comparison and submission package | Partial | A frozen Baseline 0 snapshot, ten-case manifest, integrity metadata, canonical result, and judge-facing final evaluation are tracked. Final submission assembly remains. |

### Planned multi-scene project gate

The reusable consumer workflow currently accepts one `profile` and one optional `scene-path` per invocation. A customer can test multiple scenes today by defining separate reusable-workflow jobs for each scene/profile, but Guardian does not yet provide a first-class combined multi-scene capture interface.

A planned project-level scene manifest would list multiple profile and `res://` scene-path entries. One workflow invocation would then preserve separate captures and sanitized logs for every scene, apply one project budget containing profile-specific rules, produce one combined deterministic verdict and artifact, and make the validated multi-profile evidence available to the optional investigator. The independent example should expand from its current main scene to include an object-heavy scene and a physics-heavy scene.

Multi-scene coverage increases CI cost: the number of Godot processes is `scenes x capture runs`, and protected-base comparison doubles that total because it captures both baseline and candidate scenes. Projects should therefore select representative performance-critical scenes rather than automatically capturing every scene.

## 16. Hackathon evidence

- [`AGENT_TRAJECTORY.md`](AGENT_TRAJECTORY.md#judge-navigation) begins with a judge navigation guide, actor/authority boundaries, representative trajectories, and milestone links, followed by the complete chronological audit of requests, decisions, inspections, edits, issues, and verification.
- [`IMPROVEMENT_CHANGELOG.md`](IMPROVEMENT_CHANGELOG.md) is the append-only product experiment record. It establishes Baseline 0 and records the investigator, configurable-budget, portable-capture, CI, calibration, and editor-workspace experiments.
- [`FINAL_EVALUATION.md`](FINAL_EVALUATION.md) compares frozen Baseline 0 with the final product across ten predefined deterministic cases. The tracked [`case manifest`](evaluation/cases.json), [`integrity metadata`](evaluation/integrity.json), raw fixtures, and canonical [`evaluation result`](evaluation/results/final-evaluation.json) make the primary `1/10` versus `10/10` result independently rerunnable without Godot or an API key.
- [`AGENT_EVALUATION.md`](AGENT_EVALUATION.md) separately evaluates the optional runtime agent across ten fixed failure packets. Its frozen [controls](evaluation/agent/config.json), [case manifest](evaluation/agent/cases.json), [integrity metadata](evaluation/agent/integrity.json), packets, prompts, and canonical [result](evaluation/agent/results/agent-evaluation.json) preserve the observed `10/10` typed versus `0/10` free-form comparison and allow API-free re-grading.
- Generated benchmark evidence currently exists locally beneath `demo_project/results/` and is ignored by Git.
- The sanitized [`main_scene` generic capture](examples/fixtures/main_scene-godot-4.5.1.json) is tracked as the first portable integration fixture.
- The [`Performance Guardian` workflow](.github/workflows/performance-guardian.yml) is the first automated deterministic gate; its tracked fixture output is uploaded as a JSON artifact, while broader categorized evidence packages remain planned.
- The [`reusable consumer workflow`](.github/workflows/reusable-performance-guardian.yml) adds fresh capture, validation, policy enforcement, sanitized logs, manifests, and canonical gate output for another Godot repository. Hosted absolute-only and paired runs are verified: the latter preserved three baseline plus three candidate captures and logs, both capture manifests, and canonical report, while returning the intended deterministic budget failure.
- The final baseline-comparison package is tracked. Final submission assembly remains outstanding.

The trajectory explains how an agent performed work. The improvement changelog explains how the product changes across evidence-backed experiments, including unsuccessful or removed approaches.

### Documentation skill

The repository-local [`godot-performance-guardian-docs`](.agents/skills/godot-performance-guardian-docs/SKILL.md) skill instructs Codex to keep this README, `AGENT_TRAJECTORY.md`, and `IMPROVEMENT_CHANGELOG.md` synchronized with repository evidence. It is documentation tooling, not part of the runtime benchmark or planned investigation agent.

## 17. License

This repository is licensed under the [MIT License](LICENSE), Copyright (c) 2026 TaofeekS.
