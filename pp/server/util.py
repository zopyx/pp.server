"""System utilities for command execution and environment inspection.

Provides async subprocess execution via ``asyncio.create_subprocess_exec``
(no shell interpretation), PATH-based binary detection, environment variable
validation, and shell-injection-safe option sanitization.
"""

import asyncio
import os
import re
import shlex
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pp.server.logger import LOG

win32 = sys.platform == "win32"

# Allow only safe characters in command options
_SAFE_CMD_OPTIONS_RE = re.compile(r"^[a-zA-Z0-9\s\.\,\-\_\+\=\:\/\\@\(\)\[\]\"]*$")

# Default environment allowlist — only these vars are passed to subprocesses
_DEFAULT_ENV_ALLOWLIST = {
    "PATH",
    "HOME",
    "USER",
    "LANG",
    "LC_ALL",
    "TMPDIR",
    "TEMP",
    "TMP",
}

# Default conversion timeout in seconds
_DEFAULT_TIMEOUT = 300


def sanitize_cmd_options(options: str) -> str:
    """Validate and sanitize converter command-line options.

    Strips whitespace-only inputs, replaces control characters (newline,
    carriage return, tab) with spaces, and rejects any options containing
    shell-dangerous characters (semicolons, pipes, backticks, etc.).

    Args:
        options: Raw command-line option string from the API request.

    Returns:
        Sanitized option string safe for shell interpolation / shlex parsing.

    Raises:
        ValueError: If options contain characters that could enable
            shell injection.
    """
    if not options or options.strip() == " ":
        return ""
    # Replace newlines/tabs which could be used for injection
    cleaned = options.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    if not _SAFE_CMD_OPTIONS_RE.match(cleaned):
        raise ValueError(f"cmd_options contains unsafe characters: {options!r}")
    return cleaned


def parse_cmd_options(options: str) -> list[str]:
    """Parse sanitized command options into an argv list.

    First sanitizes via :func:`sanitize_cmd_options`, then splits using
    POSIX shell lexing rules (:func:`shlex.split`).

    Args:
        options: Raw command-line option string from the API request.

    Returns:
        List of individual option tokens.

    Raises:
        ValueError: If options contain unsafe characters.
    """
    safe = sanitize_cmd_options(options)
    if not safe:
        return []
    return shlex.split(safe)


def check_environment(envname: str) -> bool:
    """Check if an environment variable is set and points to an existing directory.

    Args:
        envname: Name of the environment variable to check.

    Returns:
        True if the variable is set and references a valid directory.
    """
    dirname = os.environ.get(envname)
    if dirname is None:
        LOG.debug(f"Environment variable ${envname} is unset")
        return False

    path = Path(dirname)
    if not path.exists():
        LOG.debug(
            f"The directory referenced through the environment "
            f"variable ${envname} does not exist ({dirname})"
        )
        return False
    return True


def which(command: str) -> bool:
    """Check if a command is available in the system PATH.

    Similar to the UNIX ``which`` command, but returns a boolean.

    Args:
        command: Name of the executable to locate (e.g. ``prince``).

    Returns:
        True if the command exists in at least one PATH directory.
    """
    path_env = os.environ.get("PATH", "")
    for path_str in path_env.split(":"):
        fullname = Path(path_str) / command
        if fullname.exists():
            return True
    return False


def _build_subprocess_env(
    extra_vars: Mapping[str, str] | None = None,
    allowlist: set[str] | None = None,
) -> dict[str, str]:
    """Build a minimal environment dict for subprocess execution.

    Only variables in *allowlist* (plus any *extra_vars*) are passed.
    This prevents leaking sensitive env vars (API keys, secrets) to
    untrusted converter processes.

    Args:
        extra_vars: Additional env vars to include (e.g. PDFreactor flags).
        allowlist: Set of env var names to permit. Defaults to
            ``_DEFAULT_ENV_ALLOWLIST``.

    Returns:
        Minimal environment dictionary.
    """
    allowed = allowlist or _DEFAULT_ENV_ALLOWLIST
    env = {}
    for key in allowed:
        val = os.environ.get(key)
        if val is not None:
            env[key] = val
    if extra_vars:
        env.update(extra_vars)
    return env


async def run(
    cmd: list[str],
    *,
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
    extra_env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Run a command as an argv list (no shell) and capture its output.

    Uses ``asyncio.create_subprocess_exec`` — no shell interpretation,
    so shell metacharacters in arguments have no execution semantics.

    Args:
        cmd: Command and arguments as a list (e.g. ``["prince", "-v",
            "input.html", "-o", "out.pdf"]``).
        cwd: Working directory for the subprocess.
        env: Full environment dict. If omitted, a minimal environment
            is built via :func:`_build_subprocess_env` with any
            *extra_env* merged in.
        timeout: Max seconds to wait for completion. ``None`` means
            no timeout (see ``_DEFAULT_TIMEOUT`` for the effective
            default in production).
        extra_env: Additional environment variables to merge into the
            default minimal environment (ignored if *env* is explicit).

    Returns:
        Dictionary with keys ``stdout``, ``stderr`` (decoded strings),
        and ``status`` (exit code or ``None`` if terminated by signal).

    Raises:
        asyncio.TimeoutError: If the command exceeds *timeout* seconds.
        ValueError: If *cmd* is empty.
    """
    if not cmd:
        msg = "cmd list must not be empty"
        raise ValueError(msg)

    resolved_env: dict[str, str] | None = env
    if resolved_env is None:
        resolved_env = _build_subprocess_env(extra_vars=extra_env)

    timeout_s = timeout if timeout is not None else _DEFAULT_TIMEOUT
    cmd_preview = " ".join(str(c) for c in cmd)
    LOG.info(f"CMD: {cmd_preview}  (cwd={cwd}, timeout={timeout_s}s)")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(cwd) if cwd else None,
        env=resolved_env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout_s
        )
    except TimeoutError:
        LOG.warning(f"Command timed out after {timeout_s}s: {cmd_preview}")
        # Try graceful terminate, then escalate to kill
        try:
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=5)
        except TimeoutError:
            proc.kill()
            await proc.wait()
        raise TimeoutError(f"Command timed out after {timeout_s}s") from None

    stdout = stdout_bytes.decode(errors="replace")
    stderr = stderr_bytes.decode(errors="replace")
    status: int | None = proc.returncode

    if stdout:
        LOG.info(f"Output:\n{stdout}")
    if stderr:
        LOG.info(f"Output:\n{stderr}")

    return dict(stdout=stdout, stderr=stderr, status=status)
