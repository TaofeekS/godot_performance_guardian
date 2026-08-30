# Agent Trajectory: Repository Documentation and Skill

## Judge navigation

### Two-minute route

1. Follow the [judge reproduction commands](README.md#judge-reproduction).
2. Read the [final ten-case comparison](FINAL_EVALUATION.md) and its canonical [`final-evaluation.json`](evaluation/results/final-evaluation.json).
3. Use the [representative trajectories](#representative-trajectories) below to see accepted AI, rejected AI, invalid evidence, and human usability feedback.
4. Inspect the complete [Experiment 18 execution history](#trajectory-experiment-18) and its [cross-platform integrity correction](#trajectory-experiment-18-integrity).
5. Read [`IMPROVEMENT_CHANGELOG.md`](IMPROVEMENT_CHANGELOG.md) for the product story rather than the command-by-command audit.

### Primary outcome

| Metric | Baseline 0 | Final product | Change |
| --- | ---: | ---: | ---: |
| Correct actionable outcomes | 1/10 | 10/10 | **+90 percentage points** |
| Deterministic ten-case evaluation API cost | $0 | $0 | No API required |

This result measures deterministic workflow coverage and evidence quality. It does **not** mean that game execution became 90% faster. The compared revisions, scoring rubric, limitations, and all ten cases are in [`FINAL_EVALUATION.md`](FINAL_EVALUATION.md).

### Which document answers which question?

| Document | Use it to answer |
| --- | --- |
| [`README.md`](README.md) | How do I install, run, reproduce, and use the product? |
| [`FINAL_EVALUATION.md`](FINAL_EVALUATION.md) | Did the final solution meet the predefined competition target? |
| [`IMPROVEMENT_CHANGELOG.md`](IMPROVEMENT_CHANGELOG.md) | Why did the product change, and what did each experiment teach? |
| `AGENT_TRAJECTORY.md` | What did the development agent inspect, change, test, reject, and verify? |

## Actors, tools, and authority

### Godot Performance Investigator — shipped runtime agent

- **Tool:** exactly one function tool, `validate_benchmark_results`.
- **Input:** validator-produced structured evidence and explicit limitations.
- **Contribution:** bounded evidence-linked hypotheses and recommendations that must pass local validation.
- **Authority boundary:** it cannot capture measurements, modify a project, recalculate validator facts, alter budgets, or decide the authoritative exit. Its explanation is optional and non-authoritative.

### Codex development agent — build-time implementation and evaluation agent

- **Tools:** repository inspection and editing, bounded local commands and tests, Git operations when explicitly authorized, and repository documentation/trajectory skills.
- **Contribution:** implements user-approved changes, evaluates them, records failures, and preserves verification evidence.
- **Authority boundary:** it is not shipped with the runtime product and cannot override deterministic results. Human approval controls material scope changes and explicitly requested commit, push, workflow, or external-delivery operations.

### Validator, budget checker, and calibration assistant — deterministic tools, not agents

- `validate_results.py` decides whether evidence satisfies its schema and integrity rules.
- `check_budgets.py` applies project-owned thresholds and returns deterministic policy pass or failure.
- `calibrate_budgets.py` proposes reviewable thresholds but cannot enforce, apply, commit, or authorize them automatically.
- The validator, checker, and calibration assistant use no LLM, make no causal inference, and do not change policy by themselves.
- `run_guardian.py` orchestrates those deterministic results and may invoke the optional investigator without transferring authority to AI.

## Representative trajectories

### Grounded accepted investigation

In [Experiment 13](#trajectory-experiment-13), a hosted regression supplied structured baseline/candidate evidence. `gpt-4.1-mini` produced evidence-linked recommendations that survived local validation. The optional explanation was accepted, but all three deterministic rules still failed and the authoritative exit remained `1`. The model explained an already-made decision; it did not change it.

### Rejected model output and deterministic fallback

In [Experiment 8](#trajectory-experiment-8), Terra and Sol each produced output that failed the grounding contract, so rejected text was suppressed and deterministic fallback supplied the usable report. The human then approved [Experiment 9's typed-output redesign](#trajectory-experiment-9). Mini later produced an accepted evidence-linked contribution while local code retained control of facts, measurements, citations, and report rendering.

### Invalid capture evidence discovered and corrected

In [Experiment 13](#trajectory-experiment-13), six JSON captures initially appeared schema-valid, but their sanitized Godot logs exposed script-load failures. Guardian rejected the evidence even though JSON existed and Godot had exited successfully. The consumer script was corrected, captures were repeated, and the intended 2,000-versus-25,000 object/node regression was then measured and failed deterministic policy.

### Human usability checkpoint

In [Experiment 16](#trajectory-experiment-16), the first editor surface used a side dock. The user reported that it covered important Inspector and Node workspace areas. The development agent moved Guardian into Godot's main workspace in [Experiment 17](#trajectory-experiment-17); automated parser, helper, and lifecycle checks passed, and the user then manually confirmed that the corrected interface worked.

## Milestone index

| Stage | Main contribution | Direct trajectory |
| --- | --- | --- |
| Baseline 0 | Deterministic synthetic benchmark and evidence-based documentation | [Baseline and task identity](#trajectory-baseline) |
| Experiment 1 | Validator-gated read-only investigator | [Open](#trajectory-experiment-1) |
| Experiment 2 | Actionable, secret-safe rate-limit diagnosis | [Open](#trajectory-experiment-2) |
| Experiment 3 | Deterministic evidence citations and grounding gate | [Open](#trajectory-experiment-3) |
| Experiment 4 | Schema-driven deterministic fallback | [Open](#trajectory-experiment-4) |
| Experiment 5 | Configurable performance budgets | [Open](#trajectory-experiment-5) |
| Experiment 6 | Portable Godot performance-capture addon | [Open](#trajectory-experiment-6) |
| Experiment 7 | Generic-profile investigator support | [Open](#trajectory-experiment-7) |
| Experiment 8 | Stronger free-form models rejected by grounding | [Open](#trajectory-experiment-8) |
| Experiment 9 | Typed model contribution with deterministic rendering | [Open](#trajectory-experiment-9) |
| Experiment 10 | Unified deterministic CI gate with optional AI | [Open](#trajectory-experiment-10) |
| Experiment 11 | Turnkey reusable consumer workflow | [Open](#trajectory-experiment-11) |
| Experiment 12 | Protected-base pull-request comparison | [Open](#trajectory-experiment-12) |
| Experiment 13 | Script-error rejection and valid object-count regression | [Open](#trajectory-experiment-13) |
| Experiment 14 | Actionable logs, annotations, and job summaries | [Open](#trajectory-experiment-14) |
| Experiment 15 | Deterministic budget calibration proposals | [Open](#trajectory-experiment-15) |
| Experiment 16 | First read-only editor evidence surface | [Open](#trajectory-experiment-16) |
| Experiment 17 | Main-screen Guardian workspace | [Open](#trajectory-experiment-17) |
| Experiment 18 | Reproducible ten-case Baseline 0/final comparison | [Open](#trajectory-experiment-18) |

## Failure-and-correction index

| Failure or correction | What changed | Evidence |
| --- | --- | --- |
| Free-form model output failed grounding | Rejected Terra/Sol text led to typed, locally rendered contributions | [Experiments 8–9](#trajectory-experiment-8) |
| Hosted workflow, Godot path, and hidden-artifact defects | The reusable workflow gained valid YAML, the setup-provided executable, and complete artifact retention | [Experiment 11 and corrections](#trajectory-experiment-11-corrections) |
| JSON existed while the measured scene script had failed | Capture logs became mandatory evidence and script diagnostics invalidate JSON | [Experiment 13](#trajectory-experiment-13) |
| Side dock harmed editor usability | Guardian moved into the main workspace and received manual user acceptance | [Experiments 16–17](#trajectory-experiment-16) |
| Raw-byte integrity depended on Git line endings | Integrity schema v2 canonicalizes UTF-8 line endings before SHA-256 | [Experiment 18 correction](#trajectory-experiment-18-integrity) |

<a id="trajectory-baseline"></a>

## Task identity

- **Task:** Rewrite the Godot Performance Budget Guardian README from repository evidence, record the documentation work, and package the workflow as a repository-local Codex skill.
- **Date:** 2026-08-28.
- **Workspace state at start:** Fresh Git repository with no commits. The benchmark implementation, short README, and validation tooling existed as untracked files. `AGENT_TRAJECTORY.md`, `IMPROVEMENT_CHANGELOG.md`, a license, and a configurable budget file did not exist.
- **Scope boundary:** This trajectory covers the documentation task. Earlier benchmark implementation work is referenced only where its files or verified outputs were used as documentation evidence.

## Original request

<details>
<summary>Verbatim original documentation request</summary>

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

</details>

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

## Follow-up: Integrated improvement changelog

### Request and timeline decision

On 2026-08-28, the user requested a short `IMPROVEMENT_CHANGELOG.md` that records every meaningful experiment, why it was tried, its result under the same evaluation method, the next decision, and lessons from experiments later removed. The user clarified that the baseline is the current repository state.

After repository inspection exposed both earlier calibration results and the absence of a changelog, the agent asked how to reconcile a current-state baseline with a past journey. The user selected **Start baseline now**, meaning earlier implementation tuning would not be reconstructed as post-baseline improvement experiments.

The user then required the existing `$godot-performance-guardian-docs` skill to maintain the improvement changelog whenever invoked and to update the README and trajectory in the same workflow. The revised plan was approved with `PLEASE IMPLEMENT THIS PLAN`.

### Evidence inspected

The agent reread the repository skill, its requirements reference, the skill-creator instructions, the agent-trajectory instructions, the README changelog references, and the end of this trajectory. Existing result files showed two historical CPU workload configurations, but the user-designated timeline starts from the current `240 x 240` configuration.

The accepted baseline values came from the already verified nine-file suite identified by `20260828T193246205Z`: three files each for healthy, node leak, and CPU spike. No Godot process was rerun for this documentation change.

### Changes made

- Updated the repository skill description, workflow, and default prompt so every invocation reviews `README.md`, `AGENT_TRAJECTORY.md`, and `IMPROVEMENT_CHANGELOG.md` together.
- Added an improvement-changelog contract to the skill reference. It requires chronological evidence, consistent evaluation, preservation of failed or removed experiments, and no fabricated entries for documentation-only work.
- Created `IMPROVEMENT_CHANGELOG.md` with the accepted current-state Baseline 0, its evaluation method, verified measurements, decision, planned next direction, and an explicit statement that no post-baseline experiments exist yet.
- Updated README's repository tree, evidence section, and skill description to link and accurately characterize the changelog.

### Verification

The official skill validator completed with:

```text
Skill is valid!
```

PyYAML 6.0.3 was supplied only in a named temporary directory because the validator depends on it but the installed Python environment does not include it. After validation, the directory was removed successfully:

```text
temporary_dependency_removed=True
```

The existing nine-file suite was reevaluated without rerunning Godot:

```text
INFO: median p95 workload: healthy=185.000 usec, cpu_spike=12725.000 usec, ratio=68.78x
INFO: supporting evidence: process p95 healthy=0.605000 ms, cpu_spike=15.075000 ms; duration healthy=4976.010 ms, cpu_spike=7992.353 ms
Validated 9 result files successfully.
```

A separate evidence check recalculated those medians from the saved JSON, confirmed retained-node sets of `[0]` for healthy, `[120]` for node leak, and `[0]` for CPU spike, and matched every displayed changelog value. It also confirmed that both the skill entrypoint and UI prompt route to all three documents, all 13 relative links resolve, and this follow-up exists in the trajectory.

The final text audit checked six documentation and skill files, found README sections 1–17 in order, parsed both JSON examples, confirmed the changelog entry contract, and found no missing links, trailing whitespace, missing final newlines, private paths, or scaffold markers. `git diff --check` reported only Git's Windows line-ending notices and no whitespace error.

No benchmark, documentation, or skill test failed during this follow-up. No Godot process was started. The changelog remains at Baseline 0 because documentation and skill edits are not product-performance experiments.

<a id="trajectory-experiment-1"></a>

## 2026-08-29 follow-up: Read-only performance investigator

### Original request, safety correction, and approval

The user supplied a new implementation request whose opening goal was:

> Implement the first read-only Godot Performance Investigator agent using the OpenAI Agents SDK.
>
> The agent must expose the existing tools/validate_results.py program as a controlled function tool, call it before forming a verdict, and explain the resulting evidence without modifying the Godot project.

The request included an API credential and required that it never appear in the repository. The credential is recorded here only as `[REDACTED]`; it was treated as compromised by disclosure, was never used, printed, written, or passed to a process, and must be revoked outside this repository.

The request required an approval checkpoint before editing. The agent inspected the repository, validator, documentation, Git state, dependency pin, ignore rules, and locally installed SDK interface. It proposed a file-by-file plan for a one-tool investigator, repository-contained path handling, standard-library tests, deterministic validation, and synchronized documentation. The user approved that complete plan with `PLEASE IMPLEMENT THIS PLAN` and explicitly invoked `$godot-performance-guardian-docs` and `$agent-trajectory`.

The approved default model is `gpt-4.1-mini`, overridable through `OPENAI_MODEL`. Live API execution was deliberately excluded because the supplied credential could not be used safely.

### Pre-implementation security scan

At the user's request, API-key patterns were scanned across repository-owned working-tree files, tracked `HEAD`, the staged index, and every reachable commit without printing matches. No repository-owned file, tracked file, staged file, or reachable commit matched. A literal ignored-workspace scan also reported pattern-like strings in four `.venv` package metadata or dependency-source files; no values were printed. The virtual environment remains ignored.

### Evidence and implementation

The agent confirmed:

- `openai-agents==0.22.0` was both installed and pinned in `requirements-agent.txt`.
- `.gitignore` already contained `.venv/`, `.env`, and `.env.*`.
- The installed SDK supports an agent-level required tool choice, resetting that choice after a tool call, `Runner.run_sync`, and a named `function_tool`.
- Existing benchmark results were available for local validation, so no Godot run was needed.

The implementation added `agent/__init__.py`, `agent/investigator.py`, and `tests/test_investigator.py`. The investigator:

- Is named exactly `Godot Performance Investigator`.
- Has one tool named `validate_benchmark_results` and requires a tool call before the model can form its report.
- Wraps the unchanged deterministic validator using `sys.executable`, a fixed resolved validator path, an argument list, no shell, captured output, and a 30-second timeout.
- Rejects empty, absolute, missing, non-directory, JSON-empty, traversal, and resolved escape paths.
- Returns consistent JSON-compatible evidence and removes repository absolute paths from captured process text.
- Reads `OPENAI_API_KEY` only from the environment and exits before the SDK runner when it is absent.
- Requires the five approved report headings and forbids treating validator success as proof of no performance problem or presenting unsupported causes as proven.

An initial eager re-export from `agent/__init__.py` was removed before final verification because it could preload `agent.investigator` when using `python -m agent.investigator`. The package initializer remains intentionally minimal.

### Commands and test evidence

Substantive read-only inspection included:

```powershell
git status --short --branch
rg --files -g '!.venv/**' -g '!.git/**'
Get-Content -Raw tools\validate_results.py
Get-Content -Raw README.md
Get-Content -Raw AGENT_TRAJECTORY.md
Get-Content -Raw IMPROVEMENT_CHANGELOG.md
Get-Content -Raw requirements-agent.txt
Get-Content -Raw .gitignore
.\.venv\Scripts\python.exe -c "<inspect installed Agents SDK signatures>"
```

The standard-library unit suite ran without an API request:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

```text
Ran 16 tests in 0.270s

OK
```

The unchanged validator was run directly over the existing result directory:

```powershell
.\.venv\Scripts\python.exe .\tools\validate_results.py .\demo_project\results
```

```text
INFO: median p95 workload: healthy=148.000 usec, cpu_spike=8549.000 usec, ratio=57.76x
INFO: supporting evidence: process p95 healthy=0.408000 ms, cpu_spike=12.588500 ms; duration healthy=4976.010 ms, cpu_spike=6406.270 ms
Validated 21 result files successfully.
```

The 21-file set is larger than the accepted nine-file Baseline 0, so these aggregate measurements are recorded as current regression-safety evidence rather than a replacement baseline.

The CLI was invoked with `OPENAI_API_KEY` explicitly absent:

```powershell
$env:OPENAI_API_KEY = $null
.\.venv\Scripts\python.exe -m agent.investigator demo_project\results
```

It stopped locally with `ERROR: OPENAI_API_KEY is not configured.` No API request occurred. No automated test failed during the initial implementation run.

### Documentation classification and remaining verification

The repository documentation now classifies the investigator as implemented and locally tested, while classifying live SDK execution and report quality as unverified. `IMPROVEMENT_CHANGELOG.md` retains Baseline 0 and adds the investigator as the first post-baseline product experiment; it does not present documentation edits as performance experiments.

Final link, skill, secret-pattern, whitespace, diff, and repeated unit verification remained to be completed at the time of this chronological entry.

### Final verification result

The final unit run completed successfully:

```text
Ran 16 tests in 0.274s

OK
```

The direct validator again passed all 21 stored result files with the same 57.76× workload ratio and supporting values recorded above. Python byte-compilation of the agent and test modules also succeeded.

The repository skill's official `quick_validate.py` script was present, but both available Python runtimes lacked its undeclared `yaml` dependency. The first sandboxed attempt to install PyYAML 6.0.3 into a uniquely named temporary directory failed because network access was blocked. After approved network access, the dependency was installed only in a new temporary directory, the validator printed `Skill is valid!`, and the directory was removed after its resolved path was verified to remain under the system temporary root. No temporary dependency directory remained.

The final documentation audit found all README sections 1 through 17 in order, resolved all 11 relative links, and confirmed every expected implementation and evidence file exists. It found no trailing whitespace, missing final newline, private absolute path, scaffold marker, or key-shaped value in repository-owned files. The dedicated key-pattern scan also found no match in the repository working tree excluding `.venv`, tracked `HEAD`, the staged index, or any reachable commit.

`git diff --check` reported no whitespace error; Git emitted only its existing Windows line-ending conversion warnings. The final Git status retained the user's pre-existing documentation, skill, ignore-rule, changelog, and dependency changes alongside the new `agent/` and `tests/` directories. Nothing was committed or pushed, and the Godot benchmark was not rerun.

### Result and remaining uncertainty

The approved read-only investigator, restricted validator tool, path controls, failure handling, tests, README update, product experiment entry, and task trajectory are implemented and locally verified. The deterministic validator remains unchanged and authoritative.

A live OpenAI API call was not made. Whether the selected model produces consistently useful, evidence-grounded reports remains unverified and is the recommended next experiment with a newly issued environment-only key.

## 2026-08-29 follow-up: Correct configured Git remote documentation

### User correction and verified evidence

The user reported that README's statement about having no configured Git remote was stale and required the repository documentation skill to prevent the same error in future updates.

The agent invoked `$godot-performance-guardian-docs`, reread `README.md`, `AGENT_TRAJECTORY.md`, `IMPROVEMENT_CHANGELOG.md`, the skill entrypoint, and its complete README requirements reference. It then ran:

```powershell
git remote -v
git remote get-url origin
git remote get-url --push origin
git status --short --branch
```

Both the fetch and push configuration for `origin` resolved to:

```text
https://github.com/TaofeekS/godot_performance_guardian.git
```

### Documentation and skill changes

- Replaced README's stale no-remote statement and `<repository-url>` placeholder with a copyable clone command using the verified `origin` fetch URL.
- Strengthened the skill entrypoint so every documentation run must inspect Git remotes, prefer a configured fetch URL, fall back to a labeled placeholder only when no remote exists, and avoid exposing embedded authentication.
- Added the same remote-source and credential-safety requirements to the detailed README contract and verification checklist.
- Left `IMPROVEMENT_CHANGELOG.md` unchanged because correcting documentation and its maintenance workflow is not a product experiment.

Final skill, remote, link, formatting, secret-pattern, and diff verification followed these edits.

### Verification result

The post-edit remote check confirmed that the README clone URL exactly matches the configured `origin` fetch URL and that fetch and push URLs remain identical. Searches found no stale `no configured Git remote` statement or `<repository-url>` placeholder in README.

The official repository-skill validator printed:

```text
Skill is valid!
```

As in the preceding documentation task, PyYAML 6.0.3 was supplied only in a uniquely named system-temporary directory and removed after validation. The final documentation audit found README sections 1 through 17 in order, resolved all 11 relative links, and found no trailing whitespace, missing final newline, or key-pattern match in repository-owned files. `git diff --check` reported no whitespace error beyond Git's existing Windows line-ending notices.

No clone, commit, push, Godot run, benchmark validation, or OpenAI API request occurred. `IMPROVEMENT_CHANGELOG.md` was inspected and deliberately left unchanged.

<a id="trajectory-experiment-2"></a>

## 2026-08-29 follow-up: Actionable rate-limit diagnosis

### Reported failure and approved response

The user reported this investigator output after configuring a key:

```text
Error getting response
ERROR: investigator run failed (RateLimitError).
```

The existing CLI was inspected and found to catch every model exception generically, retaining only its class name. Consequently, it could not distinguish temporary throttling from an API project with no available quota.

The agent used the `openai-docs` workflow. Official documentation searches and direct page fetches for API error codes and rate limits returned no content in the available web tool, so no current account-specific limit or billing claim was inferred from those pages. Local inspection of the installed `openai==3.6.0` exception and client code established the implementable interface: `RateLimitError` carries status, code, type, request ID, and response headers, while the client default is two retries for HTTP 429. The current Codex process had no API key configured, consistent with the reported failure occurring in the user's separate terminal.

The user approved a plan to add allowlisted diagnostics and selected **Diagnose and stop**, explicitly rejecting an additional application retry after the SDK's built-in attempts.

### Implementation

`agent/investigator.py` now catches `RateLimitError` before the generic safe fallback. Its formatter accepts only restricted alphanumeric API metadata and finite nonnegative numeric retry delays. It never emits the raw exception message, body, prompt, request, authorization header, or arbitrary response header.

The handler classifies `insufficient_quota` as an API billing, credit, or project-limit issue for which retrying is ineffective. Other 429 responses are described as throttling after built-in retries, with a server-provided numeric wait when available. Automatic model switching and application-level retry were deliberately omitted.

Four tests were added with constructed local `RateLimitError` instances and mocked `Runner.run_sync`. Their embedded sentinel values verify that credential-like environment content, request authorization, response authorization, raw error messages, and response-body content do not reach stderr. The runner call count remains one.

### Verification evidence

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

```text
Ran 20 tests in 0.298s

OK
```

```powershell
.\.venv\Scripts\python.exe .\tools\validate_results.py .\demo_project\results
```

```text
INFO: median p95 workload: healthy=148.000 usec, cpu_spike=8549.000 usec, ratio=57.76x
INFO: supporting evidence: process p95 healthy=0.408000 ms, cpu_spike=12.588500 ms; duration healthy=4976.010 ms, cpu_spike=6406.270 ms
Validated 21 result files successfully.
```

Python byte-compilation of the edited agent and test modules succeeded. No live API request or Godot run occurred. README now distinguishes missing credentials, rejected authentication, insufficient quota, transient rate limiting, and model access failures. `IMPROVEMENT_CHANGELOG.md` records this as Experiment 2 because it materially changes runtime diagnosis rather than merely documenting existing behavior.

Final skill, link, secret-pattern, whitespace, and Git-state checks remained to be completed after this chronological entry.

### Final verification result

The official repository documentation-skill validator printed `Skill is valid!`. Its PyYAML 6.0.3 dependency was installed only into a uniquely named, verified system-temporary directory and removed after the check.

The documentation audit found README sections 1 through 17 in order, resolved all 11 relative links, and confirmed the documented clone URL still matches the configured `origin` fetch URL. No trailing whitespace, missing final newline, or temporary dependency directory remained.

The final key-pattern scan found no match in repository-owned working-tree files, tracked `HEAD`, the staged index, or any reachable commit. `git diff --check` reported no whitespace error beyond Git's existing Windows line-ending warnings. All user changes remained uncommitted for review.

No test failed. No application-level retry, automatic model fallback, live API request, Godot run, commit, or push occurred. A successful investigator response still depends on a newly issued key whose API project has available quota and access to the selected model.

<a id="trajectory-experiment-3"></a>

## 2026-08-29 — Experiment 3: Deterministic investigator evidence grounding

### Original request and approval

The documentation attachment opened with this request verbatim:

> # Goal
>
> Implement Experiment 3: deterministic evidence grounding for the Godot Performance Investigator.
>
> The first live investigator report is the “before” result for this experiment. It completed successfully and reported accurate measurements, but it introduced unsupported explanations and omitted relevant node-leak evidence.
>
> The improved investigator must constrain its important claims to deterministic evidence returned by its tool.

The supplied request then specified the complete evidence-packet fields, grounding rules, safety boundary, fourteen test requirements, evaluation target, documentation routing, and completion criteria. Its recorded “before” evidence was 21 validated files, healthy/CPU-spike median p95 workload values of 148 µs and 8,549 µs, a 57.76× ratio, process p95 values of approximately 0.408 ms and 12.589 ms, and durations of approximately 4,976 ms and 6,406 ms. The reported deficiencies were omitted node-leak evidence, no connection to the intentional CPU workload, unsupported thermal/scheduling/locking/contention explanations, and a stated 25% duration increase where the values calculate to approximately 28.7%.

Before approval, the agent inspected Git state, the investigator, validator, benchmark controller, all scenario result shapes, tests, README, improvement changelog, trajectory, installed SDK behavior, and the 21-file aggregates. It proposed extending the validator because that was the smallest way to reuse its already-loaded and validated dataset without copying validation calculations into the agent.

The user then required this exact sentence in the plan summary:

> The original agent produced an apparently useful but partly speculative report. Experiment 3 adds deterministic evidence citations and automatically blocks ungrounded reports.

The revised plan was approved verbatim through the implementation request. It preserved the sole function-tool boundary, normal validator CLI, existing assertions, no-retry policy, benchmark implementation, stored results, and prohibition on Godot reruns, commits, pushes, unrelated access, and credential exposure.

### Implementation and evidence design

The agent invoked `$godot-performance-guardian-docs` and `$agent-trajectory`, read both supplied skill entrypoints completely, and read the documentation skill's complete requirements reference before documentation edits.

`tools/validate_results.py` gained an opt-in `--evidence-json` mode. The default command retains its existing human-readable messages and exit code. Structured mode uses the same loaded results, per-file assertions, grouping, and cross-run statistics, then emits ordered IDs `E1` through `E22`. These cover validation count; workload, process, and duration medians; ratios and percentage changes; cleanup evidence for all scenarios; actor and leak configuration; mixed CPU configurations; and narrowly allowlisted current controller behavior. Failed validation emits no verified evidence.

The packet records repository-relative sources and explicit limitations: passing configured checks is not proof that no other problem exists; the stored set mixes historical CPU configurations; stored JSON lacks a source revision/hash; headless synthetic evidence does not establish GPU performance; and the available evidence does not establish root cause.

`agent/investigator.py` continues to expose only `validate_benchmark_results`. It now parses the structured validator packet and converts invalid packets, timeouts, and operational failures into evidence-empty error packets. Instructions require `[E#]` citations, every scenario, supported causal language, read-only evidence-linked recommendations, and the exact root-cause uncertainty sentence.

After the SDK returns, the CLI extracts the packet actually produced by the tool call and applies a deterministic local gate to the five-section report. The gate checks heading order, citations, supported numeric presentation, scenario coverage, validation-status consistency, causal language, uncertainty, and recommendation safety. It prints only stable grounding-rule identifiers on rejection, never the rejected report, and does not retry.

### Commands, test failure, and response

The substantive local commands used during implementation were:

```powershell
.\.venv\Scripts\python.exe .\tools\validate_results.py .\demo_project\results
.\.venv\Scripts\python.exe .\tools\validate_results.py --evidence-json .\demo_project\results
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m py_compile .\agent\investigator.py .\tools\validate_results.py .\tests\test_investigator.py
git remote -v
git status --short
```

The first expanded unit run executed 29 tests and produced one real failure: the valid grounded-report fixture was flagged with `G07_UNSUPPORTED_NUMBER`. A diagnostic showed that the numeric scanner interpreted the `5` in `p95` and partial values after the `x` in `160x160` and `240x240` as standalone measurements. The scanner was corrected to exclude digits embedded in identifiers and to normalize numeric workload-dimension separators before extraction. The bad 25% fixture remained rejected.

Two further cases were then added: malformed validator output must become an evidence-empty safe error, and a safe five-section validation-failure report must remain possible when no evidence IDs exist.

The next run completed successfully:

```text
Ran 31 tests in 1.050s

OK
```

Python byte-compilation also completed successfully. The normal validator output remained:

```text
INFO: median p95 workload: healthy=148.000 usec, cpu_spike=8549.000 usec, ratio=57.76x
INFO: supporting evidence: process p95 healthy=0.408000 ms, cpu_spike=12.588500 ms; duration healthy=4976.010 ms, cpu_spike=6406.270 ms
Validated 21 result files successfully.
```

Canonical structured output was generated repeatedly and compared in tests. The packet calculated a 28.743109% median-duration increase, reported 120 retained nodes across all six node-leak runs, zero across all nine healthy runs, and zero across all six CPU-spike runs. It also identified three `160x160` and three `240x240` CPU-spike results.

### Documentation and current remaining uncertainty

The repository documentation skill synchronized README's current status, evaluation contract, evidence limitations, and hackathon links. `IMPROVEMENT_CHANGELOG.md` retained all prior entries and appended Experiment 3 with the supplied live report as its “before” evaluation. Documentation-only history remains here rather than being represented as a product experiment.

The environment check reported only whether configuration existed and did not inspect or print any credential. `OPENAI_API_KEY` was absent and `OPENAI_MODEL` was unset, so the default remains `gpt-4.1-mini` and no post-change live request was made. The fixed local report fixtures establish that known unsupported output is blocked; they do not establish the quality of a future live model response.

Final skill, link, secret-pattern, deterministic-output, whitespace, and Git-state verification followed this entry.

### Final verification result

A final grounding case was added after review to ensure that nonnumeric statements in Validation status and Verified facts also require evidence citations. The complete suite then reported:

```text
Ran 32 tests in 1.087s

OK
```

The unchanged human-readable validator again passed all 21 files with the same 57.76× workload ratio and supporting measurements shown above. Two independent structured invocations produced identical canonical JSON. Python byte-compilation succeeded.

The documentation skill's official `quick_validate.py` printed `Skill is valid!`. Its PyYAML 6.0.3 dependency was installed only in a uniquely named system-temporary directory and that directory was removed. PowerShell's `New-Item -LiteralPath` invocation emitted a non-test parameter error before `pip --target` created the directory itself; validation still completed successfully and the guarded cleanup verified the removal target before deleting it.

The documentation audit resolved all 15 README links, found every required source and skill file, confirmed final newlines and no trailing whitespace, and reconfirmed that the documented clone URL matches the configured `origin` fetch URL. Filename-only scans found no API-key-pattern match in the working tree, tracked files, staged content, or reachable history. `git diff --check` reported no whitespace error, only Git's existing Windows line-ending notices.

No Godot run, post-change live API request, commit, or push occurred. The implementation and deterministic local controls are verified; the quality and 4/4 rubric result of a future grounded live report remain unverified.

<a id="trajectory-experiment-4"></a>

## 2026-08-29 — Experiment 4: Schema-driven deterministic fallback

### Reported live failure and planning

The user reported this exact grounding result from a live investigator run:

```text
ERROR: investigator grounding failed (G03_REQUIRED_EVIDENCE_MISSING,G04_SCENARIO_COVERAGE,G07_UNSUPPORTED_NUMBER,G08_REQUIRED_UNCERTAINTY,G11_UNCITED_RECOMMENDATION,G13_UNTESTABLE_RECOMMENDATION).
```

Inspection confirmed that the API and deterministic validator had completed, but the model report failed six literal post-generation checks. The rejected report itself was unavailable by design, so no claim was made about its exact wording. The agent identified a prompt–gate mismatch: the gate required a fixed set of citations, literal scenario tokens, evidence-compatible numeric presentation, an exact uncertainty sentence, cited recommendations, and a narrow action-verb allowlist.

The user selected a safe deterministic fallback rather than relaxing the evidence boundary. The first plan was then corrected with this requirement:

> avoid permanent dependecies on the exact e1 to e22
>
> Report source: Deterministic fallback generated after model output failed grounding.
>
> Before Experiment 4, rejected model output produced no usable investigation. After Experiment 4, the same failure produces a deterministic, fully cited report without another API request.

The revised schema-driven plan was approved in full. It treats IDs as opaque citation labels and makes metric, scenario, source type, unit, and value shape the stable interface.

### Implementation

`agent/investigator.py` gained a semantic evidence resolver with sixteen required categories covering validation count; workload, process, and duration comparisons; retained-node evidence for all scenarios; CPU configuration; and allowlisted behavior for healthy, node-leak, and CPU-spike. It rejects missing, ambiguous, duplicate-ID, wrong-unit, or wrong-value-shape evidence without exposing packet contents in CLI errors.

The grounding gate now derives required citations and causal-source citations from those semantic matches rather than hard-coded `E` numbers. Citation parsing accepts safe opaque labels. Renumbering items or adding unrelated evidence does not alter report meaning.

A deterministic fallback renderer uses only resolved packet values and their actual IDs. It includes the exact report-source disclosure, all five sections, all scenarios, evidence-linked explanations and read-only investigations, the validator limitation, and the exact root-cause uncertainty statement. The same gate validates it before output.

When model output is rejected, stderr contains only a warning and rule identifiers; the rejected text is not emitted. The fallback is printed without a second SDK call. Passed deterministic validation returns zero, while failed validation produces an evidence-empty report and remains nonzero. Missing packets and invalid semantic schemas continue to fail safely.

### Test failures and response

The first implementation run executed 32 tests and failed five. Current repository evidence had expanded from the 21-file Experiment 3 set to 31 files, including 13 healthy, nine node-leak, and nine CPU-spike results. Historical tests still expected 21 files, six leak runs, and the earlier aggregate numbers. Another test still expected rejected reports to exit nonzero with empty stdout, and the instruction test still expected literal `[E1]` wording.

The failures were not benchmark-validator failures. The direct validator passed all 31 files. Tests were changed to recompute expected aggregates and run counts from the current JSON set, resolve evidence semantically, and assert the new fallback contract. This removed fixed result-count and evidence-number coupling.

The next run executed 38 tests and had one remaining instruction-string mismatch caused by a changed line wrap. That assertion was updated to check the semantic wording rather than formatting. Review then found that an already grounded validation-failure report still returned zero on the normal output path. The CLI exit logic was corrected and a regression test was added.

### Verified local result

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m py_compile .\agent\investigator.py .\tools\validate_results.py .\tests\test_investigator.py
.\.venv\Scripts\python.exe .\tools\validate_results.py .\demo_project\results
```

```text
Ran 39 tests in 1.319s

OK
```

```text
INFO: median p95 workload: healthy=163.000 usec, cpu_spike=11510.000 usec, ratio=70.61x
INFO: supporting evidence: process p95 healthy=0.605000 ms, cpu_spike=12.537000 ms; duration healthy=4976.010 ms, cpu_spike=7285.752 ms
Validated 31 result files successfully.
```

Two structured validator invocations produced identical canonical JSON. Python byte-compilation succeeded. The fallback itself passed the same grounding gate, used renumbered IDs automatically, ignored unrelated evidence, failed safely on missing or duplicate semantic matches, emitted no rejected sentinel text, and invoked the mocked SDK runner exactly once.

The repository documentation skill and agent trajectory skill were used for the synchronized README, Experiment 4 changelog, and this chronological record. `OPENAI_API_KEY` was absent from the implementation process, so no live request occurred. Final skill, link, secret-pattern, whitespace, and Git-state checks followed this entry.

### Final verification result

The documentation skill's official validator printed `Skill is valid!`. PyYAML 6.0.3 was supplied only through a uniquely named system-temporary directory, which was removed after validation. No temporary validation directory remained.

The final README audit found all 17 numbered sections, resolved all 15 Markdown links, confirmed the clone URL still matches the configured `origin` fetch URL, and found no trailing whitespace or missing final newline. Filename-only secret-pattern scans found no match in the working tree, tracked files, staged content, or reachable history. `git diff --check` reported no whitespace error; Git emitted only its existing Windows line-ending notices.

Five repository files were modified for Experiment 4: the investigator, its tests, README, improvement changelog, and trajectory. The benchmark controller and validator were unchanged. No Godot run, live API request, commit, or push occurred.

<a id="trajectory-experiment-5"></a>

## 2026-08-29 — Experiment 5: Configurable performance budgets

### Original request and approval

The user first supplied the Experiment 5 goal and added this exact correction:

> Create budgets/example_budgets.json using this exact v1 schema. The completed example file must contain the four demonstration rules listed below.

The final approved implementation request began:

> PLEASE IMPLEMENT THIS PLAN:
> # Experiment 5: Configurable Performance Budgets
>
> Add a standard-library-only checker that compares validated evidence with configurable project budgets and produces deterministic local/CI pass-fail results without AI.
>
> The validator, investigator, Godot scenarios, and stored results remain unchanged.

It required the exact four-rule example, semantic evidence matching rather than `E`-number coupling, strict configuration validation, deterministic human and canonical JSON modes, exit codes `0`/`1`/`2`, fixed-fixture standard-library tests, documentation through `$godot-performance-guardian-docs`, and this execution history through `$agent-trajectory`. It prohibited Godot reruns, API-key inspection or use, API requests, added dependencies, commits, and pushes.

### Inspection and design evidence

The agent read both invoked skills completely, including the documentation skill's complete README requirements reference. It inspected `README.md`, `AGENT_TRAJECTORY.md`, `IMPROVEMENT_CHANGELOG.md`, Git status and the configured remote, the validator's structured packet contract, existing investigator semantic matching, tests, and the current stored evidence. The pre-change working tree was clean and `origin` still used `https://github.com/TaofeekS/godot_performance_guardian.git` for fetch and push.

The current validator evidence contained 40 files and exposed the required aggregate metrics as unique semantic items. The design therefore kept all benchmark calculations in `tools/validate_results.py`: the new checker invokes `--evidence-json`, rejects failed or malformed packets, and evaluates only validated items selected by metric, scenario, source type, and unit. Evidence IDs are retained in output as opaque traceability labels.

### Implementation

The implementation added exactly three runtime/test artifacts before documentation:

- `budgets/example_budgets.json`, containing the four rules and field values approved by the user.
- `tools/check_budgets.py`, using only the Python standard library and a fixed validator subprocess with no shell.
- `tests/test_check_budgets.py`, using synthetic evidence packets and mocks rather than exact expectations from the changing result directory.

The checker rejects missing or unknown fields, unsafe or duplicate IDs, unsupported metric/scenario pairs, wrong units, empty descriptions, and nonfinite, Boolean, or negative limits. It requires unambiguous semantic evidence with the declared source type and unit, preserves matched evidence IDs and validator limitations, sorts results by budget ID, and treats equality as a pass. Human output and canonical JSON share one evaluated result. Exit code `0` means all budgets passed, `1` means valid evidence produced policy failures, and `2` means configuration, evidence, validation, or execution failed.

The Godot project, stored results, validator, and investigator were not modified.

### Tests, failures, and responses

The first complete test run executed 56 tests and found one presentation-only failure: the human renderer printed `PASSED` and `FAILED`, while its test expected the concise `PASS` and `FAIL` labels. The renderer was corrected and packet schema-version validation was added. The final suite then reported:

```text
Ran 57 tests in 1.579s

OK
```

Python byte-compilation of the checker and its tests also succeeded. A final source review then found that `description` was optional even though the approved exact v1 rule shape requires it. The parser and fixed tests were tightened, and the complete 57-test suite still passed in 1.601 seconds.

The unchanged validator and real example policy were then run:

```powershell
.\.venv\Scripts\python.exe .\tools\validate_results.py .\demo_project\results
.\.venv\Scripts\python.exe .\tools\check_budgets.py .\demo_project\results .\budgets\example_budgets.json
```

The validator passed all 40 existing files with healthy/CPU-spike median p95 workload of 166/11,771.5 µs (70.91×), process p95 of 0.8115/13.112 ms, and duration of 4,976.0085/7,577.4265 ms. The policy result was exactly two passes and two intentional failures:

```text
PASS: healthy-process-p95
PASS: healthy-retained-nodes
FAIL: cpu-spike-workload-p95
FAIL: node-leak-retained-nodes
BUDGET_CHECK_EXIT=1
```

The sorted human display placed the CPU-spike rule first by ID. A first JSON repeat-check script failed because it assumed result fields named `id` and `fail`; the implemented contract uses `budget_id` and `failed`. After inspecting the actual safe field names and correcting only the verification harness, two independent JSON-mode invocations were byte-identical, returned `1`, and identified only the two intended failures.

### Documentation synchronization

The repository documentation skill synchronized all three maintained documents. README now distinguishes deterministic evidence validation, configurable project policy, and optional AI investigation; documents the exact schema, supported metrics, commands, output, exit behavior, tree entries, current integration evidence, limitations, and roadmap status. `IMPROVEMENT_CHANGELOG.md` retains the earlier history and appends Experiment 5 as a product change. This trajectory records documentation operations and the two corrected verification assumptions rather than presenting them as performance experiments.

The official documentation-skill validator initially could not start because its own undeclared `yaml` dependency was absent. PyYAML 6.0.3 was installed only into a uniquely named, verified system-temporary directory. The validator printed `Skill is valid!`, and the temporary directory was removed immediately and verified absent.

Final link, Markdown, secret-pattern, whitespace, and Git-state verification follows this entry. No Godot run or API request occurred.

### Final verification result

The final unchanged validator invocation passed all 40 stored result files. The example checker again returned the expected policy exit `1`, with only `cpu-spike-workload-p95` and `node-leak-retained-nodes` failing. Two fresh canonical JSON invocations were byte-identical.

The first README audit command incorrectly collected only the first numbered heading because it addressed `MatchCollection.Groups` without enumerating matches. The corrected audit enumerated all matches. A second harness check used PowerShell's literal backtick inside a single-quoted regular expression and falsely identified lines ending in the letter `t` as trailing whitespace; `rg` showed no actual match, and the corrected `\t` expression passed. Neither harness issue identified or required a repository-content fix.

The final documentation audit resolved all 20 relative README links, confirmed all 17 numbered sections in order, found every required artifact, verified final newlines and no trailing whitespace, and reconfirmed that the documented clone URL matches both configured `origin` URLs. Filename-only secret-pattern scans found no match in the working tree, tracked files, staged content, or reachable Git history. `git diff --check` returned zero; Git printed only its existing Windows line-ending notices.

Git status contained only the three synchronized documentation files and the three intended Experiment 5 additions. No validator, investigator, Godot project, stored result, documentation-skill source, or dependency file changed. No Godot run, API-key value access, API request, added permanent dependency, commit, or push occurred.

<a id="trajectory-experiment-6"></a>

## 2026-08-29 — Experiment 6: Portable Godot 4.5 performance capture addon

### Original request, corrections, and approval

The supplied request began:

> # Goal
>
> Implement Experiment 6: Portable Godot 4.5 Performance Capture Addon.
>
> Convert the existing project-specific measurement capability into a small reusable Godot 4.5 addon. Prove that a developer can copy it into an unrelated fresh Godot project, collect performance measurements headlessly, validate the output and apply configurable performance budgets.
>
> Do not use [unrelated private project].

The unrelated private-project name is redacted from this repository record; no source, asset, data, or telemetry from that project was accessed or used.

It required an inspection and approval checkpoint before edits. The agent inspected the complete benchmark implementation, validator, budget checker, tests, representative results from all three scenarios, documentation, Git state, remote, and local Godot executable. The working tree was clean at `cdfdd7f`; 49 ignored historical files comprised 19 healthy, 15 node-leak, and 15 CPU-spike results. Their validator exited `0`, while the unchanged Experiment 5 policy exited `1` with its two intentional failures.

The agent compared a separate validator, an adapter, and backward-compatible schema dispatch. It recommended explicit synthetic/generic paths in the existing validator because a separate tool would duplicate calculations and an adapter could invent workload or cleanup meaning. The user selected an install-then-clean addon copy for the independent example and requested one tracked sanitized fixture. The final correction stated:

> If an explicitly supplied run ID already exists, preserve the file, exit with code 3 and require the caller to provide a new run ID.

The complete revised plan was then approved with `PLEASE IMPLEMENT THIS PLAN` and explicit invocations of `$godot-performance-guardian-docs` and `$agent-trajectory`.

### Implementation

The canonical addon was created under `addons/performance_budget_guardian/` with version `1.0.0`, editor registration, runtime probe, and focused installation documentation. The probe validates safe identifiers, revision text, numeric bounds, and `res://` output paths; captures generic engine metrics after configurable warmup; keeps raw samples and recalculated summaries together; records metric availability and limitations; writes atomically; and returns `2` for configuration errors or `3` for output collisions. It does not record workload time or synthetic cleanup/ownership fields.

The independent `examples/minimal_project/` uses deterministic primitive-only 2D activity seeded with `1337`. Its scene references the addon at the normal consumer path, which is populated by an ignored copy during verification. The project contains GDScript helper tests, an ignored runtime-results location, and a calibrated schema-v2 profile policy.

`tools/validate_results.py` gained explicit generic schema validation and profile evidence while retaining the synthetic path. Mixed input types fail. `tools/check_budgets.py` now accepts v1 scenario rules or v2 profile rules and semantically matches the corresponding evidence. The investigator was not modified. `tests/test_portable_addon.py` uses fixed synthetic capture fixtures and later the tracked live fixture rather than depending on the growing demo result directory.

### Test failures and operational issues

The initial 65-test Python suite passed; no Python test failed.

The first Godot command used a relative custom `--log-file`. On this Windows invocation Godot attempted an invalid `user://C:` directory and crashed before project verification. No capture was produced. Removing custom log handling exposed normal sandbox-only AppData permission messages and one real plugin defect: `plugin.cfg` used a `res://` script path even though Godot resolves that field relative to the addon, producing a doubled path. The manifest was corrected from the full resource path to `plugin.gd`.

Godot was then run with normal user-data access and `Start-Process -Wait -PassThru`. The editor parse and GDScript helper tests both exited `0`.

After the live run, the first sanitization audit falsely treated the intended `res://results` value as a drive path because its regular expression matched the `s:/` substring. No fixture was copied during that failed audit. The check was restricted to drive prefixes at the start of a string while explicitly allowing `res://`; it then found no unsafe field and the unchanged capture was copied.

Review also found that collision detection occurred only when writing after measurement. The probe was tightened to check its resolved target immediately after argument validation. A second invocation using `portable-run-001` then exited `3` before measurement, and hashing confirmed the live result remained byte-identical to the canonical fixture.

### Verified capture and compatibility evidence

Exactly one performance capture was made with:

```powershell
& $GodotExe --headless --path .\examples\minimal_project -- --pbg-profile=main_scene --pbg-run-id=portable-run-001 --pbg-output=res://results --pbg-auto-quit
```

It exited `0` and produced `examples/minimal_project/results/portable-run-001.json`. Generic validation exited `0` for 600 sequential samples covering frames 1–600. The result recorded process p95 `0.529 ms`, peak global nodes `3`, measurement duration `4140.02 ms`, capture duration `4949.63 ms`, five limitations, `source_revision: null`, and no temporary files or private absolute paths.

The deterministic calibration rule produced `1.1 ms` and `3 nodes`. Both v2 budgets passed with exit `0`. The clean live file was preserved unchanged as `examples/fixtures/main_scene-godot-4.5.1.json`, and that fixture also validated with exit `0`.

The compatibility commands reported:

```text
GENERIC_VALIDATION_EXIT=0
GENERIC_BUDGET_EXIT=0
SYNTHETIC_VALIDATION_EXIT=0
SYNTHETIC_BUDGET_EXIT=1
```

All 49 historical files retained their original assertions. The Experiment 5 policy still failed only `cpu-spike-workload-p95` and `node-leak-retained-nodes`. Repeated generic evidence and budget JSON outputs were byte-identical. The complete suite before the final fixture-specific test reported 65 tests passed in 2.230 seconds; a final complete run follows documentation synchronization.

### Documentation synchronization and remaining limits

The repository documentation skill updated README's installation, CLI, exported behavior, schemas, policy versions, verified evidence, tree, limitations, and roadmap. `IMPROVEMENT_CHANGELOG.md` appended Experiment 6 and included the user-approved portability statement only after the addon copy, live measurement, validation, and budget enforcement all succeeded. This trajectory preserves the implementation chronology and operational failures.

The claim is limited to the included independent project on Godot `4.5.1.stable.official.f62fdbde1`. Rendering/GPU performance, other operating systems, other projects, broader fixture coverage, and an editor dock remain unverified or planned. No original benchmark run, API-key inspection, API request, dependency addition, investigator change, commit, or push occurred.

### Final verification result

The final suite passed all 66 tests in 2.232 seconds, including the canonical live fixture and its v2 budget. Python byte-compilation succeeded. The official documentation-skill validator first failed to import its undeclared `yaml` dependency; PyYAML 6.0.3 was then supplied only in a verified system-temporary directory. The skill printed `Skill is valid!`, and the directory was removed immediately.

The copied consumer addon directory was resolved beneath `examples/minimal_project/` and removed after Godot verification. The ignored live result and tracked canonical fixture were preserved. Final README links, Markdown structure, command/schema evidence, secret patterns, whitespace, and Git state were audited after this entry.

A final source audit then found that the GDScript safety helpers passed `false` for `String.split`'s empty-segment behavior. Doubled separators could therefore be normalized before rejection, although the Python validator would reject the resulting capture. Both helpers were changed to retain empty segments, two GDScript assertions were added, and the non-capture helper suite was rerun before cleanup.

That final helper run exited `0`, and its ignored addon copy was again removed from the verified example-project path. The subsequent complete Python suite passed 66 tests in 2.232 seconds.

The final audit resolved all 26 relative README links, confirmed the 17 numbered sections in order, matched the documented clone URL to both configured `origin` URLs, validated the canonical fixture again, and found final newlines with no trailing whitespace. Filename-only API-key scans found no match in the working tree, tracked files, staged content, or reachable history. The unrelated private-project name was also absent. `git diff --check` returned `0`; Git emitted only its existing Windows line-ending notices.

Final status contained the intended addon, independent example, canonical fixture, portable-addon tests, validator/checker extensions, and three synchronized evidence documents. The ignored live result remains at `examples/minimal_project/results/portable-run-001.json`; the ignored installation copy is absent. Protected investigator, original demo, historical result, dependency, and Experiment 5 budget files were unchanged.

## 2026-08-29 — Experiment 6 probe-memory clarification

### User correction and approved plan

The user identified an evidence-interpretation limitation:

> Because the probe accumulates raw samples during capture, static-memory growth includes probe storage overhead and cannot by itself prove a project memory leak.

The approved follow-up required that exact statement in every generic capture, mandatory generic validation, a patch-version increment, a fixture update without changed measurements, comparable-capture guidance for memory budgets, synchronized documentation and skill requirements, and verification without rerunning Godot.

### Implementation

The addon version changed from `1.0.0` to `1.0.1` in both runtime and plugin metadata. `PerformanceBudgetProbe` now includes the exact storage-overhead statement in `known_limitations`. Generic validation requires the statement, while synthetic validation is unchanged. The generic evidence packet also preserves the limitation so both human and JSON budget output disclose it.

The canonical fixture's addon metadata and limitation list were updated without changing any sample, summary, timestamp, or measured value. Fixed tests now prove that generated-source text contains the caveat, valid fixtures include it, omission fails generic validation, and the generic evidence packet carries it. README, the addon README, the documentation-skill requirements, and Experiment 6's changelog entry now distinguish a comparable memory regression signal from proof of a project leak.

### Verification and operational issue

The targeted portable-addon suite passed 10 tests. The complete suite then reported:

```text
Ran 67 tests in 1.937s

OK
```

The canonical fixture validated with exit `0`, its two v2 budgets passed with exit `0`, and canonical generic evidence and budget JSON remained byte-identical across repeated invocations. All 49 historical synthetic results validated with exit `0`. The unchanged Experiment 5 policy returned its expected exit `1`, with only `cpu-spike-workload-p95` and `node-leak-retained-nodes` failing. Python byte-compilation succeeded.

The first documentation-skill validation attempt encountered two operational issues: `New-Item` did not accept the attempted `-LiteralPath` parameter, and sandboxed network access prevented temporary PyYAML retrieval. No repository file was affected. The corrected command used `-Path`, received approval for the download, installed PyYAML 6.0.3 only into a uniquely named system-temporary directory, printed `Skill is valid!`, and removed the directory in `finally` after verifying that its resolved path remained under the system temporary root.

No Godot run, API request, credential access, permanent dependency, commit, or push occurred. Final link, Markdown, secret-pattern, whitespace, and Git-state checks follow this entry.

The final documentation audit resolved all 26 relative README links, confirmed all 17 numbered sections, and found valid final newlines with no trailing whitespace. Filename-only API-key scans found no candidate in the working tree, tracked files, staged content, or reachable Git history. `git diff --check` returned `0` with only the repository's existing Windows line-ending notices. The temporary skill-validation directory count was zero, and Git status showed the ongoing intended Experiment 6 work plus this correction; no unrelated file was reverted or overwritten.

## 2026-08-29 — Recapture after addon-version validation failure

### Reported failure and diagnosis

The user reported:

```text
ERROR: portable-run-001.json: addon identity or version is unsupported
ERROR: portable-run-001.json: known_limitations is missing the required probe-storage memory limitation
Validation failed with 2 error(s).
```

Inspection confirmed that the ignored `portable-run-001.json` was produced by addon `1.0.0`, contained five earlier limitations, and still had 600 samples. The current addon, validator, and tracked canonical fixture use `1.0.1` and require the sixth probe-storage limitation. The consumer addon copy had been removed after the original portability test as designed. Before implementation, the old file's SHA-256 was `CB866CE8D7D47520054B31E78481D17AE45FBA82E7738B72FDCFE02C91831805`.

The approved plan preserved the old result, prohibited retroactive metadata edits, required one new uniquely identified capture, and retained strict version validation. It also required an actionable validator diagnostic and a copyable UTC-run-ID documentation workflow.

### Implementation and fresh capture

Generic validation now distinguishes an unsupported addon identity from an unsupported version. A version mismatch reports the detected version, expected `1.0.1`, and the instruction to recapture with the current addon and a new run ID. A fixed test covers the exact `1.0.0` diagnostic. README now assigns one UTC-derived `$RunId` and reuses it for capture, validation, and budget checking; both README files explain that old evidence must not be relabeled.

The canonical addon was copied into the ignored consumer path after verifying that its resolved destination remained inside `examples/minimal_project/`. Exactly one new headless Godot process was launched with run ID `portable-20260829T142235301Z`. The Windows executable detached from the invoking PowerShell command, leaving `$LASTEXITCODE` empty and making the immediate result check occur too early. No second process was launched. A follow-up process check found that the original process had completed and that its result existed.

The first privacy audit repeated an earlier harness mistake: a case-insensitive drive-letter expression matched the `s:/` substring in `res://results`. The result was unchanged. Requiring a drive path at the beginning of a JSON string corrected the audit and found no private path or identifying path component.

The fresh capture reported addon `1.0.1`, 600 sequential samples, all six limitations, process p95 `0.951 ms`, peak node count `3`, measurement duration `4139.238 ms`, and capture duration `4953.588 ms`. No result temporary file remained. Generic validation returned `0`, and both calibrated v2 budgets passed. The old result's SHA-256 was unchanged. The ignored consumer addon copy was then removed from its verified example-project path and remains recoverable from the canonical addon.

### Compatibility verification

The targeted portable suite passed 11 tests before capture. The final complete suite reported:

```text
Ran 68 tests in 1.874s

OK
```

Python byte-compilation succeeded. All 49 historical synthetic results validated, and the tracked canonical generic fixture plus its two budgets passed. The unchanged Experiment 5 policy retained exit `1` with only `cpu-spike-workload-p95` and `node-leak-retained-nodes` failing. Repeated structured evidence and budget JSON for the fresh capture were byte-identical.

No original synthetic Godot benchmark, API request, credential access, permanent dependency, commit, or push occurred. Final skill, link, secret-pattern, whitespace, and Git-state checks follow this entry.

The documentation skill printed `Skill is valid!` using PyYAML 6.0.3 from a uniquely named temporary directory; cleanup left zero matching temporary directories. The final audit resolved all 26 relative README links, confirmed all 17 numbered sections, verified final newlines and no trailing whitespace, and matched the documented repository remote to both configured `origin` URLs. Filename-only API-key scans found no candidate in the working tree, tracked files, staged content, or reachable Git history. `git diff --check` returned `0` with only existing Windows line-ending notices. Git status contained only the intended validator test, documentation, and ongoing addon work; both ignored result files remained present and the ignored addon copy remained absent.

## 2026-08-29 — Clean-clone test-fixture correction

### Request and verified dependency cause

The user asked why `httpx2` appeared in `test_investigator`, requested that all 68 tests work in a clean environment, requested a fresh evaluation of the canonical fixture and its budgets, and authorized a small corrective commit. The user then made the reproducibility requirement explicit:

> Verify whether any automated test depends on ignored demo_project/results files. Tests intended to pass from a fresh Git clone must use tracked, fixed fixtures under tests/fixtures/. Keep the 49 historical local results only for a separate integration check.

Inspection found that `openai==3.6.0`, selected by `openai-agents==0.22.0`, installs `httpx2` as a transitive transport dependency. The tests had imported `httpx2.Request` and `httpx2.Response` only to construct mocked rate-limit errors; application code did not directly depend on it. The audit also found real references to the ignored `demo_project/results/` directory in investigator path, validator-subprocess, evidence-packet, grounding, CLI-preflight, and portable-addon tests. Those tests could therefore pass locally while failing from a fresh clone.

### Fixture and dependency changes

Two small tracked fixtures were added. `tests/fixtures/generic_results/main_scene.json` is a schema-valid generic capture used for containment, real validator subprocess, generic-schema, and fixed-budget coverage. `tests/fixtures/investigator/evidence_packet.json` contains deterministic opaque evidence IDs, every semantic category required by the grounding gate, all three scenarios, limitations, and allowlisted controller behavior.

All default tests now use those fixtures or temporary directories. The rate-limit tests use `SimpleNamespace` request/response doubles and no longer import the indirect transport package. `requirements-agent.txt` pins both `openai-agents==0.22.0` and the verified compatible `openai==3.6.0`; `httpx2` remains dependency-managed by OpenAI rather than a repository test API. A source scan found no remaining `demo_project/results` or `httpx2` reference under `tests/`.

### Encountered failures and response

The first fixture-backed test run failed two tests because the new generic fixture used a semantically equivalent but schema-inexact percentile-description string. The validator intentionally requires the contract's exact nearest-rank definition. The fixture was corrected to that exact definition; no validator rule was weakened. The next complete local run passed all 68 tests.

The first attempt to stage the clean-snapshot inputs failed because the sandbox could not create `.git/index.lock`. The same narrowly scoped `git add` operation was rerun with repository Git-write approval and succeeded. No unrelated file was staged.

### Clean exported-snapshot proof

The staged index was exported with `git checkout-index` into a uniquely named system-temporary directory. The export contained zero ignored result files and no repository virtual environment. A fresh Python 3.14 virtual environment was created inside the export, and only `requirements-agent.txt` was installed. `pip check` reported no broken requirements, byte compilation succeeded, and the complete suite reported:

```text
Ran 68 tests in 0.500s

OK
```

The tracked canonical portable fixture was then validated independently. Its process p95 was `0.529 ms <= 1.1 ms`, and its peak node count was `3 <= 3`; the validator and both schema-v2 budget rules returned `0`. The temporary export and virtual environment were removed after verification and confirmed absent.

### Separate local integration evidence

The ignored historical directory was evaluated only after the clean-clone proof. All 49 synthetic results validated with exit `0`. Their current aggregate reported healthy/CPU-spike median p95 workload of `163 usec`/`11,585 usec`, a `71.07x` ratio. The unchanged Experiment 5 policy returned its expected exit `1`, and only `cpu-spike-workload-p95` and `node-leak-retained-nodes` failed. Repeated canonical evidence and budget JSON output for the tracked fixture was byte-identical.

README now distinguishes tracked unit fixtures, the tracked canonical portable integration fixture, and optional ignored historical evidence. `IMPROVEMENT_CHANGELOG.md` was deliberately left unchanged because this task corrects test infrastructure rather than introducing a product experiment. No Godot process, API request, credential access, historical-result mutation, or push occurred. Final documentation-skill, link, secret, whitespace, staged-diff, and commit verification follow this entry.

### Final verification and focused commit

The repository suite was rerun after the final fixture changes and passed all 68 tests in 0.395 seconds; byte compilation also passed. The official documentation-skill validator printed `Skill is valid!` with PyYAML 6.0.3 supplied only through a unique system-temporary directory, and cleanup confirmed that directory no longer existed.

The canonical integration recheck initially used a stale guessed budget filename and correctly returned configuration exit `2`; listing the tracked example files identified `examples/minimal_project/budgets/performance_budgets.json`. The corrected command validated the canonical capture with exit `0` and passed both budgets with exit `0`: process p95 `0.529 ms <= 1.1 ms` and peak nodes `3 <= 3`.

The final audit found both new fixtures tracked, no ignored-results path or direct `httpx2` import under `tests/`, all 28 README links present, all 17 required README headings in order, final newlines, and no trailing whitespace. `git diff --check` and its staged equivalent passed. A first changelog-unchanged harness used PowerShell command output as a Boolean even though `git diff --quiet` communicates through its exit code; the corrected check inspected `$LASTEXITCODE` and confirmed both staged and unstaged changelog content was unchanged. A strict filename-only API-key scan found no candidate in the working tree, tracked files, staged content, or reachable history. Both configured `origin` URLs still matched the documented repository URL, and no clean-test or skill-validation temporary directory remained.

The staged set contains only this trajectory, README, the dependency pin, two tracked fixtures, and the two fixture-refactored test modules. The requested single commit uses subject `Make investigator tests reproducible from clean environment`; its identifier is reported in the task handoff. No push is performed.

<a id="trajectory-experiment-7"></a>

## 2026-08-29 — Experiment 7 portable generic investigator

### Original request, correction, and approval

The supplied request began:

> # Experiment 7: Portable Generic-Capture Investigator Integration
>
> Extend the existing `Godot Performance Investigator` so it can investigate validated portable-addon captures identified by project-defined `profile` values, while preserving all current synthetic `healthy`, `node_leak`, and `cpu_spike` behavior.

It required an inspection and approval checkpoint, explicit synthetic/generic/failed dispatch, generic five-section grounding and fallback, tracked fixtures, no general shell or filesystem tool, no addon credential, no budget integration, and no edits before approval.

Inspection started from clean commit `d0d64e0`. The existing 68-test suite, tracked generic fixture, canonical v2 policy, 49-result optional integration set, and Experiment 5 result were rechecked successfully. The investigator was confirmed synthetic-specific in its instructions, required semantic map, fallback renderer, and grounding rules.

The critical packet mismatch was found before planning: generic evidence had no explicit kind, its global count used `scenario: all`, and every profile metric contained both `scenario: generic` and `profile`. The generic packet also lacked evidence that could safely state memory or source-revision availability. The user then clarified:

> Generic profile discovery must exclude the reserved profile: "all" validation-count item. Only profile-scoped metric and availability evidence defines reportable profiles.
>
> present means every contributing capture supplied a revision value, not that all supplied values are identical. unknown means none supplied one, and mixed means only some supplied one. The investigator must never claim revision equality or reveal revision values.
>
> Treat the generic identity change as a pre-release schema correction. If the evidence packet has external consumers beyond this repository, bump the schema instead of silently changing v1.

Repository, branch, tag, packaging, and reference inspection found only the repository's validator, checker, investigator, tests, and documentation consuming the packet. The corrected plan therefore retained schema version 1 as a pre-release correction, and the user approved that complete plan with `PLEASE IMPLEMENT THIS PLAN` plus explicit `$godot-performance-guardian-docs` and `$agent-trajectory` invocations.

### Implementation

`tools/validate_results.py` now emits `evidence_kind` as `synthetic`, `generic`, or `failed`. Synthetic items retain scenario identity. Generic items use profile identity only, reserve `profile: all` for the validation count, and add per-profile memory and revision availability. Memory is `available`, `unavailable`, or `mixed`. Revision is `present`, `unknown`, or `mixed` using the user's contributing-capture definitions; revision values never enter the evidence packet.

`agent/investigator.py` now validates packet identity, schema, status, counts, identifiers, safe sources, limitations, and exclusive scenario/profile identity before dispatch. The existing synthetic semantic matcher and report behavior remain. The generic matcher discovers sorted profiles only from recognized profile-scoped metric and availability evidence, excludes `all`, requires unique metrics, and permits peak-memory evidence only for `available` status.

The generic gate checks five-section order, dynamic citations, number support, every discovered profile, memory and revision availability, every limitation, exact uncertainty language, absence of synthetic-only claims and unsupported causes, read-only testable recommendations, and sensitive output. The deterministic generic fallback uses only matched packet values, preserves opaque IDs, handles all availability states, passes the same gate, never emits rejected model text, and makes no second API request.

The existing synthetic investigator fixture gained kind metadata. A tracked multi-profile generic packet fixture was added with opaque nonsequential IDs, one available-memory profile, one unavailable-memory profile, present and unknown revision status, and all generic limitations. Test-generated variants exercise mixed status without storing revision values.

The addon, Godot projects, scenarios, stored results, dependencies, and budget checker were not modified.

### Test failures and corrections

The first post-implementation 68-test run reported four failures. Two mocked validator packets lacked the new schema/kind metadata; the investigator-instruction assertion expected the established phrase `opaque evidence ID`; and the portable evidence test incorrectly required the reserved `all` item to equal `main_scene`. The fixtures and assertions were updated to the approved packet contract, and the instruction retained the established phrase.

The next 82-test run had one failure: the unavailable-memory rule searched for `static memory`, while the rendered contract used `static-memory`. The gate normalized that hyphenated form before checking for an invented byte value.

The following 84-test run had one fixture-test failure. Removing one occurrence of a citation did not make the ID absent because the same evidence correctly supported a recommendation later in the report. The test removed every occurrence to exercise the required-evidence rule. No grounding or validator rule was weakened in response to these failures.

### Verification evidence

The first complete acceptance suite after the main generic cases reported 85 tests in 1.667 seconds. A final audit added an explicit rejection case proving that the reserved `all` validation-count identity cannot be presented as a reportable profile. The final complete suite then reported:

```text
Ran 86 tests in 1.760s

OK
```

`pip check` reported no broken requirements, and byte compilation completed successfully. The tracked generic capture validated with exit `0`. Two structured packet invocations were byte-identical, declared `evidence_kind: generic`, contained one reserved `all` validation-count item, and discovered only `main_scene` as reportable. The tracked synthetic and generic fallback fixtures both produced zero grounding errors.

The canonical portable capture validated and its v2 policy passed both established rules:

```text
PASS: main-scene-peak-nodes - Measured 3 nodes within maximum 3 nodes.
PASS: main-scene-process-p95 - Measured 0.529 ms within maximum 1.1 ms.
```

All 49 ignored historical synthetic files validated with exit `0`. Their current aggregate remained healthy/CPU-spike median p95 workload `163 usec`/`11,585 usec`, ratio `71.07x`. The unchanged Experiment 5 policy returned its expected `1`; only `cpu-spike-workload-p95` and `node-leak-retained-nodes` failed.

The environment-only presence check returned `OPENAI_API_KEY_PRESENT=False`. No key value was accessed and no live request occurred. Generic model output and live generic fallback therefore remain unverified. No Godot process, commit, or push occurred.

The repository documentation skill updated README's status, tree, commands, packet contract, generic grounding/fallback behavior, availability semantics, local evidence, limitations, and roadmap. `IMPROVEMENT_CHANGELOG.md` appends Experiment 7 while preserving all earlier entries. Final skill, link, Markdown, secret, diff, and Git-state checks follow this entry.

### Final audit and Git state

The repository-local documentation skill passed its official `quick_validate.py` check. PyYAML was supplied only through a uniquely named temporary directory for that check, and the directory was removed afterward. README retained all 17 required headings; all 29 relative links resolved to existing tracked paths. The documented `origin` fetch and push URL remained `https://github.com/TaofeekS/godot_performance_guardian.git`.

The final test-source audit found no dependency on ignored `demo_project/results` data and no direct `httpx2` import. A strict filename-only credential-pattern scan found no candidate in working-tree, tracked, staged, or reachable-history content. Focused source review confirmed generic identity exclusivity, reserved-`all` exclusion, semantic profile discovery, conditional memory evidence, revision-availability semantics, dynamic citations, and packet-kind dispatch. `git diff --check` passed; its only messages were Git's informational LF-to-CRLF conversion warnings.

The final working tree contains the Experiment 7 changes to the validator, investigator, tracked fixtures, tests, README, changelog, and this trajectory. `tools/check_budgets.py`, the addon, Godot projects, stored results, and dependency manifests remain unchanged. No commit or push was performed.

<a id="trajectory-experiment-8"></a>

## 2026-08-29 — Experiment 8 grounded model upgrade evaluation

### Request and approved decision

The user requested:

> 1. Run `gpt-5.6-terra` against the same tracked fixture.
> 2. Check whether the model-generated report passes grounding without fallback.
> 3. If Terra still fails, test `gpt-5.6-sol`.

The follow-up decision adopted a one-clean-pass threshold: select Terra if its first response passed directly, otherwise test Sol once and select it only if that response passed directly. If both required fallback, retain `gpt-4.1-mini`. Operational API failures would be inconclusive rather than model-quality failures.

### Inspection and live evaluation

The task used the OpenAI documentation guidance and the repository-local `godot-performance-guardian-docs` skill. Inspection confirmed `DEFAULT_MODEL = "gpt-4.1-mini"`, the existing `OPENAI_MODEL` override, one required validator tool, and the tracked `tests/fixtures/generic_results` input. The working tree already contained the uncommitted Experiment 7 changes and was preserved. The configured Git remote still used the documented public URL.

The environment check reported only `OPENAI_API_KEY_PRESENT=True`; the credential value was never read, printed, or stored. A process-scoped Terra override made exactly one investigator invocation. It reached the API and returned `0`, but the direct response failed `G14`, `G18`, `G19`, `G21`, `G23`, and `G24`, so the accepted output was the deterministic fallback.

Because Terra failed the agreed direct-grounding rule, a process-scoped Sol override made exactly one conditional invocation against the same fixture. It returned `0`, but its direct response failed `G13`, `G14`, `G18`, `G19`, `G21`, `G23`, and `G24`; the deterministic fallback again supplied the accepted report. Rejected model text was not emitted, no application-level retry was added, and no additional live confirmation call was made.

### Decision and documentation

Neither candidate qualified. The investigator default and its configuration test therefore remain `gpt-4.1-mini`; `OPENAI_MODEL` remains available for explicit overrides. README now distinguishes live fallback verification from direct model-grounding success. `IMPROVEMENT_CHANGELOG.md` preserves Experiment 8 as a negative comparison and records the lesson that increasing model capability alone did not satisfy the exact generic report contract in these single live observations.

No Godot process, benchmark, fixture/result/budget change, dependency change, commit, or push occurred. Final local tests, byte compilation, documentation-skill validation, link checks, secret checks, whitespace checks, and Git-state review follow this entry.

### Final verification

`pip check` reported no broken requirements. The complete suite passed all 86 tests in 0.449 seconds, including the default-without-environment assertion for `gpt-4.1-mini` and the explicit `OPENAI_MODEL` override assertion. Byte compilation completed successfully.

The official skill validator printed `Skill is valid!`. Its PyYAML dependency was installed only into a uniquely named system-temporary directory; path validation preceded recursive cleanup, and the directory was confirmed absent afterward. README retained 17 numbered headings, all 29 links resolved, and all three evidence documents ended with newlines.

An initial combined audit harness exited without output, so the read-only checks were split into smaller commands. A later combined final check also had a Python quoting error; its repository checks still ran, and the link/headings/newline portion was rerun separately. The corrected checks found 29 resolvable README links, 17 numbered headings, final newlines, and no key-shaped value in working-tree, tracked, staged, or reachable-history content. `git diff --check` passed with only informational LF-to-CRLF warnings. The final status still contains the pre-existing uncommitted Experiment 7 implementation plus the three Experiment 8 documentation updates; no code default or test expectation changed for Experiment 8. The public `origin` fetch and push URL remained unchanged. No commit or push was performed.

<a id="trajectory-experiment-9"></a>

## 2026-08-29 — Experiment 9 typed model contribution

### Request and approved corrections

The user approved:

> PLEASE IMPLEMENT THIS PLAN: # Experiment 9: Typed Model Contribution with Deterministic Rendering

The user also required the evaluation and contribution boundary to be tightened:

> test gpt-4-1-mini before other agents
>
> use an enum not an action text prefix
>
> The model supplies only the limited explanation text and evidence IDs. Local validation should still reject causal terms such as “proves,” “caused by,” “memory leak,” or unsupported bottleneck claims.
>
> Require: At least one accepted recommendation. Zero or more hypotheses. At least one evidence ID per item. Unique IDs per item. Bounded item counts and text lengths. No Markdown, newlines, measurements, paths or embedded citations in model text.
>
> Adoption should require at least one model-authored item to survive local validation.
>
> If the SDK cannot produce a valid typed final output, recover without another model request, retain the already-produced validator packet when safely available, and render the deterministic fallback. If the tool packet cannot be safely recovered, return a hard nonzero failure.

The task invoked the repository-local `godot-performance-guardian-docs` skill. Its README requirements reference was read completely before documentation edits. Official OpenAI model guidance was consulted for Structured Outputs and prompt-contract design. The public `origin` fetch and push URLs remained `https://github.com/TaofeekS/godot_performance_guardian.git`.

### Inspection and implementation

Inspection confirmed the pinned Agents SDK exposes strict `output_type` schemas and a run hook that receives a function-tool result before final-output parsing. The existing investigator used one required tool, free-form Markdown output, semantic packet matching, a deterministic fallback, and a post-generation grounding gate.

`agent/investigator.py` now defines a strict typed contribution with zero to three bounded hypotheses and one to three recommendations. Recommendation action is an enum containing `compare`, `inspect`, `measure`, `profile`, `validate`, `capture`, and `repeat_capture`; only hypotheses contain limited model-authored prose. Every item requires one to four evidence IDs.

Local filtering rejects unknown or duplicate references, Markdown, newlines, measurements, paths, embedded citations, credential-shaped text, and causal language including proof, confirmation, causation, leaks, and bottlenecks. Invalid hypotheses can be discarded. At least one valid recommendation must remain, which also guarantees a real model-authored contribution.

The model no longer writes report Markdown. Local rendering reuses semantic packet matches for all verified facts, measurements, availability states, limitations, headings, and citations, then converts accepted enum choices into canonical read-only recommendations. The unchanged schema-specific grounding gate validates the result. A distinct disclosure identifies locally rendered model contributions.

An SDK run hook records exactly one safely validated `validate_benchmark_results` packet. A typed-final-output `ModelBehaviorError` uses that packet for deterministic fallback without another request. A missing, malformed, ambiguous, or unsafe packet produces the existing hard `G00_EVIDENCE_PACKET` failure. Other API and operational errors retain their prior safe handling.

### Test failures and corrections

The first focused run after implementation executed 56 existing investigator tests and found two expected assertion mismatches: one test still expected the old grounding-warning wording, and another expected the removed Markdown-heading prompt. Those assertions were updated to the typed contract.

After adding the new typed-contribution tests, the next 64-test run found two test-only issues. One instruction phrase crossed a source newline, and the empty evidence-ID case was rejected by the strict schema before local item filtering. The assertions were corrected to match the actual enforcement layer; no production rule was weakened.

The subsequent focused suite passed all 64 investigator tests. The generated strict JSON schema contained the seven enum values, one-to-four ID bounds, zero-to-three hypothesis bounds, one-to-three recommendation bounds, required fields, and `additionalProperties: false`.

### Local and live verification

`pip check` reported no broken requirements. The complete repository suite passed:

```text
Ran 94 tests in 0.538s

OK
```

Byte compilation succeeded. The tracked generic result and canonical portable fixture both validated with exit `0`. The canonical v2 policy again passed process p95 `0.529 ms <= 1.1 ms` and peak nodes `3 <= 3`. All 49 ignored historical synthetic results validated; their current healthy/CPU-spike median p95 workload comparison remained `163 usec` versus `11,585 usec`, or `71.07x`. The Experiment 5 demonstration policy returned its expected `1` with only CPU-spike workload and node-leak retention failing.

The environment check reported only `OPENAI_API_KEY_PRESENT=True`; the value was never read, printed, or stored. Exactly one process-scoped `gpt-4.1-mini` request ran against `tests/fixtures/generic_results`. It returned exit `0`, used no deterministic fallback, and produced two accepted recommendations: `profile` linked to process, physics, and memory evidence, and `compare` linked to object, node, and orphan evidence. One optional hypothesis was discarded under `C03_HYPOTHESIS_TEXT`. The locally rendered report passed the unchanged grounding gate and included every required generic limitation.

Mini therefore qualified as the first candidate and remains `DEFAULT_MODEL`. Per the conditional evaluation rule, Terra and Sol were not called. This is one nondeterministic live observation and does not establish general reliability or a model-quality ranking.

No Godot process ran. Benchmark data, fixtures, budgets, validator calculations, dependencies, and evidence schema were not changed. No commit or push occurred. Final documentation-skill, link, Markdown, secret, whitespace, and Git-state checks follow this entry.

### Final documentation and repository audit

The first official skill-validator attempt failed because the project environment did not include PyYAML. PyYAML `6.0.3` was installed only into `.skill-validation-temp`. The first sandboxed invocation then imported that directory as an inaccessible namespace and could not remove it because the escalated installer and sandbox had different access. The path was resolved and checked to be exactly the named child of the repository before an escalated validation/removal operation. That operation printed `Skill is valid!` and confirmed `TEMP_REMOVED=True`; no dependency manifest or persistent environment was changed.

README retained all 17 numbered sections, all 29 relative links resolved, and README plus both evidence documents ended with final newlines. Tests still contain zero references to ignored `demo_project/results` data. Filename-only scans found zero key-shaped matches in working-tree, tracked, staged, or reachable-history content. `git diff --check` returned `0` with only informational LF-to-CRLF warnings.

The final working tree contains five focused Experiment 9 files: the investigator, its tests, README, improvement changelog, and this trajectory. The branch remains `main` with the documented public `origin`; no commit or push was performed.

<a id="trajectory-experiment-10"></a>

## 2026-08-29 — Experiment 10 CI performance gate

### Request and approved plan

The user requested:

> PLEASE IMPLEMENT THIS PLAN:
> # Experiment 10: CI Performance Gate with Optional AI Investigation

The approved summary required one standard-library runner that loads and validates budget configuration, invokes the existing validator once, applies the existing budget evaluator without recalculating metrics, preserves exits `0`/`1`/`2`, and optionally invokes the existing investigator afterward. The explicit governing rule was:

> **The deterministic tools decide; the agent explains.**

The plan also required a Windows GitHub Actions workflow, fixed tracked fixture/policy inputs, canonical human/JSON output, no OpenAI import in `never` mode, no investigation after deterministic failure, and exactly one live `gpt-4.1-mini` unified request only when a key entry was present after local verification. Godot, dependencies, fixtures, budgets, validator calculations, investigator grounding, commits, and pushes were out of scope.

The repository-local `godot-performance-guardian-docs` and `agent-trajectory` skills were read and invoked for the documentation phase. The documentation requirements reference was read completely before edits.

### Inspection

Inspection established the tracked integration pair as `tests/fixtures/generic_results/main_scene.json` and `examples/minimal_project/budgets/performance_budgets.json`. The pre-change suite passed 94 tests. The tracked capture validated with exit `0`; its process p95 budget passed `0.5 ms <= 1.1 ms`, and its peak-node budget passed `3 <= 3`. No `.github/workflows/` directory existed.

`tools/check_budgets.py` already exposed `load_budget_configuration()`, `run_validator_packet()`, and `evaluate_budgets()`. The investigator's accepted-report and fallback disclosures, typed contribution boundary, safe errors, and five report headings were verified at their source. `requirements-agent.txt` remained pinned to `openai-agents==0.22.0` and `openai==3.6.0`. The configured public `origin` fetch and push URL remained `https://github.com/TaofeekS/godot_performance_guardian.git`.

### Implementation

`tools/run_guardian.py` was added with repository-relative containment for the result directory and budget file, including traversal and resolved symlink escape rejection. It loads policy before subprocess execution, delegates validation and evaluation to the existing checker, and renders either four-section human output or sorted compact JSON with one final newline.

The optional investigator is a fixed repository-resolved subprocess with a 120-second timeout, captured streams, no shell, and no application retry. Mode `never` neither checks the key nor launches the process. Mode `on-failure` runs once only for exit `1`; `always` runs once after exit `0` or `1`. Missing credentials, launch errors, timeouts, API/model failures, malformed reports, accepted reports, and deterministic fallback leave the deterministic exit unchanged. Only established accepted/fallback disclosures can populate the report; unrecognized or sensitive output is suppressed.

`.github/workflows/performance-guardian.yml` was added for pull requests targeting `main` and manual dispatch. It uses Windows, Python 3.14, read-only contents permission, the planned v7 GitHub actions, pinned requirements, `pip check`, the complete tests, and the tracked fixture/policy. Pull requests force `never`. Only the manual step receives `OPENAI_API_KEY` and the optional `OPENAI_MODEL` variable. The canonical report is written beneath the runner temporary directory, the Python status is preserved, and artifact upload uses `if: always()`.

`tests/test_run_guardian.py` added focused mocks and a real tracked-fixture boundary test. It covers ordering, all deterministic exits, containment, all investigation modes, one optional process, key absence, safe API/timeout/OS handling, accepted/fallback classification, rejected-output suppression, output stability, import safety, and workflow contracts without a live API call.

### Test failure and response

The first 25 focused runner tests passed. A subsequent added simulated-symlink test failed once with `NameError: name 'mock' is not defined` because the file imported `patch` directly rather than the `mock` module. The test was corrected to use the imported `patch.object`; the focused test then passed. No production behavior was changed in response.

### Deterministic verification

The substantive commands included:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q agent tools tests
.\.venv\Scripts\python.exe .\tools\validate_results.py .\tests\fixtures\generic_results
.\.venv\Scripts\python.exe .\tools\check_budgets.py .\tests\fixtures\generic_results .\examples\minimal_project\budgets\performance_budgets.json
.\.venv\Scripts\python.exe .\tools\run_guardian.py --investigate never .\tests\fixtures\generic_results .\examples\minimal_project\budgets\performance_budgets.json
```

`pip check` reported no broken requirements. The final pre-live suite passed all 120 tests in 0.629 seconds, byte compilation succeeded, and `git diff --check` returned `0`. The tracked validator, budget checker, and unified runner each returned `0`. Repeated structured validator, budget JSON, and unified JSON invocations produced identical output.

The separate optional local integration used all 49 ignored historical result files. Validation returned `0`; the Experiment 5 demonstration policy returned its expected `1`, with only CPU-spike workload and node-leak retention failing. No automated test referenced those ignored files.

### One live unified run

The environment check reported only `OPENAI_API_KEY_PRESENT=True`; the value was never read, printed, or stored. Exactly one process-scoped `gpt-4.1-mini` request then ran through:

```powershell
.\.venv\Scripts\python.exe .\tools\run_guardian.py --investigate always .\tests\fixtures\generic_results .\examples\minimal_project\budgets\performance_budgets.json
```

It returned authoritative exit `0` with one validated file and both budgets passing. The investigator outcome was directly `accepted`, not fallback. Local rendering included three accepted evidence-linked recommendations (`inspect`, `profile`, and `validate`), every required generic limitation, and the exact root-cause uncertainty statement. The result is one nondeterministic live observation and does not establish long-run model reliability.

### Documentation and remaining verification

README was synchronized with the unified command, modes, output schema, exits, authority boundary, workflow, secret/model configuration, artifact behavior, troubleshooting, and actual local/live evidence. `IMPROVEMENT_CHANGELOG.md` records Experiment 10 as a product experiment, while this section records execution history. A GitHub-hosted workflow run remains unverified; no GitHub Actions job was triggered during implementation.

No Godot process or synthetic benchmark ran. No dependency, validator calculation, budget policy, fixture, stored result, addon, investigator behavior, or Git remote changed. No API call beyond the single authorized unified Mini run occurred. No commit or push was performed. Final skill, link, heading, newline, secret-pattern, ignored-result-reference, whitespace, and Git-state audits follow this entry.

The first skill-validator invocation failed with `ModuleNotFoundError: No module named 'yaml'`, as PyYAML is intentionally not a project dependency. A follow-up temporary-install command used `New-Item -LiteralPath`, which this PowerShell rejected; `pip --target` nevertheless created the uniquely named temporary directory, installed cached PyYAML `6.0.3`, and the official validator printed `Skill is valid!`. Cleanup verified the resolved directory was an immediate system-temporary child with the expected prefix, removed it, and confirmed `TEMP_REMOVED=True`. No project manifest or persistent environment changed.

The final post-documentation suite passed all 120 tests in 0.592 seconds; `pip check`, byte compilation, and `git diff --check` also passed. README retained all 17 numbered sections, all 33 relative-link occurrences resolved, and README plus both evidence documents ended with final newlines. Tests contained zero references to the ignored `demo_project/results` path. Filename-only credential-pattern scans found zero matching working-tree, tracked, staged, or reachable-history files/commits. Final status contained the three documentation files plus the new workflow, unified runner, and runner tests. The branch remained `main` at `f177009`; no commit or push occurred.

<a id="trajectory-experiment-11"></a>

## 2026-08-29 — Experiment 11 turnkey consumer-project performance CI

### Request and approved plan

The user requested:

> PLEASE IMPLEMENT THIS PLAN:
> # Experiment 11: Turnkey Consumer-Project Performance CI

The approved summary required a reusable Windows GitHub Actions workflow that another Godot repository can call with a small job. It must install Godot `4.5.1`, produce three fresh headless captures from a configured scene, validate them, apply the consumer's v2 policy, upload evidence and the canonical report, and optionally invoke the existing investigator downstream. The consumer must commit the addon, an automatically starting probe, and a v2 budget. AI defaults to disabled, deterministic tools decide the exit, and the work adds an MIT license attributed to `TaofeekS`.

The plan further required a standard-library capture helper, symlink-aware `--workspace-root` support across validator/checker/runner/investigator, generic-only external validation, an independent temporary-consumer proof, documentation synchronization, and no commit, tag, push, synthetic benchmark rerun, or API request.

The repository-local `godot-performance-guardian-docs` skill, its complete README requirements reference, and the `agent-trajectory` skill were read before implementation. They required verified status language, exact workflow/command evidence, preservation of the 17 README sections, append-only experiment history, and a chronological execution record.

### Inspection and design evidence

The starting tree was clean at `a7f66885a14a720f22fefd083039138bf9fa082b`. Existing tools assumed the Guardian repository as their containment root, while the generic schema and v2 policy already had the semantics needed for a consumer project. The included minimal project referenced `res://addons/performance_budget_guardian/performance_probe.gd` and used profile `main_scene` with maxima `1.1 ms` process p95 and three peak nodes.

Official documentation checks confirmed Godot's `--path`, `--scene`, and `--` user-argument boundary and GitHub's immutable-SHA recommendation for cross-repository reusable workflows. The selected setup action tag resolved to immutable commit `f166999204a4f2722c6fe042fbaa3b3ea0d9c789`. The configured public `origin` remained `https://github.com/TaofeekS/godot_performance_guardian.git` for fetch and push.

### Implementation

`tools/workspace_paths.py` centralizes explicit-root resolution and relative-member containment after symlink resolution. `--workspace-root` was added to `validate_results.py`, `check_budgets.py`, `run_guardian.py`, and the investigator CLI/boundary. Default repository-root invocations retain their original behavior. External roots require relative inputs and generic captures; normalized evidence and reports contain only consumer-root-relative paths.

`tools/capture_project.py` validates the project, addon, scene/probe reference, automatic start, identifiers, numbers, source-revision shape, and output containment. It creates a fresh run directory, launches one Godot process per capture, stops on the first launch/timeout/exit/missing-output/collision failure, writes exclusive sanitized logs, and atomically writes a canonical manifest. It defaults to three runs, 120 warmup frames, 600 measured frames, sampling interval 1, and 300 seconds per process.

`.github/workflows/reusable-performance-guardian.yml` defines the approved `workflow_call` interface. It uses Windows, read-only contents permission, caller and matching-tooling checkouts, Python 3.14, the immutable setup-Godot commit, conditional agent dependency installation, a process-scoped optional secret, authoritative unified-gate exit preservation, and unconditional 14-day artifact upload. `LICENSE` now contains the standard MIT text with `Copyright (c) 2026 TaofeekS`.

Focused tests cover isolated subprocess arguments, collisions, timeouts, missing output, stop-on-failure, sanitized manifests/logs, external generic gates, investigator workspace forwarding, legacy command compatibility, and the reusable workflow's inputs, pinned action, checkout identities, conditional dependencies, secret safety, and artifacts.

### Failures and responses

The first complete test run exposed a compatibility regression: default validator invocations using absolute temporary fixture paths were rejected by the new relative-input rule. The default mode was restored to its legacy path behavior, while an explicitly supplied external workspace remains strictly relative. The full suite then retained the old mixed-schema boundary behavior.

The first temporary project copy attempted a nonexistent `scripts/` directory and omitted `main.gd`, so Godot stopped with a signal-11 crash before producing evidence. The missing scene dependency was copied and a new run prefix was used, but the restricted sandbox still caused the same engine crash. In both attempts, the helper stopped after one process, recorded a safe failure manifest/log, and accepted no measurement. After explicitly authorizing the same headless subprocess outside the sandbox, a third unique prefix completed exactly three processes. Existing failed directories were preserved during diagnosis and removed only with the containing temporary consumer after all verification.

One cross-suite test initially depended on a function default retaining a prior mocked subprocess reference. Passing the real standard-library subprocess runner explicitly in that integration test removed the state dependency; production behavior was unchanged.

### Independent consumer evidence

The successful command used the local Godot `4.5.1.stable.official.f62fdbde1` executable against a temporary independent directory containing the minimal project and a copied canonical addon. It used profile `main_scene`, source revision `a7f66885a14a720f22fefd083039138bf9fa082b`, run prefix `exp11-local-final`, three processes, 120 warmup frames, 600 measured frames, and sampling interval 1.

All three captures completed with 600 sequential samples. Their process p95 values were `0.364 ms`, `0.344 ms`, and `0.334 ms`; all peak node counts were three. Structured generic validation accepted three files and declared revision availability present without exposing or comparing values. The existing v2 policy passed median p95 `0.344 ms <= 1.1 ms` and median peak nodes `3 <= 3`. The unified `--investigate never` command returned authoritative exit `0`, attempted no API request, retained consumer-relative paths, and found no temporary file or private consumer path in capture JSON.

### Documentation and remaining uncertainty

The documentation skill synchronized README status, tree, requirements, addon-versus-CI distinction, consumer prerequisites, immutable caller example, every workflow input/default, outputs, exits, artifacts, secret behavior, workspace containment, licensing, and local-versus-hosted verification. Its requirements reference now makes those claims repository invariants. `IMPROVEMENT_CHANGELOG.md` records Experiment 11 as a product change; this section preserves its execution history and failed attempts.

The reusable workflow has not yet run on GitHub-hosted Windows or from a separate hosted caller. The local proof establishes only this included project, local Godot build, and machine. No OpenAI request, original synthetic benchmark, commit, tag, or push occurred. Final regression, integration, documentation, secret, link, whitespace, and Git-state checks follow this entry.

### Final verification

`pip check` reported no broken requirements, all 129 tests passed in 0.998 seconds, and byte compilation succeeded. The tracked generic fixture validated and its policy passed `0.5 ms <= 1.1 ms` plus `3 <= 3`. The canonical live fixture separately passed `0.529 ms <= 1.1 ms` plus `3 <= 3`. Two repeated structured-validator outputs and two repeated unified JSON outputs were byte-equivalent.

The optional 49-file historical integration validated successfully. Its Experiment 5 demonstration policy returned the expected `1`, with only `cpu-spike-workload-p95` and `node-leak-retained-nodes` failing. No test referenced the ignored historical results directory.

The first official documentation-skill validator attempt failed because PyYAML is intentionally absent from project dependencies. A sandboxed temporary installation then failed because network access was restricted and its verified temporary directory was removed. With explicit permission, cached PyYAML `6.0.3` was installed only into a new system-temporary directory; the official validator printed `Skill is valid!`, and cleanup confirmed removal. No manifest or persistent Python environment changed.

README retained 17 numbered sections, every checked relative link resolved, and all changed documents ended with final newlines. The configured public fetch/push remote remained correct. `git diff --check` returned `0` with only line-ending notices. Filename-only credential scans found no matches in the working tree, tracked files, staged state, or reachable history, and no private absolute path was found. The temporary consumer directory—including both failed diagnostic attempts and the successful fresh evidence—was removed after measurements and metadata were recorded here. Final status contains only the focused Experiment 11 implementation, tests, license, workflow, skill, and documentation changes; no commit or push was performed.

<a id="trajectory-experiment-11-corrections"></a>

## 2026-08-29 — Hosted workflow-definition correction

### Request and diagnosis

The user reported that the workflow tried to run on every push and failed, then approved the plan beginning:

> PLEASE IMPLEMENT THIS PLAN:
> # Fix Invalid GitHub Actions Workflows

The selected trigger policy remained pull requests plus manual dispatch for the repository gate, and `workflow_call` only for the reusable workflow. The user explicitly requested the correction, regression tests, Experiment 11 clarification, commit, push, and post-push public metadata inspection.

Read-only GitHub API inspection found failed run IDs `33270743889`, `33273002357`, and `33273001829`. Each was labeled as a `push` event and had zero jobs, showing that GitHub rejected the definition before trigger scheduling. The public run page identified the original workflow error as an unavailable `runner` context at job-level `env`. It identified the reusable workflow error as YAML syntax on line 54, where a plain description contained a second colon followed by a space.

### Correction and local verification

The repository workflow no longer defines `GUARDIAN_REPORT` from `${{ runner.temp }}` at job scope. Both command steps use `%RUNNER_TEMP%\performance-guardian.json`; the artifact step retains its supported step-level `${{ runner.temp }}` path. The reusable workflow quotes the colon-bearing investigation description. No push trigger was added.

Regression tests now require pull-request/manual and reusable-call boundaries, reject an explicit push trigger, prohibit the unsupported job-level expression, require the two supported temporary-path forms, and detect unquoted colon-bearing descriptions. The focused seven workflow tests passed. The complete suite then passed 130 tests in 1.007 seconds; `pip check`, byte compilation, and `git diff --check` also passed. No Godot process, benchmark, or OpenAI request ran.

The repository documentation skill and trajectory skill were used for this correction. `IMPROVEMENT_CHANGELOG.md` records it as an Experiment 11 clarification rather than a new experiment. GitHub acceptance, commit identifiers, push outcome, and remaining hosted uncertainty are recorded after delivery below.

### Commit, push, and public verification

The first sandboxed staging attempt failed because `.git/index.lock` could not be created under restricted permissions. No partial index change occurred. After explicit approval, the six verified files were staged and committed as `a672eda` with message `Fix invalid GitHub Actions workflow definitions`. The commit was pushed successfully from `8e7e7bf` to `a672eda` on `origin/main`.

Public GitHub API inspection after the push reported workflow IDs `345505769` (`Performance Guardian`) and `345528362` (`Reusable Performance Guardian`) with state `active`. No run existed for head commit `a672eda`; that is the expected trigger result because the repository workflow is pull-request/manual only and the reusable workflow is call-only. The latest run list still ended at the three historical zero-job failures on the prior commits.

This verifies that GitHub accepted both corrected definitions. It does not verify execution of either hosted job or a call from another consumer repository. README and the Experiment 11 clarification were synchronized with that distinction in a follow-up documentation commit.

## 2026-08-29 — Hosted consumer Godot executable correction

### Request, evidence, and approved plan

After a separate consumer workflow reached the capture stage, the user supplied its hosted log and reported:

> i found the error
>
> godot executable not founc

The visible log contained `ERROR: Godot executable was not found`. Earlier hosted evidence showed that checkout, Python setup, Godot setup, optional dependency installation, and artifact upload completed, while the capture outcome was failure and the authoritative gate rejected the incomplete capture. The user then approved the plan to use the executable installed by `setup-godot`, add regression coverage, synchronize the Experiment 11 evidence, commit, push, and inspect GitHub metadata. The consumer repository itself was explicitly left outside the implementation scope.

The repository documentation skill, its complete README requirements reference, and the agent-trajectory skill were read before changes. The starting branch was clean `main` at `58cdb49`, and fetch/push `origin` remained `https://github.com/TaofeekS/godot_performance_guardian.git`.

### Diagnosis and correction

Inspection found that the reusable workflow pinned and ran `chickensoft-games/setup-godot`, but invoked the capture helper with `--godot-executable "godot"`. The helper resolves command names with `shutil.which()` and correctly rejected that name because it was not on the hosted process path. The hosted job environment supplied a `GODOT` path, so the defect was the workflow handoff rather than addon configuration or a measured budget regression.

The capture step now rejects a missing, blank, or non-file `GODOT` value with a safe configuration error and passes `$env:GODOT` to the fixed capture helper argument. The workflow still preserves failed capture evidence with `continue-on-error`, forwards the actual capture outcome to the deterministic gate, and uploads artifacts unconditionally. The existing workflow contract test now requires the `GODOT` file check and setup-provided argument and rejects the prior literal command.

### Local verification and remaining work

The two focused reusable-workflow tests passed. The complete suite then reported:

```text
Ran 130 tests in 1.033s

OK
```

Python byte compilation also returned `0`. Both workflow files parsed successfully with PyYAML `6.0.3`, supplied only through a uniquely named system-temporary directory that was validated before recursive cleanup and removed afterward. The official repository documentation-skill validator printed `Skill is valid!`. All checked Markdown links resolved, README retained its 17 numbered sections, every evidence document ended with a newline, `pip check` found no broken requirements, and `git diff --check` found no whitespace error. Filename-only credential-pattern scans found zero matching working-tree, tracked, staged, or reachable-history files or commits.

No Godot process, benchmark, OpenAI request, fixture change, budget change, or consumer-repository mutation occurred. README and the Experiment 11 clarification now distinguish the failed hosted attempt from successful hosted capture. Commit, push, public workflow-metadata inspection, and the consumer rerun remain to be recorded after they occur.

### Commit, push, and public verification

The five focused files were staged after a clean staged whitespace check and reviewed as a 54-insertion, five-deletion diff. Commit `580606bcf603bb0279d90a957c6498947d366182` was created with the approved message `Use setup Godot path in reusable workflow` and pushed from `58cdb49` to `origin/main`.

The planned GitHub CLI query could not run because `gh` is not installed on this machine. No repository state changed as a result. A read-only query to GitHub's public REST API then reported `Performance Guardian` and `Reusable Performance Guardian` as `active`. The reusable workflow content at commit `580606b` had blob SHA `80cf79ea20e8ec3440ea0135c524b6ada18ef11f`, exactly matching `git hash-object` for the verified local workflow.

This confirms the correction is pushed and GitHub recognizes the definition. It does not establish successful hosted capture. The consumer repository must update its reusable-workflow reference to full commit `580606bcf603bb0279d90a957c6498947d366182`, correct its separate budget path to `performance_budgets.json`, and rerun. No consumer repository was modified or dispatched during this task.

## 2026-08-29 — Hosted raw-evidence artifact correction

### Request and observed evidence

After the executable correction, the user supplied `performance-guardian-main_scene-33276123451-1.zip` and reported that `never` worked. Read-only ZIP inspection found exactly two entries: `_temp/capture-manifest.json` and `_temp/guardian-report.json`. The manifest reported status `passed`, three requested and completed runs, 120 warmup frames, 600 measured frames, sampling interval 1, and six expected relative evidence paths: three capture JSON files and three Godot logs beneath `.performance-guardian/`.

The canonical gate report returned authoritative exit `0`: all three candidates validated, process p95 passed at `0.093 ms <= 2 ms`, peak nodes passed at `12 <= 100`, and investigation outcome was `not_requested`. The measurements and deterministic verdict were therefore valid, but the downloaded artifact did not preserve the raw capture and log paths named by the manifest.

The user approved the plan beginning:

> PLEASE IMPLEMENT THIS PLAN:
> # Preserve Raw Capture Evidence in Hosted Artifacts

The approved approach was the artifact action's supported hidden-file input on the existing narrow path list, not a workspace-wide upload or a copy into another staging directory. Delivery requires commit, push, public definition verification, and a new immutable SHA; the consumer repository remains outside this task.

### Implementation and local verification

The reusable workflow now sets `include-hidden-files: true` on the unconditional upload step. Its only paths remain the consumer project's `.performance-guardian/` directory, runner-temporary capture manifest, and runner-temporary Guardian report. The regression test isolates the upload step, requires those inputs and 14-day retention, and rejects `.performance-guardian-tooling`, `${{ github.workspace }}`, and `OPENAI_API_KEY` from the upload scope.

Both focused reusable-workflow tests passed. The complete suite reported:

```text
Ran 130 tests in 1.014s

OK
```

Python byte compilation returned `0`, and `pip check` reported no broken requirements. Both workflows parsed successfully with PyYAML `6.0.3`, supplied only through a uniquely named system-temporary directory that was validated before recursive removal. The official documentation-skill validator printed `Skill is valid!`. All checked Markdown links resolved, README retained its 17 numbered sections, all evidence documents ended with newlines, and `git diff --check` found no whitespace error. Filename-only credential-pattern scans found zero matching working-tree, tracked, staged, or reachable-history files or commits.

No Godot process, benchmark, OpenAI request, fixture or budget change, or consumer-repository mutation occurred. README and the Experiment 11 record now treat the hosted deterministic run as verified while keeping corrected raw artifact preservation pending a new consumer ZIP. Commit, push, and public metadata checks follow this entry.

### Commit, push, and public verification

The five focused files were staged after the complete diff and staged whitespace check passed. Commit `0cd6a573d21b5ddd1ffd624be2782d0e9979e3ab` was created with message `Preserve raw performance evidence artifacts` and pushed from `2a2c0e3` to `origin/main`.

GitHub's public REST metadata reported the reusable workflow as `active`. The workflow at commit `0cd6a57` had blob SHA `fba8347337dfa640bf363c9d2c621ea5857bc377`, exactly matching the verified local file. This establishes that the correction is delivered and recognized; it does not prove the next ZIP contains the raw files. The consumer must pin the new full commit, rerun `never`, and inspect the artifact for the three captures, three logs, manifest, and gate report. No consumer repository was changed or dispatched during implementation.

<a id="trajectory-experiment-12"></a>

## 2026-08-29 — Experiment 12 baseline-aware pull-request regression gate

### Request and approved plan

The user first closed the prior hosted-artifact troubleshooting with:

> okay i think we can move forward now
>
> okay let work on experiment 12

The approved implementation request began verbatim:

> PLEASE IMPLEMENT THIS PLAN:
> # Experiment 12: Baseline-Aware Pull-Request Regression Gate
>
> Add opt-in paired comparison for consumer pull requests. The reusable workflow will capture the protected base revision and PR candidate on the same runner, validate both result sets, apply base-controlled absolute and relative budgets, preserve both evidence sets, and optionally provide a grounded comparison-aware investigation.
>
> Existing v1/v2 policies and non-comparison commands remain compatible. Comparison uses budget schema v3 and defaults off.

The detailed contract required exact v3 fields, two structured validator calls, explicit zero-baseline behavior, schema-v2 comparison output, protected-base policy authority, six default captures, comparison-aware grounded investigation, tracked fixtures, a real external Godot evaluation, documentation synchronization, commit, push, and an immutable delivered SHA.

### Inspection and implementation

The repository documentation skill, its complete requirements reference, and the agent-trajectory skill were read before changes. Inspection covered `check_budgets.py`, `run_guardian.py`, `validate_results.py`, `capture_project.py`, `investigator.py`, the reusable workflow, tests, tracked fixtures, both READMEs, the changelog, Git history, and the configured remote.

`check_budgets.py` gained strict schema-v3 parsing and semantic paired evaluation. It preserves v1/v2 paths, treats equality as pass and negative deltas as improvements, defines zero/zero as 0%, and treats a positive candidate over a zero baseline as an undefined percentage and relative failure. `run_guardian.py` adds contained `--baseline-results`, schema-v2 comparison output, and comparison inputs for optional investigation without changing deterministic authority.

`comparison_evidence.py` builds packet schema v2 from the same validator aggregates and v3 policy results. `investigator.py` accepts `evidence_kind: comparison`, validates semantic rule items, suppresses revision values, renders deterministic facts and limitations, grounds typed contributions, and retains its one-tool/one-SDK-call boundary. The workflow adds opt-in PR-only comparison, isolated base checkout at `github.event.pull_request.base.sha`, protected-base policy loading, sequential baseline/candidate captures, distinct manifests, and narrow unconditional artifacts.

Tracked unchanged, regression, policy, and investigator packet fixtures were added. The regression fixture proves the important policy distinction: candidate process p95 `0.61 ms` passes the `1.1 ms` absolute maximum but its 22% increase fails the 20% relative maximum.

### Failures and responses

The first external consumer setup stopped before Godot launch because PowerShell `Copy-Item -LiteralPath` treated the addon's `*` wildcard literally. The capture helper then correctly rejected the missing committed addon. The failed uniquely prefixed directory was resolved beneath the system temporary root before recursive cleanup. The retry used wildcard-aware `-Path`; no policy or measurement setting changed.

An initial local regression run exposed three compatibility issues: mocked rules lacked the new schema attribute, an existing test expected the old optional-investigation call signature, and the comparison grounding gate interpreted a validator limitation containing “prove” as a model causal claim. The implementation defaulted mocked legacy rules to schema v1, preserved the old no-baseline call form, and excludes verbatim validator limitations from causal scanning. The focused tests and then the complete suite passed.

### Real paired evaluation

The corrected temporary workspace copied the independent minimal project and addon into separate `baseline` and `candidate` projects. `capture_project.py` ran three isolated Godot `4.5.1` processes per side with seed/configuration inherited from the project, 120 warmup frames, 600 measured frames, sampling interval 1, distinct collision-safe prefixes, and supplied opaque revision metadata.

All six captures completed. The v3 unified gate validated three baseline and three candidate files, reported revision availability without emitting values, and returned authoritative exit `0`. Baseline/candidate median process p95 was `0.531 ms`/`0.526 ms` (`-0.9416195857%`); peak nodes remained `3`/`3`. Both absolute and relative rules passed unchanged. No OpenAI request was made during this measurement.

### Documentation and remaining delivery

The documentation skill synchronized README, addon guidance, and its repository-specific requirements. The previously supplied nine-entry hosted ZIP closed Experiment 11's raw-artifact claim: it contained three 600-sample captures, three logs, the internal and runner manifests, and the canonical exit-0 report, with no detected private path or credential pattern. `IMPROVEMENT_CHANGELOG.md` records Experiment 12 separately from this execution history.

The first evidence-inspection cleanup command validated both real directories and confirmed byte-identical comparison packets with no exposed revision value or private path, but its PowerShell pipeline incorrectly passed a filename string to `Get-Content`. It stopped before deletion. A corrected explicit-path loop confirmed six captures, 600 samples each, and supplied revision metadata, then removed the verified TEMP-contained workspace.

The environment check reported only `OPENAI_API_KEY_PRESENT=True`; the value was never read, printed, or stored. Exactly one authorized live comparison request ran. It returned deterministic fallback with `C06_VALIDATION_FAILED` because local diagnosis found that the investigator's comparison subprocess command appended the candidate positional argument twice. No second API request was made. The command construction was fixed, a regression test now requires baseline, candidate, and policy exactly once, and local comparison packet generation returned `comparison`, `passed`, with a fallback that passed grounding. Live comparison interpretation remains unverified rather than being misclassified as model failure.

Final full-suite, byte compilation, validator, policy, canonical-output, optional historical, workflow, link, skill, secret, whitespace, commit, push, and public GitHub checks follow this entry.

### Final local verification before delivery

`pip check` reported no broken requirements. The complete suite passed 146 tests in 6.479 seconds and byte compilation succeeded. Repeated generic validator and v2 budget JSON were byte-identical. The tracked unchanged v3 pair returned exit `0`; the tracked regression returned exit `1` with only the relative process rule failing while both absolute limits passed. All 49 optional historical results validated, and Experiment 5 retained exactly its two intentional failures.

PyYAML `6.0.3` was installed only into a uniquely named system-temporary directory. The official documentation-skill validator printed `Skill is valid!`, both workflow files parsed, and the temporary dependency directory was removed. README links and numbered sections passed, the configured fetch/push remote remained the public `origin`, and `git diff --check` reported no whitespace error. The credential scan identified only the intentional mock secret fixture in `tests/test_investigator.py`; excluding that test-only sentinel, no working-tree, tracked, or reachable-history filename or commit matched the credential patterns.

### Commit, push, and public definition verification

The focused 20-file staged diff passed `git diff --cached --check` and was reviewed as 1,506 insertions and 64 deletions. Commit `8c01e350bbf90f280459a6822c686b753b19ebbb` was created as `Add baseline-aware pull request regression gate` and pushed from `4c4ded0` to `origin/main`.

Read-only GitHub public API metadata reported both `Performance Guardian` and `Reusable Performance Guardian` as `active`. The reusable workflow blob at the immutable implementation commit was `cc983648193feb4613e28f4e64924686d523e434`, exactly matching `git hash-object` locally. This proves delivery and definition recognition. It does not prove hosted paired execution; a consumer pull request using the documented two-step migration is still required. No consumer repository was modified or dispatched.

## 2026-08-30 — Experiment 12 hosted artifact-path correction

### Request, diagnosis, and approval

The user supplied screenshots of a hosted manual consumer run and asked:

> this is the problem i got
>
> found out what is wrong with it
>
> let me know what is a problem
>
> how you plan to solve it
>
> dont change any code yet just show me the plans

The screenshots showed candidate capture and `Run authoritative performance gate` completing successfully. Protected-base checkout and capture were skipped, which was consistent with a manual absolute-only run. `Upload performance evidence` alone failed with:

```text
Invalid pattern '.performance-guardian-base-source/./.performance-guardian'. Relative pathing '.' and '..' is not allowed.
```

Inspection confirmed that the reusable workflow always constructed a baseline upload pattern as `.performance-guardian-base-source/${{ inputs['project-path'] }}/.performance-guardian`. With the consumer's valid `project-path: .`, this became the rejected `/./` pattern even though comparison was disabled. Missing baseline files would have been only a warning, but the artifact action rejected the invalid pattern before file discovery. The deterministic gate result and the later artifact-preservation failure were therefore separate outcomes.

After receiving the read-only diagnosis and implementation plan, the user asked about documentation and then approved the correction with:

> okay do this

### Implementation

The reusable workflow now stages evidence before invoking the artifact action. The PowerShell step resolves the consumer project beneath `GITHUB_WORKSPACE`, checks containment, and copies candidate evidence into a fixed runner-temporary staging directory. It resolves and stages protected-base evidence only when `compare-with-base` is true. Available baseline/candidate manifests and the canonical Guardian report are copied beneath a reports directory. The upload action receives only the fixed staging path, retains `include-hidden-files: true`, 14-day retention, and `if: always()`, and never receives an interpolated consumer path.

Regression coverage now requires fixed-path staging, candidate and conditional baseline destinations, containment resolution, narrow report staging, and an upload input without consumer interpolation or explicit `.`/`..` segments. Capture, validation, budget, comparison, and investigator calculations were not changed.

The documentation skill synchronized the root README, addon README, Experiment 12 clarification, and repository-specific documentation requirements. The README explains absolute versus comparison artifact contents, the distinction between a green authoritative gate and failed evidence preservation, and the corrective action for the exact invalid-pattern symptom. Hosted staging remains unverified until a consumer reruns against the delivered correction.

### Verification and operational notes

The focused reusable-workflow tests passed three of three. The complete suite reported:

```text
Ran 146 tests in 5.061s

OK
```

Python byte compilation succeeded and `pip check` reported no broken requirements. The repository environment lacked PyYAML, so the first workflow/skill validation attempt stopped with `ModuleNotFoundError` without changing dependencies. PyYAML `6.0.3` was then supplied only in a uniquely named system-temporary target; both workflows parsed and the official skill validator printed `Skill is valid!`. The temporary target was removed afterward. The temporary-directory setup emitted a non-fatal PowerShell warning because `New-Item` does not accept `-LiteralPath`; `pip --target` created the unique directory and all requested validation still completed successfully.

The first Markdown-link command mishandled root-level files because `Split-Path -Parent README.md` returns an empty string. It produced only diagnostic path errors and no edits. The corrected command used the workspace root for root-level documents; all relative links resolved, README sections 1 through 17 were present, and all checked documents had final newlines. Working-tree, tracked-file, and reachable-history scans reported no credential-pattern filename or commit match. `git diff --check` reported no whitespace error.

Commit, push, immutable SHA reporting, and hosted consumer rerun evidence follow this entry. No Godot process, benchmark, OpenAI request, fixture, budget, or consumer repository was changed or invoked during this correction.

### Delivery and remaining hosted verification

The seven-file focused diff passed staged whitespace inspection and was committed as `248dbcf551e7480b69bffced2ef458adab238e94` with message `Normalize reusable workflow artifact staging`. It was pushed from `820abba` to `origin/main`; a read-only remote check confirmed that `refs/heads/main` resolved to the same full commit.

GitHub's public workflow metadata reported `Reusable Performance Guardian` as `active` at `.github/workflows/reusable-performance-guardian.yml`. This proves delivery and workflow-definition recognition, not successful hosted artifact staging. The consumer must update its `uses:` reference to `248dbcf551e7480b69bffced2ef458adab238e94` and rerun. Absolute-only acceptance requires candidate captures/logs plus available reports in the artifact; paired acceptance additionally requires protected-base evidence and its manifest.

<a id="trajectory-experiment-13"></a>

## 2026-08-30 — Experiment 13 valid-object-count investigation and implementation

### Request and approved boundary

The user approved Experiment 13 after inspection of an external comparison artifact showed that the scene controller had not loaded. The central request was:

> The previous comparison was invalid because `performance_visual.gd` failed to load on both revisions. The independent probe still produced JSON, so Guardian compared an inactive 12-node scene instead of the intended 2,000-versus-25,000 populations.

The approved work covers Guardian capture integrity, PluginTest clean-checkout script correction, deterministic object/node policy calibration, an always-on `gpt-4.1-mini` comparison evaluation, synchronized documentation, and delivery to both repositories. GPU metrics and longer captures remain out of scope.

### Inspection and invalid-before evidence

Read-only inspection of `performance-guardian-main_scene-33281834727-1.zip` found three baseline captures, three candidate captures, their logs and manifests, and a canonical exit-0 report. Every JSON contained 600 samples, but every baseline and candidate sample reported 12 nodes and 1,418 objects. All six Godot logs contained `SCRIPT ERROR:` parse failures for `performance_visual.gd` and `Failed to load script ... Parse error`. The probe node ran independently, so JSON existence and Godot exit status had not established that the measured controller was active.

Public PluginTest inspection found `main` configured for 2,000 shapes and `codex/high-load-visual-performance` for 25,000. The controller preloaded `performance_shape.gd` but also depended on the editor-generated `PerformanceShape` global type cache, and it randomized its RNG instead of applying the benchmark seed. The high-load caller requested `investigate: always` but did not pass the repository secret into the reusable workflow. The v3 policy lacked an object-count rule.

### Guardian integrity implementation and focused verification

`tools/capture_project.py` now detects `SCRIPT ERROR:`, failed script loads, failed script-source loads, and failed GDScript/C# resource loads across captured stdout and stderr. Detection happens after the log is sanitized and persisted but before return-code and result-file acceptance. The manifest becomes failed with `godot_script_error`, contains no capture entries, leaves `completed_runs` at zero, and returns exit `2`, so downstream validation cannot treat the JSON as authoritative.

`tests/test_capture_project.py` creates a result file while returning process exit `0` and injects the diagnostic through each output stream. Both cases stop after one launch, preserve a sanitized log, and reject the capture. The focused module passed 9 tests and Python byte compilation succeeded. README, addon guidance, the repository-local documentation skill, and its detailed requirements now require clean scene logs before a capture can support a performance claim. Cross-repository correction, calibration, hosted evidence, final full verification, commits, and pushes follow this entry.

### Guardian delivery and PluginTest correction

The complete Guardian suite passed 147 tests, `pip check` found no broken requirements, byte compilation succeeded, whitespace checks passed, and the documentation skill's official validator reported `Skill is valid!` using PyYAML installed only in a uniquely named temporary directory and removed afterward. Commit `d9b96e78cd5775b621134afdf40077512931c1c2` (`Reject captures with Godot script errors`) was pushed to Guardian `main`.

PluginTest was cloned into an ignored temporary workspace. On `codex/object-count-baseline`, `class_name PerformanceShape` and casts to the cached global type were removed while the explicit preload remained. Dynamic `Variant` references preserve method dispatch, `_rng.seed = 1337` replaced randomization, both caller jobs name `res://main.tscn`, and the workflow pins the new immutable Guardian commit. The baseline PR job remained comparison-disabled for migration.

A clean Godot 4.5.1 editor parse produced no error. Three local 2,000-shape captures then passed generic validation with 600 samples and no log errors. Per-run process p95 values were 10.246, 10.799, and 10.124 ms; median peak nodes were 2,280 and median peak objects were 5,584. The count ceilings were set to `ceil(median × 1.10)`: 2,508 nodes and 6,143 objects, each with 5% relative tolerance. The existing 2 ms/20% process rule was preserved as approved; it fails on this local host and was not relaxed. Commits `5bb8744` and `89ef110` were pushed, then `main` advanced to `89ef1100d84966da20b74715b0e47e22f992ae5a` with comparison still disabled.

The corrected `main` was merged into `codex/high-load-visual-performance`. Its workflow conflict was resolved in favor of `compare-with-base: true`, `investigate: always`, `gpt-4.1-mini`, and the repository-secret mapping; no secret value entered source or output. The 25,000-shape branch also parsed cleanly. Three local candidate captures passed validation with 600 samples and no script/load errors. Comparison measured median peak nodes 2,280 to 26,357 (about 1,056% growth), objects 5,584 to 49,513 (about 787% growth), and process p95 10.246 to 216.101 ms (about 2,009% growth). All three rules failed both absolute and relative checks, demonstrating the intended deterministic regression. Commit `d8459127fdfbfe533c8ac72a9b9f838006063cd3` was pushed.

No open high-load PR remained, so an authenticated GitHub REST call used the existing credential only in memory to create [PluginTest pull request #2](https://github.com/TaofeekS/PluginTest/pull/2); the credential was neither printed nor stored. Public Actions metadata confirmed run `33283797557` was in progress against Guardian `d9b96e78…`, protected base `89ef110…`, and candidate `d845912…`. At the latest check baseline capture had completed and candidate capture was running. Hosted verdict, artifact inspection, and AI grounding outcome follow this entry.

### Hosted calibration and final acceptance

Run `33283797557` completed baseline and candidate capture successfully, returned deterministic exit `1`, and uploaded a 17-entry artifact. The first valid hosted baseline measured median peak nodes 2,320 and objects 5,891, so the count maxima were recalibrated to `ceil(baseline × 1.10)`: 2,552 and 6,481. Commit `56bc966` updated PluginTest `main`; merge commit `529fc418093b02cb56b44dd7ebdb07d0f2b3cadb` propagated the protected policy into PR #2 and triggered the final run.

Final hosted run `33284218827` completed all six captures successfully. Each side contained three files of 600 samples, and all six logs were free of script parse/load diagnostics. Baseline/candidate median process p95 was 14.169/224.999 ms, peak nodes 2,289/26,366, and peak objects 5,608/49,511. Relative growth was 1,487.967%, 1,051.857%, and 782.864%, respectively. Validation passed, all three configured candidate absolute/relative rules failed, and the authoritative result was budget-failure exit `1`.

The final run requested investigation exactly once. `gpt-4.1-mini` returned an accepted typed contribution rather than fallback. Local filtering discarded an unsafe hypothesis under `C03_HYPOTHESIS_TEXT` but retained three cited read-only recommendations. Deterministic rendering covered all three metrics and both revisions without revealing revision values, included all validator/comparison limitations and the exact root-cause uncertainty sentence, and made no unsupported causal claim. The 17-entry artifact preserved six capture JSON files, six sanitized logs, two internal manifests, two runner manifests, and the canonical report. Scans found no private path, credential-shaped value, or authorization header.

### Final repository verification and cleanup

After the final documentation synchronization, the complete Guardian suite again passed 147 tests in 5.135 seconds, byte compilation succeeded, and `pip check` reported no broken requirements. Every local Markdown link resolved, numbered README sections 1 through 17 remained present, and `git diff --check` reported no whitespace error. The updated documentation skill again passed its official validator with PyYAML supplied only through a unique temporary target and removed immediately afterward.

The PluginTest clone, ignored local captures, downloaded hosted ZIP files, and extracted artifacts existed only beneath the dedicated `.experiment-13` workspace directory. Its resolved absolute path was verified as that exact child of the Guardian workspace before recursive removal; no consumer source or hosted evidence was deleted remotely. Final documentation commit, Guardian push, public branch/workflow checks, and the remaining safe credential-pattern scan follow this entry.

<a id="trajectory-experiment-14"></a>

## 2026-08-30 — Experiment 14 actionable Actions reporting

### Request and approved plan

After observing that the authoritative gate returned exit `1` without showing the failed budget in the step log, the user requested:

> The best next improvement would be to:
>
> - Print a safe human-readable budget summary directly in the failed step.
> - Add the same summary to the GitHub Actions job summary.
> - Create GitHub error annotations for failed rules.
> - Keep canonical JSON and raw captures in the artifact for deeper inspection.
> - Show the accepted AI explanation in the job summary while clearly separating it from the authoritative budget verdict.
>
> do this

The approved Experiment 14 plan required one standard-library renderer, integration into both Guardian workflows, saved deterministic exits, safe handling of optional AI, fixed tests including the observed `11.58 ms > 2 ms` failure, documentation synchronization, Guardian delivery, and exactly one PluginTest manual `on-failure` evaluation without retry.

### Inspection and implementation

The repository documentation skill, its complete requirements reference, the agent-trajectory skill, and skill-creator guidance were read before documentation changes. Inspection covered both workflows, `run_guardian.py`, v1/v2 canonical report shapes, v3 absolute/comparison result structures, workflow tests, README, addon guidance, experiment history, and current Git state.

`tools/render_action_report.py` was added as a standard-library presentation boundary. It validates report schema and exit consistency, renders deterministic log and Markdown output, escapes GitHub workflow commands, combines absolute and relative failures by budget ID, and emits a single safe evaluation annotation when rules cannot be evaluated. It shows AI text only for recognized accepted or deterministic-fallback outcomes that pass its safe presentation check. Credentials, private paths, raw exceptions, revision values, and rejected model output are withheld.

Both workflows now save the gate exit before presentation. The reusable PowerShell step writes the unchanged canonical JSON, derives the exact artifact name, invokes the renderer once with `GITHUB_STEP_SUMMARY`, warns on presentation failure, and exits with the saved gate code. The repository workflow applies the same sequence to pull-request and manual jobs. Artifact paths and secret scope were not broadened.

### Local failures and verification so far

The first focused run had one test-only expectation error: the test expected colons in the annotation message body to use property escaping, while GitHub requires colon/comma escaping only in command properties. The implementation output was correct; the assertion was narrowed to the message-body contract. The focused modules then passed.

`pip check` reported no broken requirements. The complete suite passed 160 tests in 5.037 seconds and Python byte compilation succeeded. A real tracked v2 report passed and rendered `0.5 ms <= 1.1 ms` plus `3 nodes <= 3 nodes`, with authoritative and renderer exits both `0`. A real tracked v3 regression retained gate exit `1` while the renderer returned `0`; it showed the baseline/candidate values and the `22% > 20%` relative process failure and emitted one annotation. Documentation, skill validation, delivery, consumer update, and hosted evidence follow this entry.

The repository virtual environment lacked PyYAML, so no permanent dependency was added. PyYAML `6.0.3` was installed only into a uniquely named system-temporary directory, both workflow definitions parsed, the official documentation-skill validator printed `Skill is valid!`, and the temporary directory was removed. All checked relative Markdown links resolved, README retained sections 1 through 17, and final-newline checks passed.

The first credential-scan expression used PCRE constructs unsupported by Git's extended regular-expression engine; Git rejected the expression without searching or changing files. A corrected set of portable patterns then reported no matching working-tree or tracked filename and no reachable commit identifier. The test-only key-shaped sentinel was assembled from string fragments so the safety test remains effective without resembling a stored credential. The final full run again passed all 160 tests in 4.942 seconds; byte compilation, dependency consistency, and `git diff --check` also passed.

### Guardian and PluginTest delivery

The 11-file staged implementation/documentation diff passed staged whitespace checks and was committed as `7622997bd3a9c5d166703e578af943b7e25f61ba` with the approved message `Add actionable GitHub Actions reporting`. It was pushed from `ef36f83` to Guardian `origin/main`, and `git ls-remote` confirmed the same remote SHA.

PluginTest was cloned into the dedicated `.experiment-14/PluginTest` workspace. Only its two reusable-workflow references changed, both from the earlier Guardian revision to `7622997bd3a9c5d166703e578af943b7e25f61ba`. The two-line diff passed whitespace inspection, was committed as `f3ca43995e3ed9780cc99e0f68182cb7ae25fe90` with message `Use actionable Guardian workflow reporting`, and was pushed to PluginTest `main`.

Exactly one authenticated GitHub workflow dispatch was sent for `main` with `investigate: on-failure`; the existing credential was used only in process memory and was not printed or stored. Dispatch returned HTTP `204` and created [run 33286227714](https://github.com/TaofeekS/PluginTest/actions/runs/33286227714). No second dispatch or AI retry occurred.

### Hosted result and evidence inspection

Candidate capture succeeded, the gate failed as expected, evidence staging/upload succeeded, and the overall run concluded failure. The downloaded gate log showed three of three candidate files validated, `Budgets: FAILED`, `main-scene-process-p95: 11.619 ms > 2 ms`, `Optional AI: ACCEPTED`, authoritative exit `1`, and the exact uploaded artifact name. No presentation warning was emitted. GitHub's check-run annotations API and the public Actions page both showed the named process-budget annotation; GitHub also retained its generic process-exit annotation.

The canonical report recorded schema `2`, deterministic status `budget_failed`, exit `1`, three validated files, and accepted investigation after one API attempt. Local inspection verified all five required report headings, the local-rendering disclosure, and the exact root-cause uncertainty sentence. It found no credential pattern, private path, or revision-value wording. One invalid optional hypothesis had been filtered under `C03_HYPOTHESIS_TEXT`; accepted recommendations remained.

The artifact contained nine entries: three capture JSON files, three Godot logs, the internal capture manifest, runner capture manifest, and canonical Guardian report. Every capture reported profile `main_scene`, addon `1.0.1`, and 600 samples. The generic validator passed all three files, all logs were free of script-load diagnostics, and artifact scans found no private absolute path or credential pattern.

The renderer writes `GITHUB_STEP_SUMMARY` before emitting its log, so the successful hosted presentation log and absence of its safe warning establish that the append operation completed. GitHub's REST/check-run response returned no custom summary body, and the in-app browser's unsigned public view required sign-in for job details. Direct visual inspection of the Markdown body therefore remains unverified; no extra run was made merely to close that UI-access gap. Final Guardian documentation verification, cleanup, commit, and push follow this entry.

The temporary clone, downloaded log ZIP, artifact ZIP, and extracted evidence were contained beneath the exact `.experiment-14` child directory. That resolved target was verified before recursive removal; remote commits, the workflow run, and its GitHub artifact remain available. The final Guardian suite passed all 160 tests in 4.860 seconds, byte compilation succeeded, `pip check` found no broken requirements, all checked relative links resolved, README retained sections 1 through 17, and `git diff --check` passed. The official documentation-skill validator again printed `Skill is valid!` using temporary PyYAML removed immediately afterward. Final working-tree, tracked-file, and reachable-history credential scans reported no matching filename or commit identifier.

<a id="trajectory-experiment-15"></a>

## 2026-08-30 — Experiment 15 budget calibration assistant

### Request and approved boundary

The user requested:

> PLEASE IMPLEMENT THIS PLAN:
> # Experiment 15: Budget Calibration Assistant
>
> Add a deterministic calibration assistant that converts repeated, validated generic captures into a reviewable schema-v3 budget proposal.

The approved plan requires local generation and explicit application commands, balanced process/node/object formulas, one structured-validator invocation, at least three captures per profile, five hosted captures by default, atomic collision-refusing output, manual/default-branch-only calibration, no AI or enforcement in calibration mode, actionable proposal rendering, a five-run local Godot evaluation, synchronized documentation, Guardian and PluginTest delivery, and exactly one hosted calibration that does not apply its proposal.

### Inspection and implementation

The repository-local documentation skill, its complete README requirements reference, the agent-trajectory skill, and skill-creator guidance were read before documentation or skill changes. Implementation inspection covered `check_budgets.py`, `validate_results.py` evidence shape, workspace containment, capture orchestration, Actions presentation, both workflow contracts, tracked fixtures, the addon example, and current documentation.

`tools/calibrate_budgets.py` now builds schema-v3 rules exclusively from passed generic aggregate evidence. It rejects reserved/global profile metadata as a profile, ambiguous or malformed aggregates, fewer than three contributing runs, unsafe paths, collisions, and synthetic evidence. It gives long rule IDs deterministic SHA-256 suffixes, writes policy and report atomically, and leaves no temporary output. Apply mode reuses the strict budget parser, rejects self-application, creates a missing target, and requires `--replace` for an existing policy.

`render_action_report.py` now dispatches calibration-report schema v1 separately from Guardian verdict schemas. Its log and Markdown summary state that the output is a proposal rather than an enforced verdict, show observed value, margin, proposed maximum, relative allowance, evidence ID, artifact guidance, and the five-step migration sequence.

The reusable workflow defaults to `mode: enforce` and retains three enforcement captures. `budget-file` is optional only at the callable schema boundary and is still checked as required for enforcement. `mode: calibrate` defaults to five captures, is accepted only for manual dispatch on the consumer default branch, forbids comparison and investigation, skips optional dependency installation and `run_guardian.py`, generates the two proposal files, renders them, and stages them with capture evidence. No API secret is referenced by the calibration step.

### Tests and local evaluation

The first focused modules passed after one expectation was updated to reflect the intentionally narrowed optional-dependency condition. The complete initial suite passed 173 tests after the final symlink-containment case was added.

The first temporary consumer copy accidentally included ignored editor state and old results; Godot crashed before producing evidence. A second clean tracked-file export parsed, but its sandboxed capture could not use Godot's normal AppData directories and stopped safely with `godot_exit`. Neither attempt was treated as measurement evidence. The same clean isolated consumer was then run with the required local permission. Exactly five Godot `4.5.1.stable.official.f62fdbde1` processes completed using seed 1337, 120 warmup frames, 600 measured frames, interval 1, and profile `main_scene`.

The five captures passed generic validation. The structured aggregates were `0.421 ms` median process p95, `3` median peak nodes, and `1,393` median peak objects. The balanced proposal contained `0.7 ms` with 20% relative allowance, `4` nodes with 5%, and `1,533` objects with 5%. The proposal was explicitly applied to a separate temporary policy, and `check_budgets.py` reported all three absolute rules passed on the same captures. Repository example policies were unchanged and no OpenAI request or synthetic benchmark ran.

### Delivery and hosted proof

The focused 11-file Guardian change was committed as `a1d0cfd02cffbc626884454cdcd4341dd1c2bd24` with message `Add budget calibration assistant` and pushed to `origin/main`. The public PluginTest caller was cloned into a unique temporary directory. Its manual interface now separates `enforce` and `calibrate`: only enforcement maps `OPENAI_API_KEY`, while calibration passes five runs, comparison false, and investigation never. The one-file change parsed, passed whitespace checks, was committed as `5dde4ee3b4614d1d9aa208ecddbc29fcd9b16c72` (`Add Guardian budget calibration workflow`), and was pushed to PluginTest `main`.

The GitHub CLI was unavailable; that command failed locally before any network dispatch. One authenticated REST dispatch was then made, using the existing Git credential only in process memory and never printing or storing it. HTTP `204` created [PluginTest run 33288045948](https://github.com/TaofeekS/PluginTest/actions/runs/33288045948). No second dispatch or AI request occurred.

The hosted job completed successfully. Protected-base checkout/capture, investigator dependency installation, the authoritative enforcement gate, and AI were skipped. Candidate capture, calibration generation, presentation, staging, and upload succeeded. The artifact contained exactly fourteen files: five capture JSON files, five clean Godot logs, internal and runner manifests, the canonical calibration report, and proposed schema-v3 policy. Every capture had 600 samples; all five validated, no log contained script-load diagnostics, and scans found no private absolute path or credential-shaped value.

Hosted aggregate medians were `11.62 ms` process p95, `2,281` peak nodes, and `5,580` peak objects. The proposal contained `17.5 ms` with 20% relative allowance, `2,510` nodes with 5%, and `6,138` objects with 5%. Read-only evaluation of that proposed policy against the same hosted captures passed all three absolute rules. The proposal was not applied or committed to PluginTest.

The downloaded Actions log contained the proposal-only warning, the five-capture validation count, and all three observed/proposed recommendation pairs. It contained no API-request marker. Because the renderer appends `GITHUB_STEP_SUMMARY` before printing those lines and returned success, the hosted summary write also completed; direct signed-in visual inspection of the rendered Markdown body remains a UI-access limitation rather than a workflow failure.

### Final verification and cleanup

The complete final suite passed 173 tests in 4.994 seconds with one environment-dependent symlink test skipped because directory symlink creation was unavailable. Python byte compilation succeeded, `pip check` reported no broken requirements, both workflows parsed, and the official documentation-skill validator printed `Skill is valid!`. README retained numbered sections 1 through 17, every checked relative Markdown link resolved, all evidence documents had final newlines, and `git diff --check` reported no whitespace error. Key-shaped working-tree and tracked-file scans returned no filename, and no reachable commit identifier matched the key-shape patterns.

The initial dirty temporary consumer, clean local consumer, temporary PyYAML target, PluginTest clone, and downloaded hosted artifact were each resolved beneath the system temporary directory and required an expected unique Guardian prefix before recursive removal. All five exact targets were removed; no remote repository, workflow artifact, committed fixture, or local historical benchmark result was deleted. Final Guardian documentation commit, push, remote SHA check, and Git state follow this entry.

<a id="trajectory-experiment-16"></a>

## 2026-08-30 — Experiment 16 editor evidence dock

### Request, planning, and corrections

The user first requested:

> Editor dock\
> Display probe status, recent captures, failed rules, and links to evidence inside Godot.

Repository inspection established that the addon registered only `PerformanceBudgetProbe`, raw captures contained measurements but not verdicts, and failed rules existed only in canonical Guardian reports. The user selected the recommended read-only scope, automatic project scanning plus project-contained import, and setup-readiness status without live-progress claims. The approved plan was titled **Experiment 16: Godot Editor Evidence Dock**.

The user then corrected two implementation details:

> Godot 4.5 documents:
>
> add_control_to_dock(...)
> remove_control_from_docks(...)
>
> It does not document a method simply called add_dock. Use the exact API names in the implementation plan and tests.

and required schema-specific evidence time, explicitly prohibiting filesystem modification time. Inspection confirmed generic capture v1 contains required `ended_at_utc`, while Guardian report v1/v2 and calibration report v1 currently contain no canonical report timestamp. The final approved plan therefore placed valid untimestamped reports after timestamped captures and treated an invalid capture timestamp as invalid evidence.

### Skill use and inspection

The complete repository-local documentation skill, its `references/readme-requirements.md`, and the complete `agent-trajectory` skill were read before documentation work. Inspection included Git status/history, `git remote -v`, the addon entrypoint and manifest, runtime probe, validator addon identity, canonical capture and report shapes, tracked fixtures, portable-addon tests, both evidence documents, root/addon READMEs, local tool versions, and Godot 4.5 editor documentation. The configured fetch/push remote remained the public `https://github.com/TaofeekS/godot_performance_guardian.git`; Python was 3.14.6, PowerShell was 7.6.4, and the required local Godot executable reported `4.5.1.stable.official.f62fdbde1`.

### Implementation

`evidence_reader.gd` was added as a bounded read-only presentation parser. It accepts project-contained JSON only, rejects lexical traversal and traversed links, limits scans to 1,000 JSON files and individual files to 8 MiB, redacts unsafe display text, recognizes generic capture v1, Guardian report v1/v2, and calibration report v1, and never exposes revision values. Captures require a valid calendar-aware canonical `ended_at_utc` and sort newest first; untimestamped reports sort afterward by type and normalized `res://` path; invalid evidence sorts last. Failed absolute and relative results are merged by rule ID for presentation without recomputing policy.

`performance_guardian_dock.gd` was added as a read-only editor `VBoxContainer`. It displays active-scene probe readiness, configured frames/output, latest matching capture, up to 20 recognized evidence files, invalid-file warnings, deterministic failed rules, safe details, proposal-only calibration recommendations, FileSystem navigation, and path copying. It scans probe outputs, `res://results`, `res://.performance-guardian`, and session-selected project JSON. It launches no process, validator, budget checker, network request, or AI operation.

`plugin.gd` now creates the dock with exact `add_control_to_dock(DOCK_SLOT_RIGHT_BL, _dock)`, refreshes it through debounced scene/filesystem signals, removes it with exact `remove_control_from_docks(_dock)`, then frees it. Addon and capture metadata advanced to `1.1.0`. Because the dock does not change capture schema or the mandatory limitation, the validator now accepts historical `1.0.1` and current `1.1.0` captures; `1.0.0` remains rejected with an actionable current-version diagnostic.

Five compact tracked editor fixtures, a Godot helper, and `tests/test_editor_dock.py` were added. Existing addon tests now require the new files and verify both compatible addon versions. Documentation was synchronized across the root README, addon README, documentation-skill requirements, and append-only Experiment 16 changelog.

### Failures and responses

The first Godot editor attempt ran under restricted filesystem access, could not create its `user://` directory, and crashed with signal 11 before a meaningful addon result. It was rerun with normal local access as an environment correction, not treated as product evidence.

The first meaningful editor parse found two new-code compile errors: the dock attempted to read a preloaded script's resource path as a static member, and a nullable latest-capture value lacked an explicit type. The comparison now uses the canonical script path constant and the nullable value is explicitly typed.

The first explicit helper check then rejected a valid Guardian report because Godot JSON may materialize an integral JSON number without static `int` type. The parser now accepts only finite integral numeric exit codes and normalizes them to `int`; the helper was also changed to prevent a rejected report from causing a secondary property-access error.

Direct Godot invocation on this Windows executable returned control before the child finished, causing the first pass-marker check to race. Delayed output still printed `PBG_EDITOR_DOCK_TESTS=passed`. Verification was corrected to use hidden `Start-Process -Wait`, after which the marker was read as `passed` and removed. A check-only wrapper also produced an unusable null `$LASTEXITCODE`; synchronized process waiting replaced that wrapper.

The first official skill-validator attempt failed only because PyYAML was absent. PyYAML 6.0.3 was installed into a unique temporary target, the validator printed `Skill is valid!`, and the target was removed. Two exploratory verification commands had command-expression issues—one malformed search regex and one root-relative Markdown-link base calculation. Both were corrected; neither changed repository files or implementation behavior.

Godot editor initialization rewrote `examples/minimal_project/project.godot` formatting and added an engine feature line. That unrelated generated edit was removed with a focused patch, restoring the tracked file byte-for-byte.

### Verification evidence and remaining gap

The focused dock/addon suite passed 19 tests. The final complete repository suite passed 180 tests in 4.932 seconds with one environment-dependent directory-symlink test skipped. Python byte compilation succeeded, `pip check` reported no broken requirements, and the tracked generic fixture plus historical canonical `1.0.1` fixture both validated successfully after the compatibility update.

The synchronized Godot 4.5.1 helper produced its ignored `passed` marker, which was immediately removed. A synchronized three-second headless editor lifecycle exited `0`; its temporary stdout/stderr logs contained no `SCRIPT ERROR`, `Parse Error`, invalid-call, or failed-script-load diagnostic and were removed. No performance capture, original synthetic benchmark, hosted workflow, or OpenAI request ran.

The editor process exercised plugin parsing and lifecycle but the current automation environment could not directly inspect the rendered dock visually. Layout appearance and hands-on interaction therefore remain unverified and are documented as the next evaluation step. No commit or push was requested or performed during Experiment 16.

<a id="trajectory-experiment-17"></a>

## 2026-08-30 — Experiment 17 main-screen evidence workspace

### Original request and approved plan

After installing Experiment 16 in the public PluginTest example, the user reported:

> the dock is covering the whole left side of the scren making it hard to check inspector and and node tab
>
> can we make it like dialogic tab that will be in the same place as the 2d 3d script game asselib at the top middle
>
> so it will be easy to access without destroying the current workarea

Inspection confirmed that addon `1.1.0` used `add_control_to_dock(DOCK_SLOT_RIGHT_BL, _dock)`, so it necessarily competed with an editor side-dock slot. Godot 4.5's `EditorPlugin` class reference documents main-screen plugins in the workspace selector beside 2D, 3D, Script, Game, and AssetLib. The user selected the compact **Guardian** tab label and requested Experiment 17 delivery to both Guardian and PluginTest. The approved implementation plan replaced the side dock completely, retained the central page title **Performance Guardian**, advanced the addon to `1.2.0`, preserved old capture compatibility, and prohibited captures, workflows, benchmarks, and API requests during this change.

### Skill use and inspection

The complete repository-local `$godot-performance-guardian-docs` skill, its complete README requirements reference, and the complete `$agent-trajectory` skill were read before documentation edits. Inspection covered Git state and the configured public remote, the addon manifest and plugin entrypoint, the evidence presentation and parser scripts, validator version handling, focused addon tests, the included independent project, all three evidence documents, and the official Godot 4.5 main-screen `EditorPlugin` contract.

### Implementation

`performance_guardian_dock.gd` was renamed to `performance_guardian_main_screen.gd`. The existing read-only content and evidence data flow remain intact, while its root now expands across the central editor area. `plugin.gd` creates that control beneath `EditorInterface.get_editor_main_screen()`, hides it initially, reports `_has_main_screen() == true`, exposes the **Guardian** name and a built-in icon, and changes visibility only when Godot calls `_make_visible()`. Disabling the plugin removes the control from its parent before freeing it. All dock-slot APIs and automatic workspace-selection APIs were removed.

The addon and capture metadata advanced to `1.2.0`. The validator accepts historical `1.0.1`, Experiment 16 `1.1.0`, and current `1.2.0` captures while continuing to reject `1.0.0` with the current-version recapture diagnostic. Presentation and helper tests were renamed for the main-screen interface, and contract tests now require the documented main-screen methods and reject side-dock registration.

### Test and operational evidence

No focused or complete Python test failed. The focused addon/main-screen run passed 19 tests. The complete suite passed 180 tests in 4.936 seconds with one environment-dependent directory-symlink test skipped. Python byte compilation completed, and the tracked generic test fixture plus historical canonical fixture each validated successfully.

The canonical addon was copied temporarily into the ignored independent example. Its Godot 4.5.1 evidence helper exited `0`, wrote the synchronized `passed` marker, and the marker was read and removed. A three-second headless editor lifecycle then exited `0` with no `SCRIPT ERROR`, parse error, invalid-call, failed-script-load, or other matched script diagnostic. The temporary copied addon was resolved beneath the example project before removal. No project configuration diff remained.

The automation can verify plugin registration, parsing, lifecycle, and absence of side-dock APIs, but it cannot directly observe the rendered top toolbar or hands-on switching between Guardian and 2D/3D/Script. Those visual interaction claims remain pending confirmation after PluginTest receives the published addon. No performance capture, synthetic benchmark, hosted workflow dispatch, or OpenAI request occurred.

### Documentation verification and operational issue

The first official documentation-skill validation attempt failed because the project environment does not include PyYAML. A temporary-target installation was then attempted under restricted network access and could not reach the package index; that target was removed by the command's cleanup block. The same temporary-only procedure was authorized with normal network access, installed cached PyYAML 6.0.3, printed `Skill is valid!`, and removed the unique temporary target. No permanent dependency was added.

The synchronized documentation describes the main-screen API and read-only boundary, keeps Experiment 16 as historical side-dock evidence, and marks direct visual confirmation as pending. README retained all 17 numbered sections, every checked relative Markdown link resolved, all five evidence/requirements documents ended with a newline, `git diff --check` found no whitespace error, and working-tree, tracked-file, and reachable-history key-pattern scans found no filename or commit identifier to report.

### Delivery to Guardian and PluginTest

The focused Guardian change was committed as `80ba5d6fa829b4e947eff8e4aee0f540727aa58a` with message `Move Guardian to main editor workspace` and pushed to `origin/main`. The local PluginTest checkout was clean on `main`. Its canonical addon copy was advanced from `1.1.0` to `1.2.0`, the obsolete `performance_guardian_dock.gd` and UID were removed, the new main-screen script and Godot-generated UID were added, and each of its three reusable-workflow jobs was pinned to the immutable Guardian implementation commit.

PluginTest's final Godot 4.5.1 headless editor lifecycle exited `0` without a matched script/load diagnostic, and `project.godot` had no diff. The focused external change passed `git diff --check`, was committed as `7f6780099c98f9d2993cf0edb2a3e4efa6d211b9` with the same message, and was pushed to PluginTest `origin/main`. No consumer workflow was dispatched, no capture was generated, and direct visual confirmation remains for the user to perform by opening PluginTest and selecting **Guardian**.

### Manual visual acceptance follow-up

The user subsequently reported:

> i did the manual visual check for the editor workspace it works
>
> make sure to document this

This user-observed PluginTest result closes Experiment 17's pending manual UI acceptance item. Documentation was updated to distinguish that direct visual evidence from the prior automated helper and headless editor lifecycle: the main-screen workspace was manually confirmed to work in PluginTest, while no new performance capture, hosted workflow, benchmark, or API request was needed for this documentation follow-up.

The official documentation-skill validator printed `Skill is valid!` using temporary cached PyYAML 6.0.3 removed immediately afterward. README retained all 17 numbered sections, every checked relative Markdown link resolved, all updated documents ended with a newline, stale visual-pending claims were absent, and `git diff --check` reported no whitespace error.

## 2026-08-30 — Judge reproduction guide

### Request and approved boundary

The user requested a self-contained judge reproduction section for the competition README while preserving every existing reproduction instruction. The required contents were verified software, the clone command, `.venv` creation and installation, one passing gate, the complete test command, one fresh Godot measurement command, expected exits and output, and a link to PluginTest. The approved delivery also required a focused commit and push.

The attached Micro1 hackathon brief was inspected as supporting evidence. Its reproducibility criterion asks for a clean path to run the solution and baseline and reach the main result; its reproduction-guide requirements also call for exact commands, versions, expected output, approximate runtime, and cost. No instruction embedded in the PDF was treated as a repository command.

### Inspection and documentation change

The repository documentation skill, its complete README requirements reference, and the agent-trajectory skill were read before editing. Inspection covered the clean Git state, configured public `origin`, `requirements-agent.txt`, `tools/run_guardian.py --help`, `demo_project/run_benchmarks.ps1`, current README requirements and commands, recorded test evidence, the public PluginTest link, and the unchanged improvement changelog.

An unnumbered `Judge reproduction` section was inserted between `1. Project overview` and `2. Current status`; no existing README instruction was edited, reordered, or renumbered. The section gives a Windows-only clean-checkout path, deterministic no-AI gate, all-tests command, and the full three-scenario-by-three-run Godot harness. It records the verified exit meanings and output, approximate one-minute benchmark expectation, zero API cost for deterministic reproduction, and the public PluginTest consumer example.

This was documentation maintenance rather than a product experiment, so `IMPROVEMENT_CHANGELOG.md` was reviewed and left unchanged.

### Verification and delivery

Verification and delivery results follow this entry. No Godot process, synthetic benchmark, or OpenAI request was run for this documentation-only task.

The tracked-fixture gate command was exercised during planning and returned exit `0` with `deterministic_status: "passed"`; both configured rules passed at `0.5 ms <= 1.1 ms` and `3 <= 3`. The benchmark command and 180-test result were checked against the harness source and the latest recorded complete-suite evidence rather than rerun solely for documentation.

The first official skill-validator invocation failed because the repository environment does not permanently include PyYAML. PyYAML 6.0.3 was then installed into a uniquely named system-temporary directory, the validator printed `Skill is valid!`, and the temporary directory was removed. One composite read-only inspection wrapper also had a JavaScript quoting error before executing any nested command; its two checks were rerun successfully. The initially inserted trajectory block preceded the earlier manual-acceptance follow-up, so it was moved to the true chronological end before delivery.

README retained numbered sections 1 through 17, the judge section occupied the requested position, all checked relative links resolved, and all three evidence documents retained final newlines. The focused key-pattern scan found no matching filename, `IMPROVEMENT_CHANGELOG.md` had no diff, and `git diff --check` reported no whitespace error. Final diff inspection, commit, push, and remote verification followed this pre-delivery checkpoint.

<a id="trajectory-experiment-18"></a>

## 2026-08-30 — Experiment 18: Final ten-case competition evaluation

### Original request and approved boundary

The user requested a reproducible final competition evaluation comparing the accepted Baseline 0 implementation at commit `22af3b44962517b0f1d7ac0b7499f724f2e2cb34` with the current product at commit `2bf5ff6efbedb44a8ac0370b686554a5a4ac4e40`. The primary metric was fixed in advance as **correct actionable outcomes** over ten shared cases. The task required a frozen baseline package, tracked fixtures, a standard-library evaluator, canonical deterministic output, `FINAL_EVALUATION.md`, synchronized repository documentation, and tests for integrity, safety, containment, exit codes, score recomputation, and byte stability.

The approved boundary excluded Godot execution, OpenAI requests, commits, and pushes. Unsupported Baseline 0 interfaces had to remain visibly `unsupported` rather than being simulated or counted as tool failures. The result had to describe expanded workflow coverage, not game-speed improvement.

### Skill use and repository inspection

The complete repository-local `$godot-performance-guardian-docs` skill and requirements reference were read before documentation changes. The supplied `$agent-trajectory` instructions governed this chronological record. Inspection covered the clean Git state, configured public remote, both comparison revisions, Baseline 0 source, current validator/checker/gate/calibration interfaces, existing fixed fixtures, ignored historical evidence, README status claims, experiment history, and the hackathon reproduction requirements already summarized in the repository documentation.

The first candidate historical suite tested with the frozen baseline validator was not the accepted Baseline 0 evidence: it produced `143 usec` healthy workload p95, `5,091 usec` CPU-spike workload p95, and a `35.60x` ratio. All available nine-file suites were then evaluated consistently. Suite `20260828T193246205Z` reproduced the documented accepted measurements: `185 usec`, `12,725 usec`, and `68.78x`, with all nine files valid. That suite was selected and frozen rather than changing the documented baseline to fit the first available files.

### Evaluation package and implementation

`evaluation/` now contains the frozen Baseline 0 validator, source revision, SHA-256 integrity manifest, accepted nine-file synthetic suite, compact generic/comparison/malformed/calibration fixtures, strict policies, a shared ten-case manifest, and canonical output. The frozen validator hash is `6277baaacfc9a62734e3b72d94fa4fe03e742c5a78fd8b40d52b2f0c3226d412`.

`tools/run_submission_evaluation.py` uses only the Python standard library. It resolves repository-contained paths, verifies fixture and implementation hashes, launches fixed argument-list subprocesses with `shell=False`, captures their output under bounded timeouts, normalizes only safe facts, recalculates both scores from raw case results, and provides exit `0`, `1`, or `2` for complete success, missed final oracle, or integrity/configuration/operational failure. Its canonical JSON excludes timestamps and observed runtime so repeated inputs remain byte-identical.

The same manifest defines all ten cases for both implementations: the accepted synthetic suite, generic validation, a passing v2 policy, process failure, node failure, multiple failures, unchanged v3 comparison, a relative-only regression, malformed evidence, and three-capture calibration. The challenge fixture deliberately measures baseline `0.5 ms` and candidate `0.61 ms`: the candidate passes the `1.1 ms` absolute ceiling but its `22%` increase fails the `20%` relative allowance.

### Failures encountered and corrections

The first complete evaluator run exposed two implementation/oracle mismatches. Absolute fixture paths were passed to `run_guardian.py`, whose public containment contract requires repository-relative inputs; those cases safely exited `2`. The evaluator was corrected to pass paths relative to the already validated workspace root. The calibration oracle also expected hyphenated IDs, while the real deterministic generator correctly preserved the safe profile identifier `main_scene`; the manifest was corrected to match the tool's actual IDs. The initial partial score was not retained as product evidence. After correction, the complete final side passed all ten oracles.

Focused testing also exercised deliberate negative paths: integrity mismatch, unsafe containment, malformed manifest, subprocess timeout and operating-system errors, output collision, and CLI exits `0`, `1`, and `2`. No raw subprocess output, private absolute path, credential-shaped value, source-revision value, or unsupported causal claim is preserved in the canonical result.

### Measured results and verification

The focused evaluator suite passed 19 tests in `10.045` seconds. Two consecutive real evaluator runs were byte-identical with SHA-256 `d88261711f9fa836903137d5a9099a5102691a08ff7e2b59cb29518119d2e453`; one observed run took `3.515` seconds. Baseline 0 produced one correct actionable outcome from ten (`10%`) and nine honest `unsupported` results. The final product produced ten from ten (`100%`), a gain of nine cases or **90 percentage points**. Deterministic API cost was `$0`, and human review time was not measured.

The complete repository suite passed 199 tests in `15.052` seconds with one environment-dependent directory-symlink test skipped. Python byte compilation completed, `pip check` reported no broken requirements, and the existing tracked deterministic gate returned exit `0` with `0.5 ms <= 1.1 ms` and `3 <= 3` nodes. No Godot process, benchmark, OpenAI request, commit, or push occurred.

### Documentation result and remaining boundary

`FINAL_EVALUATION.md` records the intended user, bottleneck, fairness and resource difference, fixed rubric, full ten-case table, challenging-case evidence, observed runtime, deterministic cost, supporting-but-secondary AI evidence, failed-model lesson, remaining failure mode, hot take, and conclusion. README keeps its existing reproduction instructions and adds the one-command final comparison, tracked package links, updated roadmap/evidence status, and correct 199-test expectation. The documentation requirements now preserve the fixed-manifest, revision, integrity, score, and scope-warning contract. Experiment 18 was appended to `IMPROVEMENT_CHANGELOG.md` without rewriting prior experiments.

The remaining submission deliverable is the five-minute solution video. Fixed fixtures establish reproducible tool decisions, not universal project compatibility, GPU behavior, project-owned object attribution, threshold quality, or long-run model reliability.

### Final documentation and integrity checks

A final canonical check first piped evaluator text through PowerShell `Set-Content`; that text round trip changed the file bytes and therefore was not a valid byte-stability comparison. A second attempt correctly used the evaluator's atomic `--output` option but supplied a system-temporary absolute path, which the containment contract rejected with exit `2`. The final check used a unique repository-relative output, returned exit `0`, matched the tracked canonical SHA-256 exactly, and removed the temporary file. These rejected attempts changed no tracked evidence and confirmed that output containment is enforced.

The official skill validator initially failed because PyYAML is not a permanent project dependency. A sandboxed temporary installation could not reach the package index. The same temporary-only procedure was then authorized with normal network access, installed cached PyYAML 6.0.3, printed `Skill is valid!`, and removed the temporary directory. No dependency was added to the repository environment.

All checked Markdown links resolved, README retained numbered sections 1 through 17, every updated evidence/requirements document ended with a newline, and `git diff --check` reported no whitespace error. The workspace plus reachable-history high-confidence key-pattern scan returned no matching filename or commit identifier. Final Git status contained only the intended evaluation implementation, tracked fixtures/result, tests, final report, and synchronized documentation; no commit or push was performed.

<a id="trajectory-experiment-18-integrity"></a>

## 2026-08-30 — Experiment 18 cross-platform integrity correction

### Reported failure and diagnosis

The user reported the exact reproduction failure:

> EvaluationError: integrity mismatch for evaluation/baseline/validate_results.py

Inspection found a clean working tree at commit `5b8c7689147e5741054be2e5090e3c0942964e07`. The frozen validator's Git index and Baseline 0 source were byte-identical LF text with SHA-256 `d4c99669b2b2ef20ede75944a0445d915802d4a25060c81c2dfbcbbf86016d96`. The Windows working copy used CRLF and matched the manifest's old hash `6277baaacfc9a62734e3b72d94fa4fe03e742c5a78fd8b40d52b2f0c3226d412`. Auditing every manifest member showed this was the only working-tree/index mismatch. The evidence was not corrupted; schema v1 had accidentally made Git line-ending policy part of the integrity verdict.

The approved correction rejected a raw-byte LF-only manifest because an existing Windows checkout could still retain CRLF after pulling it. Instead, integrity schema v2 declares `sha256_utf8_lf`: each member must decode as UTF-8, CRLF and lone CR become LF, and SHA-256 is calculated over the normalized UTF-8 bytes. All non-line-ending content remains significant.

### Implementation and tests

The evaluator now strictly requires integrity schema v2 and the declared hash mode, safely rejects malformed UTF-8, and reports genuine mismatches without exposing raw content. The manifest records the canonical Baseline 0 hash `d4c99669b2b2ef20ede75944a0445d915802d4a25060c81c2dfbcbbf86016d96`. The frozen validator, fixtures, case manifest, expected outcomes, compared revisions, and canonical result were not changed.

Four focused behaviors were added: LF/CRLF/lone-CR equivalence, substantive-change detection, strict schema/hash-mode rejection, and invalid-UTF-8 rejection. The focused evaluator suite passed 22 tests in `10.100` seconds. Two real current-checkout evaluations returned exit `0` and exactly matched the existing canonical SHA-256 `d88261711f9fa836903137d5a9099a5102691a08ff7e2b59cb29518119d2e453`.

A Git archive of the committed repository was expanded into a unique temporary directory and overlaid only with the pending evaluator and manifest correction. The first extraction retained CRLF on this Windows host, so it did not exercise the failing representation. The frozen validator in a second export was explicitly converted to LF, its raw hash matched `d4c99669...`, and the complete ten-case evaluator returned exit `0`. Both temporary exports and archives were removed.

The complete repository suite passed 202 tests in `14.962` seconds with one environment-dependent directory-symlink test skipped. `pip check`, Python byte compilation, and the existing no-AI deterministic gate passed; the gate again measured `0.5 ms <= 1.1 ms` and `3 <= 3` nodes. No test failed, no Godot process or OpenAI request ran, and no commit or push was performed.

### Documentation result

README and `FINAL_EVALUATION.md` now define the portable UTF-8/LF integrity rule. The Experiment 18 changelog history retains the original result and adds this portability clarification. The repository documentation requirements preserve the schema-v2 contract. Final documentation-skill, link, secret, newline, and whitespace verification follows this entry.

The official documentation-skill validator printed `Skill is valid!` using temporary cached PyYAML 6.0.3, which was removed immediately afterward. Every checked relative Markdown link resolved, README retained numbered sections 1 through 17, all documentation files ended with a newline, and `git diff --check` reported no whitespace error. The workspace and reachable-history high-confidence credential-pattern scan found no matching filename or commit identifier. Final status contained only the eight intended correction files.

## 2026-08-30 — Judge trajectory navigation

### Request and structural decision

The user asked how to make the agent trajectory easy for a competition judge to navigate, then selected the recommended additive top-index design rather than splitting or condensing the audit. The approved plan required a two-minute evidence route, explicit agent/tool authority boundaries, four representative trajectories, a Baseline 0-through-Experiment 18 milestone index, a failure/correction index, a collapsed-but-preserved original request, a README deep link, and a durable documentation-skill contract.

Inspection measured the pre-change trajectory at 2,119 lines and 206,535 bytes. The final evaluation began near line 2,045, and the file had no judge-facing contents map. The chronology contained strong evidence but gave setup, experiments, corrections, and delivery entries equal visual weight.

### Documentation change

The new top layer identifies the shipped **Godot Performance Investigator**, the build-time **Codex development agent**, and the deterministic validator, budget checker, calibration assistant, and unified runner without conflating their authority. It records the investigator's single `validate_benchmark_results` tool and preserves deterministic exit authority. The primary snapshot is derived from canonical evaluation evidence: Baseline 0 `1/10`, final `10/10`, change `+90` percentage points, and deterministic API cost `$0`.

Four short trajectories link accepted investigation, rejected-model fallback and typed redesign, script-invalid evidence correction, and the user-confirmed editor usability change to their detailed history. Explicit stable anchors support all 19 milestone rows and the major correction links. The long original documentation request remains verbatim but is collapsed behind a Markdown disclosure. README now deep-links directly to judge navigation, and the repository documentation requirements preserve the new structure.

This was documentation maintenance rather than a product experiment, so the existing `IMPROVEMENT_CHANGELOG.md` content was inspected and not changed by this navigation task. Verification follows this entry; no Godot process, OpenAI request, or full test-suite rerun is required.

All 33 internal trajectory links resolved against unique headings or explicit anchors, and all checked relative file links existed. The canonical result independently confirmed `1/10`, `10/10`, `+90` percentage points, and API cost `$0`. Source inspection confirmed the investigator's exact name and sole function tool plus the deterministic validator, checker, calibration, and runner boundaries. The official documentation-skill validator printed `Skill is valid!` using temporary cached PyYAML removed immediately afterward. README retained sections 1 through 17, the single disclosure block was balanced, all documentation files ended with a newline, `git diff --check` passed, and working-tree plus reachable-history credential-pattern scans found no matching filename or commit identifier. No product test, Godot process, OpenAI request, commit, or push occurred.

## 2026-08-30 — Multi-scene roadmap documentation

### Request and evidence inspection

The user proposed testing additional scenes alongside the main scene and approved documenting first-class multi-scene testing as a future step. They also asked to remove the obsolete media-deliverable wording from current-facing documentation while preserving append-only history.

Inspection confirmed that `.github/workflows/reusable-performance-guardian.yml` currently exposes one required `profile` and one optional `scene-path` per invocation. The generic validator already groups validated captures by profile, and the v2/v3 budget checker matches profile-scoped evidence semantically. Therefore the missing capability is customer-facing multi-scene capture and workflow orchestration, not basic multi-profile aggregation. The included independent example currently contains only `main.tscn`.

### Documentation decision

README now labels manifest-driven multi-scene orchestration as planned, records separate workflow jobs as the current workaround, proposes main, object-heavy, and physics-heavy example scenes, and explains that capture processes scale as scenes multiplied by runs and double during protected-base comparison. No implementation or verification claim was added.

Current-facing README and final-evaluation wording now treats final submission assembly generically. Older trajectory and improvement-changelog statements remain unchanged as historical evidence. The documentation-skill requirements preserve both the multi-scene implementation boundary and this current-versus-historical distinction. This was documentation maintenance, so no product experiment was appended to `IMPROVEMENT_CHANGELOG.md`. No Godot process, product test, workflow, capture, or OpenAI request was run.

Verification confirmed that README and `FINAL_EVALUATION.md` contain no remaining obsolete media-deliverable reference, README retains numbered sections 1 through 17, every checked relative Markdown link resolves, and all maintained documentation files end with a newline. The official documentation-skill validator printed `Skill is valid!` using temporary PyYAML 6.0.3, which was removed afterward without changing project dependencies. The checked documentation contained no high-confidence credential pattern, and `git diff --check` reported no whitespace error. Final status contained only the four intended documentation files.
