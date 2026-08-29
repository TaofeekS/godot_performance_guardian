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
- Do not call generated ignored JSON files a committed baseline or organized hackathon evidence package.

## Verification checklist

- Inspect `git remote -v` or equivalent and compare the README clone URL with the configured fetch URL. If a remote contains credentials or embedded authentication, omit those secrets and document a safe public URL or labeled placeholder instead.
- Inspect all README-linked targets with filesystem checks.
- Compare commands with the GDScript parser, PowerShell parameters, and Python CLI.
- Confirm cited result output against an existing result set or command log.
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
