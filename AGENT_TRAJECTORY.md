# Agent Trajectory: Repository Documentation and Skill

## Task identity

- **Task:** Rewrite the Godot Performance Budget Guardian README from repository evidence, record the documentation work, and package the workflow as a repository-local Codex skill.
- **Date:** 2026-08-28.
- **Workspace state at start:** Fresh Git repository with no commits. The benchmark implementation, short README, and validation tooling existed as untracked files. `AGENT_TRAJECTORY.md`, `IMPROVEMENT_CHANGELOG.md`, a license, and a configurable budget file did not exist.
- **Scope boundary:** This trajectory covers the documentation task. Earlier benchmark implementation work is referenced only where its files or verified outputs were used as documentation evidence.

## Original request

The documentation request was available in the supplied attachment. It is quoted below with one unrelated private-project name redacted to honor the request's own exclusion constraint:

```text
Use `$agent-trajectory` to record this documentation task as it happens.

## Goal

Create or update `README.md` for the Godot Performance Budget Guardian repository.

The README must accurately describe the repository’s current implementation. Inspect the workspace before writing and do not document planned features as if they already exist.

## Context

This is a fresh, synthetic project for the Micro1 Agentic Workflows Hackathon. It must not use, mention or contain [unrelated private project] source code, private assets or proprietary telemetry.

The project targets the exact installed Godot 4.5.x version. Its initial purpose is to establish a deterministic performance-measurement baseline using synthetic scenarios:

* Healthy scenario
* Node-leak scenario
* CPU-spike scenario

The complete future product may include a reusable editor plugin and an investigation agent, but those features must be labelled as planned unless they are already implemented and verified in the repository.

## Instructions

Before editing:

1. Inspect the complete repository structure.
2. Read the relevant scripts, configuration files, budgets and evaluation tools.
3. Determine the exact Godot version being used.
4. Identify which commands have actually been run successfully.
5. Identify incomplete, missing or unverified features.
6. Briefly state your documentation plan before writing.

Then create or update `README.md`.

## Required README sections

### 1. Project title and short description

Explain in one concise paragraph that the project detects performance-budget regressions in repeatable Godot scenarios and preserves evidence for diagnosis.

### 2. Current status

Clearly distinguish:

* What currently works
* What is partially implemented
* What is planned

Do not claim that the editor plugin, LLM agent, automatic repair or full 10-case evaluation exists unless the repository proves it.

### 3. Intended user and problem

Explain:

* Who experiences the problem
* Why manually noticing performance regressions is difficult
* Why repeatable performance budgets are useful
* How this differs from merely viewing Godot’s profiler

### 4. Current baseline

Explain that the baseline:

* Runs deterministic synthetic scenarios
* Collects performance measurements
* Compares measurements with configured budgets
* Reports pass or fail
* Does not yet provide automated root-cause investigation unless that feature exists

### 5. Repository structure

Include an accurate tree of the repository and briefly explain the purpose of every important folder and file.

Do not list files that do not exist without marking them as planned.

### 6. Requirements

Document:

* Exact tested Godot version
* Python version, if Python is used
* Supported operating system currently verified
* Whether a debug build is required
* Any dependencies
* Whether an internet connection or API key is required

If a version or platform has not been verified, say so.

### 7. Quick start

Provide exact commands for:

* Cloning or opening the repository
* Opening the synthetic project in Godot
* Running the healthy scenario
* Running the node-leak scenario
* Running the CPU-spike scenario
* Running the evaluation script
* Locating generated results

Use Windows PowerShell commands first. Include Linux/macOS alternatives only if the commands are supported by the implementation.

Use the actual project paths and argument names found in the code.

### 8. Benchmark methodology

Document:

* Fixed random seed
* Warm-up period
* Number of measured frames or iterations
* Number of repeated runs
* Metrics collected
* How median and p95 are calculated
* How scenario duration is measured
* Why raw samples are preserved

Only describe behaviour implemented in the code. Mark intended methodology as planned when necessary.

### 9. Scenarios

For each implemented scenario, explain:

* What it does
* Which regression it represents
* Which measurements should change
* What result is expected

Do not insert invented numerical results.

### 10. Performance budgets

Explain:

* Where budgets are stored
* What each field means
* How developers can change them
* That limits should be calibrated from repeated healthy runs
* Why results from different machines should not be directly compared

Include an example only if it matches the actual schema.

### 11. Output format

Show a real or schema-accurate JSON example.

Explain:

* Raw samples
* Calculated statistics
* Engine version
* Scenario identifier
* Budget results
* Error information

Do not present fabricated measurements as verified results.

### 12. Evaluation

Explain how the evaluation tool objectively checks:

* Healthy scenario does not trigger known regressions
* Node-leak scenario fails the appropriate object or node budget
* CPU-spike scenario fails the appropriate time budget
* Output is valid and deterministic enough for comparison

Include actual verified output only when it is available.

### 13. Reproducibility notes

Explain:

* Baseline and final solution must use the same scenarios
* Tests should run on the same hardware and configuration
* Performance measurements are noisy
* Warm-up and repeated runs reduce noise
* Headless execution cannot provide meaningful rendering measurements
* The exact Godot version and relevant configuration must be recorded

### 14. Known limitations

List current limitations honestly, including applicable items such as:

* Synthetic scenarios only
* Godot 4.5.x only
* GDScript-focused implementation
* Debug-only memory monitors
* CPU and object-growth focus
* No meaningful GPU measurements in headless mode
* No automatic root-cause agent yet
* No editor dock yet
* Limited operating-system verification

Only include limitations relevant to the current repository.

### 15. Roadmap

Separate planned stages:

1. Deterministic baseline
2. Configurable budgets
3. Ten evaluation fixtures
4. Reusable Godot editor dock
5. Agent-assisted investigation
6. Temporary experimental fixes and verification
7. Final baseline comparison and submission package

Mark completed stages based on repository evidence.

### 16. Hackathon evidence

Briefly point readers to:

* `AGENT_TRAJECTORY.md`
* `IMPROVEMENT_CHANGELOG.md`
* Baseline results
* Iteration results
* Final results

Explain the distinction between the agent trajectory and improvement changelog.

### 17. License

Document the actual license if one exists. Otherwise state that a license has not yet been selected; do not assume MIT automatically.

## Writing requirements

* Use clear GitHub-flavoured Markdown.
* Write for a developer seeing the repository for the first time.
* Keep commands copyable.
* Use relative links.
* Avoid marketing exaggeration.
* Avoid unsupported performance claims.
* Do not invent files, test results, supported platforms or features.
* Do not expose credentials, private paths or identifying information.
* Keep planned features clearly separated from implemented features.
* Prefer concise explanations over repetitive prose.

## Verification

After writing the README:

1. Check that every referenced file exists or is explicitly marked as planned.
2. Check that every command matches the actual implementation.
3. Run safe README commands where practical.
4. Verify all relative links.
5. Report which commands were verified and which remain unverified.
6. Show the final `README.md` path and summarize any documentation gaps.

## Done when

* `README.md` exists at the repository root.
* It accurately describes the current repository.
* It provides reproducible setup and execution instructions.
* It distinguishes implemented and planned features.
* It contains no fabricated measurements or completion claims.
* Verified commands and remaining limitations are clearly documented.
```

The user then added:

> also turn this to a skill

## Planning and approval

The agent activated and read the `agent-trajectory` and `skill-creator` instructions. Before planning, it inspected the repository and asked two decisions that could not be inferred from files:

- The user selected a skill specific to this repository rather than a generic Godot or general README skill.
- The user selected a repository-local skill rather than a personal Codex installation.

The proposed plan covered three deliverables:

1. Rewrite `README.md` with the required evidence-based sections.
2. Create this chronological `AGENT_TRAJECTORY.md`.
3. Add `.agents/skills/godot-performance-guardian-docs/` with a concise entrypoint, UI metadata, and a detailed README requirements reference.

The plan explicitly required reuse of the existing successful suite rather than rerunning it solely for documentation, relative-link checks, command-to-source checks, skill validation, and `git diff --check`. The user approved the plan with the instruction `PLEASE IMPLEMENT THIS PLAN`.

## Evidence gathering

### Repository inspection

The agent read the complete contents of:

- `README.md`
- `demo_project/project.godot`
- `demo_project/main.tscn`
- `demo_project/scripts/test_actor.gd`
- `demo_project/scripts/benchmark_controller.gd`
- `demo_project/run_benchmarks.ps1`
- `tools/validate_results.py`
- Both root and demo-project `.gitignore` files

It also inspected the complete non-cache repository tree, Git state, configured remotes, generated result inventory, representative result schema, and expected documentation artifact paths.

### Substantive commands

The following commands or command groups were used. User-specific absolute paths are redacted where they were not necessary to the record.

```powershell
Get-Content -Raw <agent-trajectory-skill>/SKILL.md
Get-Content -Raw <attachment>/pasted-text.txt
rg --files -g '!demo_project/.godot/**' -g '!demo_project/results/**'
git status --short
```

```powershell
Get-Content -Raw README.md
Get-Content -Raw demo_project\project.godot
Get-Content -Raw demo_project\main.tscn
Get-Content -Raw demo_project\scripts\test_actor.gd
Get-Content -Raw demo_project\scripts\benchmark_controller.gd
Get-Content -Raw demo_project\run_benchmarks.ps1
Get-Content -Raw tools\validate_results.py
```

```powershell
python --version
<installed-godot-4.5.1> --version
$PSVersionTable.PSVersion.ToString()
git remote -v
git status --short --branch
git check-ignore -v demo_project\results\*.json demo_project\.godot
```

Python standard-library snippets were used to inspect result keys, metric availability, tolerances, environment metadata, scenario counts, retained-node evidence, and the successful suite's CPU ratio. These commands only read existing JSON files.

### Findings

Facts established before writing:

- The project implements `healthy`, `node_leak`, and `cpu_spike` with seed 1337, 120 warmup frames, 600 measured frames, and 64 actors.
- The batch harness starts three isolated runs per scenario and passes the resulting nine paths to the validator.
- The controller records direct workload time and six Godot performance monitors, preserves 600 raw samples, calculates summaries, and writes atomically.
- The validator recomputes summaries, checks cleanup and leak evidence, and compares median per-run p95 workload times across healthy and CPU-spike results.
- Current limits are hard-coded in the controller and validator. No configurable budget file exists.
- No editor dock/plugin, LLM investigation agent, repair workflow, ten-case fixture set, improvement changelog, organized evidence package, license, Git remote, or commit exists.
- Godot `4.5.1.stable.official.f62fdbde1`, Python 3.14.6, PowerShell 7.6.4, and Windows 10.0.26200 were the exact verified environment.
- Existing result metadata recorded headless debug runs with static-memory data available.

### Reused benchmark evidence

The documentation task did not rerun the expensive suite. It reused a successful nine-run result set generated earlier in the same workspace. The recorded output was:

```text
INFO: median p95 workload: healthy=185.000 usec, cpu_spike=12725.000 usec, ratio=68.78x
INFO: supporting evidence: process p95 healthy=0.605000 ms, cpu_spike=15.075000 ms; duration healthy=4976.010 ms, cpu_spike=7992.353 ms
Validated 9 result files successfully.
Benchmark suite passed. Results: <workspace>\demo_project\results
```

Inspection of those nine files confirmed three results per scenario, Godot `4.5.1-stable (official)`, Windows headless debug metadata, retained-node values of 0 for healthy, 120 for node leak, and 0 for CPU spike.

## Implementation

### Repository-local skill

The `skill-creator` initializer was run with the approved name, repository path, reference resource, and UI fields:

```powershell
python <skill-creator>/scripts/init_skill.py godot-performance-guardian-docs `
  --path .agents\skills `
  --resources references `
  --interface "display_name=Performance Guardian Docs" `
  --interface "short_description=Maintain evidence-grounded project documentation" `
  --interface 'default_prompt=Use $godot-performance-guardian-docs to update this repository README and documentation trajectory from verified evidence.'
```

The generated scaffold was replaced with repository-specific instructions. `SKILL.md` requires evidence-first documentation, accurate status classification, protection from private or proprietary material, maintenance of the README and trajectory, and verification after edits. `references/readme-requirements.md` holds the detailed 17-section contract and repository invariants. `agents/openai.yaml` retains automatic invocation and the approved interface text.

### README

The original short benchmark README was expanded into a developer-facing project document. It now distinguishes implemented, partial, planned, and unverified capabilities; documents the exact environment and command interfaces; explains the benchmark, scenarios, embedded thresholds, JSON schema, validator, limitations, roadmap, hackathon evidence, documentation skill, and absent license.

The JSON example uses fields and measurements read from an existing verified CPU-spike result. The evaluation excerpt is copied from recorded successful output and is labeled as single-machine evidence rather than a portable claim.

## Issues and responses

### Test failures

No documentation-content check or skill-structure check found a defect in the finished deliverables. The official skill validator was initially unable to start because its own undeclared `yaml` import was unavailable; that dependency issue is recorded below as an operational issue rather than a failed assessment of the skill.

### Operational editing issues

1. A combined patch attempted to delete and re-add `README.md` in one operation. The patch engine rejected it before changing files with `invalid patch: multiple operations target ... README.md`.
2. A follow-up delete-only patch also failed to delete `README.md`. No file content was lost.
3. The agent responded by using supported in-place update patches. The skill entrypoint, requirements reference, README, and trajectory were then written successfully.
4. The first `quick_validate.py` runs stopped at import time with `ModuleNotFoundError: No module named 'yaml'`; they did not evaluate the skill. The bundled workspace Python had the same missing dependency.
5. A sandboxed attempt to install PyYAML into a named temporary directory could not access PyPI. After approval, PyYAML 6.0.3 was installed only in that temporary directory. The validator initially could not read the escalated directory from the sandbox, then ran successfully with the same approved access.
6. A source-search pattern beginning with `--scenario` was initially interpreted as an `rg` option. Repeating it with the standard `rg -- <pattern>` separator produced the expected argument-to-source matches.
7. The first sandboxed removal of the temporary PyYAML directory was denied. The path was resolved and checked to be inside the system temporary directory; approved removal then succeeded with `temporary_dependency_removed=True`.

These were editing-tool issues, not benchmark or validator failures.

## Verification evidence

The full benchmark was not rerun solely for documentation. Existing successful result evidence was inspected instead.

The official skill validation completed with:

```text
Skill is valid!
```

A final standard-library documentation check parsed both README JSON blocks, resolved every relative Markdown link, checked the numbered headings, matched cited result values to the stored JSON, checked the trajectory's major sections, and scanned all new text files for trailing whitespace and final newlines. Its output included:

```text
relative_links 10 missing []
numbered_sections [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
json_examples 2 valid
verified_result_values_present True
trajectory_sections_present True
trailing_whitespace []
missing_final_newline []
```

Argument searches matched the documented `--scenario`, `--run-id`, and `--output` names to `benchmark_controller.gd`. A scan found no private absolute paths, excluded project names, or unfinished scaffold markers in the README, trajectory, or skill. `git diff --check` produced no output; because the fresh repository's files are untracked, the independent text scan above supplied the meaningful whitespace verification.

The inexpensive Python evaluation was then rerun over the existing nine-file suite without rerunning Godot:

```text
INFO: median p95 workload: healthy=185.000 usec, cpu_spike=12725.000 usec, ratio=68.78x
INFO: supporting evidence: process p95 healthy=0.605000 ms, cpu_spike=15.075000 ms; duration healthy=4976.010 ms, cpu_spike=7992.353 ms
Validated 9 result files successfully.
```

Verified through existing execution evidence:

- All three scenario values were exercised by the successful batch harness.
- The Windows batch harness created and validated nine results.
- The Python validator returned success for that exact nine-file set.

Not freshly or independently verified by this documentation task:

- Cloning, because the repository has no configured remote URL.
- A clean interactive editor launch outside the managed environment.
- Linux or macOS execution.
- Other Godot, Python, or PowerShell versions.

## Final result and remaining gaps

The root `README.md` now contains the required evidence-grounded developer documentation and all 17 requested sections. The repository-local `godot-performance-guardian-docs` skill contains a validated entrypoint, explicit automatic-invocation metadata, and a routed detailed requirements reference. This file records the documentation task and its verification without claiming completion of planned product work.

Remaining product and documentation gaps are the configurable budget schema, ten fixtures, editor dock, investigation agent, automated repair workflow, categorized versioned results, `IMPROVEMENT_CHANGELOG.md`, Git remote, and license. Generated results remain ignored local evidence rather than a committed baseline/iteration/final package.
