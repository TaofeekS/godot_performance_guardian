# README Requirements

Use this contract whenever creating or substantially revising the root `README.md` for Godot Performance Budget Guardian.

## Status classification

- **Implemented:** present in the workspace and supported by code or direct evidence.
- **Verified:** exercised successfully with recorded output. State the exact environment and avoid generalizing results.
- **Partial:** a narrower mechanism exists but does not satisfy the complete product concept.
- **Planned:** requested or roadmapped but absent from the implementation.
- **Unverified:** plausible or supported by generic tooling, but not exercised in this repository.

When prose requirements conflict with repository evidence, preserve the requested topic but describe the missing capability honestly. Never invent a file, schema, command result, platform, integration, or license.

## Required sections

The README must cover these topics, using clear GitHub-flavored Markdown and relative links:

1. Project title and one-paragraph description of repeatable performance-regression detection and preserved diagnostic evidence.
2. Current status divided into implemented, partial, and planned capabilities.
3. Intended developer, the difficulty of noticing regressions manually, the value of repeatable limits, and the distinction from viewing Godot's profiler.
4. Current baseline behavior, including collection, evaluation, pass/fail reporting, and the absence of automated investigation when applicable.
5. An accurate repository tree and the purpose of important files and folders. Planned files must be explicitly labeled and not linked as if present.
6. Exact verified Godot, Python, PowerShell, and OS versions; debug-build behavior; dependencies; and network or API-key requirements.
7. Windows PowerShell quick start for obtaining/opening the checkout, opening Godot, each scenario, the evaluation harness, independent validation, and result location. Verify the current Git remote and use its fetch URL for clone instructions when configured; use a labeled placeholder only when no remote exists. Add other platforms only after verification.
8. Implemented methodology: seed, actors, warmup, measurement count, sampling order, repeated runs, metrics, cleanup boundaries, percentiles, duration, and raw evidence.
9. Each scenario's workload, represented regression, expected changing metrics, and expected outcome.
10. Current budget storage, field or assertion meaning, how it can be changed, healthy-run calibration, and machine-comparison warning. Do not imply a configurable schema exists when thresholds are embedded in code.
11. A real or schema-accurate abbreviated JSON example plus raw samples, summaries, engine/scenario metadata, verdict location, and error reporting behavior.
12. Objective evaluator checks and actual verified output only when available.
13. Reproducibility constraints, measurement noise, warmup/repetition, headless rendering limitations, and recorded environment configuration.
14. Relevant limitations, including synthetic coverage, Godot/GDScript/platform scope, debug-only metrics, headless GPU limits, and missing product features.
15. Seven roadmap stages: deterministic baseline, configurable budgets, ten fixtures, editor dock, investigation agent, experimental fixes, and final comparison/submission package. Mark completion only from evidence.
16. Hackathon evidence: agent trajectory, improvement changelog, and baseline/iteration/final results. Explain missing artifacts and distinguish process history from product-change history.
17. Actual license, or an explicit statement that none has been selected.

The README may add a short section for the repository-local documentation skill, provided the required topics remain present and the skill is not confused with the runtime product.

## Repository-specific invariants

- The project is synthetic and must not use or mention unrelated private-project implementation details, private assets, or proprietary telemetry.
- Use the argument names implemented by the controller: `--scenario`, `--run-id`, and `--output`.
- Treat direct `workload_time_usec` as the primary CPU comparison and Godot process time plus duration as supporting evidence.
- Explain scenario-owned counts separately from noisy engine-global counts.
- Explain that `MEMORY_STATIC` can be unavailable and must then be represented as `null`, not a valid zero.
- Explain that the portable probe retains raw samples during capture, so static-memory growth includes probe storage overhead and cannot by itself prove a project memory leak. Memory-budget comparisons must use matching measured-frame counts and sampling intervals.
- Explain atomic temporary-file writing and refusal to overwrite an existing final result.
- Preserve the consumer-workflow contract: installing the addon is distinct from enabling CI; the caller commits the addon, an automatically starting probe, and a v2 or v3 budget; the workflow defaults to three isolated captures, comparison is opt-in, AI defaults off, and deterministic exits remain authoritative.
- Preserve the multi-scene roadmap boundary: the current reusable workflow accepts one profile and one optional scene path per invocation, while first-class manifest-driven multi-scene capture remains planned. Document separate per-scene workflow jobs as the current workaround and state that future capture cost scales as scenes multiplied by runs, doubled for protected-base comparison.
- Require clean sanitized Godot logs and a passed capture manifest before documenting a consumer capture as valid. State that script parse/load diagnostics invalidate independently written probe JSON and must prevent validation, budgets, and investigation from treating it as authoritative evidence.
- Document schema-v3 paired comparison accurately: a protected-base policy controls both absolute and per-rule relative limits; `--baseline-results` requires v3; zero-baseline percentage behavior is explicit; and v1/v2 commands remain compatible.
- Preserve the safe migration order: merge a schema-v3 policy while `compare-with-base` is false, then enable comparison in a later pull request so the protected base already contains that policy.
- State that comparison requires a pull-request event, captures base then candidate sequentially on the same runner with identical settings, and doubles the configured capture count. Describe same-runner sequencing as noise reduction, not proof of identical thermal, scheduling, or system-load conditions.
- Verify `.github/workflows/reusable-performance-guardian.yml` before documenting its inputs, defaults, artifacts, secret scope, or action versions. Preserve the immutable `chickensoft-games/setup-godot@f166999204a4f2722c6fe042fbaa3b3ea0d9c789` pin unless implementation evidence changes it.
- Preserve the hosted artifact contract: normalize and stage the narrow evidence set before upload; include candidate evidence and reports in absolute-only mode; include baseline plus candidate evidence and both manifests in comparison mode; never pass interpolated `.` or `..` path segments to the artifact action. Distinguish a deterministic gate result from a later artifact-preservation failure.
- Preserve the actionable Actions-reporting contract: canonical JSON remains authoritative and unchanged; logs list measured values and thresholds; one escaped annotation represents each failed rule; the Markdown job summary separates deterministic tables from non-authoritative accepted/fallback AI; renderer failure cannot alter the previously saved exit; and rejected text, credentials, private paths, raw exceptions, and revision values are suppressed.
- Preserve the calibration contract: reusable mode defaults to `enforce`; `budget-file` remains required there but not for `calibrate`; hosted calibration is manual/default-branch-only, defaults to five captures, forbids comparison and AI, and creates a proposal rather than a verdict. Document balanced process/node/object formulas, the minimum three validated captures, collision-safe atomic output, explicit `--replace`, and the five-step review/migration sequence. Never imply that calibration edits, commits, or authorizes policy automatically.
- Preserve the editor-workspace contract: it is a read-only Godot 4.5 main-screen plugin named **Guardian**, added beneath `EditorInterface.get_editor_main_screen()`, declared through `_has_main_screen()`, and shown only through `_make_visible()`. It must not register a side dock, automatically switch workspaces, launch captures or tools, or calculate budgets from raw JSON. Document active-scene readiness, project-contained evidence only, schema-specific timestamps, the 20-item recognized-evidence view, calibration's proposal-only status, and canonical Guardian reports as the sole failed-rule source. Record that the PluginTest placement and switching behavior was manually confirmed by the user, but do not generalize that observation into automated or cross-platform UI coverage. Never use filesystem timestamps as evidence time or imply live capture progress or direct access to undownloaded CI artifacts.
- Explain that `--workspace-root` permits an explicit consumer root while all project, scene, results, and budget inputs remain relative to it, with resolved symlink containment and generic-only external validation.
- Preserve the Windows containment contract: workspace membership is decided by filesystem identity so equivalent short and long path aliases such as `RUNNER~1` and `runneradmin` require no customer workaround. Calibration inputs and not-yet-created outputs must reuse the shared containment boundary while retaining traversal, unsafe-drive, and symlink-escape rejection. Distinguish a successful deterministic repository gate from complete repository-CI proof when an independent test job is still failing.
- Preserve the Linux reproduction boundary: Ubuntu 24.04 under WSL2 is verified only for a clean tracked export, Python 3.12.3 dependencies/tests, Godot 4.5.1 headless parsing and helpers, three portable captures, validation, calibration, and deterministic gates. Keep the exact official Linux archive checksum and copyable Judge reproduction commands synchronized with evidence. Do not generalize this into native Linux editor/GPU verification, macOS support, Linux hosted consumer CI, or portability of the PowerShell synthetic batch harness.
- Distinguish local independent-consumer proofs from hosted evidence. The verified hosted absolute-only ZIP proves three captures, three logs, both manifests/reports, and authoritative exit `0`; PluginTest PR #2 verifies paired hosting with three baseline plus three candidate captures/logs, two manifests, a canonical exit-1 report, and one accepted comparison investigation.
- Preserve the final-evaluation contract: Baseline 0 is the frozen validator from commit `22af3b44962517b0f1d7ac0b7499f724f2e2cb34`, the compared final product revision is `2bf5ff6efbedb44a8ac0370b686554a5a4ac4e40`, and both sides use the same ten-case manifest. Define a correct actionable outcome through its predefined status, numerical evidence, and safe detail oracle. Record unsupported baseline capabilities as unsupported rather than simulated failures. Keep the `1/10` versus `10/10` result, 90-percentage-point change, relative-only challenge, integrity manifest, and canonical result tied to tracked evidence. Integrity schema v2 hashes valid UTF-8 after canonical CRLF/lone-CR-to-LF normalization so Git checkout policy cannot invalidate equivalent text; every other content change must still fail integrity. State plainly that this measures deterministic workflow coverage, not game-speed improvement, ten independent games, GPU behavior, or AI reliability.
- Preserve the controlled-agent-evaluation contract separately from the API-free final evaluation. The frozen Experiment 19 package uses ten comparison-failure packets, the pinned `gpt-4.1-mini-2025-04-14` snapshot, matched prompts and safety/detail rules, alternating paired order, a 256/1,744 output-token split, zero retries, disabled tracing/storage, one packet-tool call per run, a `$2.00` aggregate ceiling, and one observed run per variant/case. Keep the observed `10/10` typed versus `0/10` free-form direct result, zero typed fallbacks, twenty agent runs, forty model requests, twenty tool calls, `$0.0237344` cost, latency statistics, rejected-text hashing, API-free `--verify`, and one-run nondeterminism limitation tied to `AGENT_EVALUATION.md` and the canonical result. Do not turn it into a general model ranking or imply AI has deterministic authority.
- Preserve the trajectory-navigation contract: `AGENT_TRAJECTORY.md` starts with judge navigation, canonical deterministic and controlled-agent outcome links, explicit shipped-investigator/build-time-agent/deterministic-tool authority boundaries, four representative trajectories, a Baseline 0-through-current-experiment milestone index, and a failure/correction index. Keep those links synchronized with stable explicit anchors and derive measurements from canonical evidence. Preserve the complete chronological audit below this layer; collapse long verbatim source requests for display only and never delete their content.
- Keep current-facing README and final-evaluation language free of obsolete video-deliverable requirements. Preserve older append-only trajectory and improvement-changelog statements as historical evidence rather than rewriting them.
- Do not call generated ignored JSON files a committed baseline or organized hackathon evidence package.

## Verification checklist

- Inspect `git remote -v` or equivalent and compare the README clone URL with the configured fetch URL. If a remote contains credentials or embedded authentication, omit those secrets and document a safe public URL or labeled placeholder instead.
- Inspect all README-linked targets with filesystem checks.
- Compare commands with the GDScript parser, PowerShell parameters, and Python CLI.
- Confirm cited result output against an existing result set or command log.
- Recalculate final-evaluation summaries from `evaluation/results/final-evaluation.json`, verify its hash-bound fixtures through `tools/run_submission_evaluation.py`, and compare its documented revisions with `evaluation/cases.json` and `evaluation/integrity.json`.
- Re-grade the controlled agent result through `tools/run_agent_evaluation.py --verify`, compare documentation numbers with `evaluation/agent/results/agent-evaluation.json`, and confirm rejected report text is absent before publishing Experiment 19 claims.
- Confirm planned artifacts are labeled and not linked as existing files.
- Check Markdown and diffs for malformed links, whitespace errors, machine-specific private paths, and accidental unsupported claims.
- Update `AGENT_TRAJECTORY.md` with the verification performed and any remaining gaps.

## Improvement changelog contract

Treat `IMPROVEMENT_CHANGELOG.md` as the product-evolution record, distinct from the agent's execution history.

- Begin with the user-designated baseline. Do not reconstruct earlier work when the user has declared the current state to be the starting baseline.
- Keep entries chronological and append-only. Never delete a failed, reverted, or removed experiment; record why it was removed and what it taught.
- Give every meaningful experiment its own entry containing the hypothesis or intended improvement, why it was tried, what changed, the evaluation method, the observed result, the decision, and the next step.
- Use the same scenarios, seed, warmup, samples, repetitions, validator, hardware, and configuration as the baseline whenever possible. Call out deviations before comparing results.
- Copy measurements only from saved results or recorded command output. Label unavailable evidence and do not infer missing values.
- Documentation-only edits are trajectory events, not product experiments. When no post-baseline experiment exists, state that plainly instead of inventing a journey or final result.
- Keep README's repository tree, evidence links, and current-status language synchronized with the changelog's existence and maturity.

On every skill invocation, inspect the changelog even when no new experiment is expected. Leave existing entries unchanged when repository evidence has not changed.
