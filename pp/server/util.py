###############################################################
# pp.server - Produce & Publish Server
# (C) 2021, ZOPYX,  Tuebingen, Germany
################################################################

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

    Raises ValueError if options contain shell-dangerous characters.
    Falls back to shlex.quote() for maximum safety.
    """
    if not options or options.strip() == " ":
        return ""
    # Replace newlines/tabs which could be used for injection
    cleaned = options.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    if not _SAFE_CMD_OPTIONS_RE.match(cleaned):
        raise ValueError(f"cmd_options contains unsafe characters: {options!r}")
    return cleaned


def check_environment(envname: str) -> bool:
    """Check if the given name of an environment variable exists and
    if it points to an existing directory.
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
    """Implements a functionality similar to the UNIX
    ``which`` command. The method checks if ``command``
    is available somewhere within the $PATH and returns
    True or False.
    """
    path_env = os.environ.get("PATH", "")  # also on win32?
    for path_str in path_env.split(":"):
        fullname = Path(path_str) / command
        if fullname.exists():
            return True
    return False


async def run(cmd: str) -> dict[str, str | int | None]:
    """Run `cmd` asynchronously.
    Returns: dict(status, stdout, stderr)
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
