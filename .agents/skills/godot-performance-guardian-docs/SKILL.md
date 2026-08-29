---
name: godot-performance-guardian-docs
description: Maintain the Godot Performance Budget Guardian README, agent trajectory, and improvement changelog from verified repository evidence. Use only for documentation work in this repository; do not use for implementing benchmark, plugin, agent, or repair features.
---

# Godot Performance Guardian Documentation

Document the repository as it exists. Inspect the complete workspace, relevant GDScript, project configuration, harness, validator, generated evidence, Git state, and locally available tool versions before editing claims or commands.

On every invocation, inspect `README.md`, `AGENT_TRAJECTORY.md`, and `IMPROVEMENT_CHANGELOG.md` together with the implementation and available evidence. Read [references/readme-requirements.md](references/readme-requirements.md) completely before changing any of the three documents.

## Evidence rules

- Classify capabilities as implemented, partial, planned, missing, or unverified from workspace evidence. Never present roadmap intent as current behavior.
- Verify paths, arguments, schemas, thresholds, versions, platform support, Git remotes, and test output at their sources. Inspect `git remote -v` or equivalent before documenting clone commands. Use the configured fetch URL when present and an explicitly labeled placeholder only when no remote exists. Never publish credentials or embedded authentication from a remote URL.
- For consumer CI claims, inspect the reusable workflow, capture helper, workspace-root boundaries, pinned action revisions, artifact paths, and actual local/hosted verification separately. Never imply that copying the addon alone enables CI.
- Distinguish deterministic workload configuration from noisy performance measurements. Do not generalize one machine's numbers into portable claims.
- Treat embedded validator assertions as the current budget mechanism unless a configurable budget schema actually exists.
- Reuse trustworthy existing results and command logs. Do not rerun costly benchmarks solely to make documentation appear complete.
- Keep unrelated private source code, private assets, proprietary telemetry, credentials, private filesystem paths, and identifying information out of repository documentation.

## Deliverables

Review all three evidence documents on every invocation. Update a document only when the current task or repository evidence justifies a change; never create artificial churn merely to touch every file.

Maintain `README.md` for a developer encountering the project for the first time. Keep commands copyable, links relative, examples schema-accurate, limitations direct, and planned work clearly separated. Synchronize its status, repository tree, and evidence links when either companion document changes.

Maintain `AGENT_TRAJECTORY.md` for the documentation task. Record the request, plan and approval, user corrections, inspections, substantive commands, edits, failures or operational issues, verification evidence, final result, and unresolved gaps. Quote the original request when available, distinguish facts from interpretation, and never manufacture missing history.

Maintain `IMPROVEMENT_CHANGELOG.md` as the append-only product experiment record. Create the accepted current-state baseline when the file is absent. Append an experiment only when evidence shows a meaningful product or evaluation change; documentation-only work belongs in the trajectory. Preserve failed, reverted, and removed experiments with their results and lessons. If no experiment occurred, verify the changelog and leave its experiment history unchanged.

After editing, validate the skill itself, check all three documents and their Markdown references against the workspace, confirm commands and measurements against their sources, and run non-mutating formatting or syntax checks. Report what was verified and what remains unverified.
