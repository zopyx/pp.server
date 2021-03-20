###############################################################
# pp.server - Produce & Publish Server
# (C) 2021, ZOPYX,  Tuebingen, Germany
################################################################

import os
import sys
import asyncio

from pp.server.logger import LOG

win32 = sys.platform == "win32"


def checkEnvironment(envname: str) -> bool:
    """Check if the given name of an environment variable exists and
    if it points to an existing directory.
    """

    dirname = os.environ.get(envname)
    if dirname is None:
        LOG.debug("Environment variable ${} is unset".format(envname))
        return False

    if not os.path.exists(dirname):
        LOG.debug("The directory referenced through the environment "
                  "variable ${} does not exit ({})".format(envname, dirname))
        return False
    return True


def which(command: str) -> bool:
    """Implements a functionality similar to the UNIX
    ``which`` command. The method checks if ``command``
    is available somewhere within the $PATH and returns
    True or False.
    """
    path_env = os.environ.get("PATH", "")  # also on win32?
    for path in path_env.split(":"):
        fullname = os.path.join(path, command)
        if os.path.exists(fullname):
            return True
    return False


async def run(cmd):
    """Run `cmd` asnychronously.
    Returns: dict(status, stdout, stderr)
    """

    LOG.info(cmd)
    proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    stdout = stdout.decode()
    stderr = stderr.decode()
    status = proc.returncode

    if stdout:
        LOG.info(f"Output:\n{stdout}")
    if stderr:
        LOG.info(f"Output:\n{stderr}")

    return dict(stdout=stdout, stderr=stderr, status=status)
