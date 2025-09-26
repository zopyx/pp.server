###############################################################
# pp.server - Produce & Publish Server
# (C) 2021, ZOPYX,  Tuebingen, Germany
################################################################

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Union

from pp.server.logger import LOG

win32 = sys.platform == "win32"


def checkEnvironment(envname: str) -> bool:
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


async def run(cmd: str) -> Dict[str, Union[str, int]]:
    """Run `cmd` asnychronously.
    Returns: dict(status, stdout, stderr)
    """

    LOG.info(cmd)
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()

    stdout = stdout.decode()
    stderr = stderr.decode()
    status = proc.returncode

    if stdout:
        LOG.info(f"Output:\n{stdout}")
    if stderr:
        LOG.info(f"Output:\n{stderr}")

    return dict(stdout=stdout, stderr=stderr, status=status)
