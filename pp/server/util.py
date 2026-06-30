"""System utilities for command execution and environment inspection.

Provides shell command execution (async), PATH-based binary detection,
environment variable validation, and shell-injection-safe option sanitization.
"""

import asyncio
import os
import re
import sys
from pathlib import Path

from pp.server.logger import LOG

win32 = sys.platform == "win32"

# Allow only safe characters in command options
_SAFE_CMD_OPTIONS_RE = re.compile(r"^[a-zA-Z0-9\s\.\,\-\_\+\=\:\/\\@\(\)\[\]\"]*$")


def sanitize_cmd_options(options: str) -> str:
    """Validate and sanitize converter command-line options.

    Strips whitespace-only inputs, replaces control characters (newline,
    carriage return, tab) with spaces, and rejects any options containing
    shell-dangerous characters (semicolons, pipes, backticks, etc.).

    Args:
        options: Raw command-line option string from the API request.

    Returns:
        Sanitized option string safe for shell interpolation.

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
            f"variable ${envname} does not exit ({dirname})"
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
    path_env = os.environ.get("PATH", "")  # also on win32?
    for path_str in path_env.split(":"):
        fullname = Path(path_str) / command
        if fullname.exists():
            return True
    return False


async def run(cmd: str) -> dict[str, str | int | None]:
    """Run a shell command asynchronously and capture its output.

    Uses ``asyncio.create_subprocess_shell`` — the command string is
    interpreted by the system shell. For user-supplied input, ensure
    options are sanitized via :func:`sanitize_cmd_options` first.

    Args:
        cmd: Shell command string to execute.

    Returns:
        Dictionary with keys ``stdout``, ``stderr`` (decoded strings),
        and ``status`` (exit code or ``None`` if the process was
        terminated by a signal).
    """
    LOG.info(cmd)
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout_bytes, stderr_bytes = await proc.communicate()
    stdout = stdout_bytes.decode(errors="replace")
    stderr = stderr_bytes.decode(errors="replace")
    status: int | None = proc.returncode

    if stdout:
        LOG.info(f"Output:\n{stdout}")
    if stderr:
        LOG.info(f"Output:\n{stderr}")

    return dict(stdout=stdout, stderr=stderr, status=status)
