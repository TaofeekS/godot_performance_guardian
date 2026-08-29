"""Safe workspace-root and repository-relative path resolution helpers."""

from __future__ import annotations

from pathlib import Path


class WorkspacePathError(ValueError):
    """A workspace or repository-relative path is unsafe or invalid."""


def resolve_workspace_root(value: str | Path | None, default: Path) -> Path:
    """Resolve an explicit workspace root without including it in diagnostics."""

    candidate = default if value is None else Path(value)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise WorkspacePathError("workspace root does not exist") from error
    if not resolved.is_dir():
        raise WorkspacePathError("workspace root is not a directory")
    return resolved


def resolve_workspace_member(
    root: Path,
    value: str,
    *,
    label: str,
    expected: str | None = None,
    require_json: bool = False,
) -> tuple[Path, str]:
    """Resolve one relative member and reject traversal or symlink escapes."""

    if not isinstance(value, str) or not value.strip():
        raise WorkspacePathError(f"{label} path is required")
    supplied = Path(value)
    if supplied.is_absolute() or supplied.drive or supplied.anchor or ".." in supplied.parts:
        raise WorkspacePathError(f"{label} path must be workspace-relative")
    resolved = (root / supplied).resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as error:
        raise WorkspacePathError(f"{label} path must remain inside the workspace") from error

    if expected is not None and not resolved.exists():
        raise WorkspacePathError(f"{label} does not exist")
    if expected == "directory" and not resolved.is_dir():
        raise WorkspacePathError(f"{label} is not a directory")
    if expected == "file" and not resolved.is_file():
        raise WorkspacePathError(f"{label} is not a file")
    if require_json and resolved.suffix.lower() != ".json":
        raise WorkspacePathError(f"{label} must use the .json extension")
    return resolved, relative.as_posix()
