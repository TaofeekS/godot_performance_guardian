"""Read-only OpenAI agent for interpreting validated Godot benchmark results."""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable

from agents import Agent, ModelSettings, Runner, function_tool
from openai import RateLimitError


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = (REPOSITORY_ROOT / "tools" / "validate_results.py").resolve()
DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_TIMEOUT_SECONDS = 30.0
SAFE_API_METADATA = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

INVESTIGATOR_INSTRUCTIONS = """\
You are the Godot Performance Investigator, a read-only reasoning layer over a
deterministic benchmark validator. You have exactly one tool. You must call
validate_benchmark_results before forming any verdict, using the exact
repository-relative results directory supplied by the user.

Treat the tool result as the only verified benchmark evidence available to you.
A successful validator exit means only that the supplied result set passed the
validator's configured assertions. It does not prove that the project has no
performance problems. Never claim that a suspected cause is proven without
both source-code and benchmark evidence. Keep possible causes explicitly
hypothetical, do not invent measurements, and do not claim to have inspected
files that the tool did not expose.

Return a concise Markdown report using exactly these section headings:

## Validation status
## Verified facts
## Possible explanations
## Recommended next investigation
## Remaining uncertainty

If validation fails or the tool returns an error, explain that limitation and
recommend resolving it before interpreting performance. Never propose edits as
though they were already made. You cannot modify, delete, or overwrite files.
"""


def resolve_results_directory(results_directory: str) -> tuple[Path, str, int]:
    """Resolve and validate a repository-contained benchmark result directory."""

    if not isinstance(results_directory, str) or not results_directory.strip():
        raise ValueError("A repository-relative results directory is required.")

    supplied = Path(results_directory)
    if supplied.is_absolute() or supplied.drive or supplied.anchor:
        raise ValueError("The results directory must be repository-relative.")

    resolved = (REPOSITORY_ROOT / supplied).resolve()
    try:
        relative = resolved.relative_to(REPOSITORY_ROOT)
    except ValueError as error:
        raise ValueError("The results directory must remain inside the repository.") from error

    if not resolved.exists():
        raise FileNotFoundError("The results directory does not exist.")
    if not resolved.is_dir():
        raise NotADirectoryError("The results path is not a directory.")

    json_file_count = sum(1 for path in resolved.glob("*.json") if path.is_file())
    if json_file_count == 0:
        raise FileNotFoundError("The results directory contains no JSON result files.")

    return resolved, relative.as_posix(), json_file_count


def _sanitized_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    text = value.decode(errors="replace") if isinstance(value, bytes) else str(value)
    root_variants = {
        str(REPOSITORY_ROOT),
        str(REPOSITORY_ROOT).replace("\\", "/"),
    }
    for root in root_variants:
        text = text.replace(root, "<repository>")
    return text


def _safe_api_metadata(value: object) -> str | None:
    if not isinstance(value, str) or not SAFE_API_METADATA.fullmatch(value):
        return None
    return value


def _numeric_retry_after(error: RateLimitError) -> float | None:
    headers = error.response.headers
    for header, divisor in (("retry-after-ms", 1000.0), ("retry-after", 1.0)):
        value = headers.get(header)
        try:
            seconds = float(value) / divisor
        except (TypeError, ValueError):
            continue
        if math.isfinite(seconds) and seconds >= 0:
            return seconds
    return None


def format_rate_limit_error(error: RateLimitError) -> str:
    """Return actionable 429 diagnostics without exposing raw API content."""

    code = _safe_api_metadata(error.code)
    error_type = _safe_api_metadata(error.type)
    request_id = _safe_api_metadata(error.request_id)
    retry_after = _numeric_retry_after(error)

    details = ["HTTP 429"]
    if code:
        details.append(f"code={code}")
    if error_type:
        details.append(f"type={error_type}")
    if request_id:
        details.append(f"request_id={request_id}")
    if retry_after is not None:
        details.append(f"retry_after={retry_after:g}s")

    classification = {value.lower() for value in (code, error_type) if value}
    prefix = f"ERROR: OpenAI API rate limit ({'; '.join(details)}). "
    if "insufficient_quota" in classification:
        return prefix + (
            "The API project has no available quota. Check API billing, credits, "
            "and project usage limits; retrying will not resolve this condition."
        )

    guidance = (
        "The request was throttled after the SDK's built-in retries. Check the "
        "API project's rate limits"
    )
    if retry_after is not None:
        guidance += f" and wait at least {retry_after:g} seconds before trying again"
    else:
        guidance += " before trying again"
    if any("model" in value.lower() for value in (code, error_type) if value):
        guidance += "; this limit appears model-specific, so verify OPENAI_MODEL access"
    return prefix + guidance + "."


def _evidence(
    *,
    validation_status: str,
    validator_invoked: bool,
    results_directory: str | None,
    json_file_count: int | None,
    exit_code: int | None,
    stdout: str = "",
    stderr: str = "",
    timed_out: bool = False,
    error_type: str | None = None,
) -> dict[str, Any]:
    return {
        "validation_status": validation_status,
        "validator_invoked": validator_invoked,
        "results_directory": results_directory,
        "json_file_count": json_file_count,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "timed_out": timed_out,
        "error_type": error_type,
    }


def run_validator(
    results_directory: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    *,
    subprocess_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    """Run the existing deterministic validator and return structured evidence."""

    try:
        _resolved, relative_directory, json_file_count = resolve_results_directory(
            results_directory
        )
    except (ValueError, FileNotFoundError, NotADirectoryError) as error:
        return _evidence(
            validation_status="error",
            validator_invoked=False,
            results_directory=None,
            json_file_count=None,
            exit_code=None,
            stderr=str(error),
            error_type="invalid_results_directory",
        )

    command = [sys.executable, str(VALIDATOR_PATH), relative_directory]
    try:
        completed = subprocess_runner(
            command,
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        return _evidence(
            validation_status="error",
            validator_invoked=True,
            results_directory=relative_directory,
            json_file_count=json_file_count,
            exit_code=None,
            stdout=_sanitized_text(error.stdout),
            stderr=_sanitized_text(error.stderr),
            timed_out=True,
            error_type="timeout",
        )
    except OSError:
        return _evidence(
            validation_status="error",
            validator_invoked=True,
            results_directory=relative_directory,
            json_file_count=json_file_count,
            exit_code=None,
            stderr="The validator process could not be started.",
            error_type="os_error",
        )

    return _evidence(
        validation_status="passed" if completed.returncode == 0 else "failed",
        validator_invoked=True,
        results_directory=relative_directory,
        json_file_count=json_file_count,
        exit_code=completed.returncode,
        stdout=_sanitized_text(completed.stdout),
        stderr=_sanitized_text(completed.stderr),
    )


@function_tool(
    name_override="validate_benchmark_results",
    description_override=(
        "Run the repository's deterministic benchmark validator against a "
        "repository-relative results directory and return structured evidence."
    ),
)
def validate_benchmark_results(results_directory: str) -> dict[str, Any]:
    """Validate stored benchmark results before forming an investigation verdict."""

    return run_validator(results_directory)


def build_investigator(model: str | None = None) -> Agent[None]:
    """Build the read-only investigator without making a network request."""

    selected_model = model or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
    return Agent(
        name="Godot Performance Investigator",
        instructions=INVESTIGATOR_INSTRUCTIONS,
        model=selected_model,
        tools=[validate_benchmark_results],
        model_settings=ModelSettings(
            tool_choice="required",
            parallel_tool_calls=False,
        ),
        tool_use_behavior="run_llm_again",
        reset_tool_choice=True,
    )


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Interpret existing Godot benchmark results without modifying them."
    )
    parser.add_argument(
        "results_directory",
        help="Repository-relative directory containing benchmark result JSON files",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _argument_parser().parse_args(argv)

    try:
        _resolved, relative_directory, _count = resolve_results_directory(
            args.results_directory
        )
    except (ValueError, FileNotFoundError, NotADirectoryError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not configured.", file=sys.stderr)
        return 2

    prompt = (
        "Investigate the stored Godot benchmark results in the repository-relative "
        f"directory {relative_directory!r}. Validate them before forming any verdict."
    )
    try:
        result = Runner.run_sync(build_investigator(), prompt)
    except RateLimitError as error:
        print(format_rate_limit_error(error), file=sys.stderr)
        return 1
    except Exception as error:  # The CLI must fail safely without exposing request details.
        print(f"ERROR: investigator run failed ({type(error).__name__}).", file=sys.stderr)
        return 1

    print(result.final_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
