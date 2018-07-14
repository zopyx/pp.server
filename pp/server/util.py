################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX,  Tuebingen, Germany
################################################################

import os
import sys
import easyprocess
from pp.server.logger import LOG

win32 = sys.platform == "win32"


def runcmd(cmd):
    """ Execute a command using the easyprocess module """

    handle = easyprocess.EasyProcess(cmd)
    handle.call()
    stderr = handle.stderr
    stdout = handle.stdout
    status = handle.return_code

    if stdout:
        LOG.debug(stdout)
    if stderr:
        LOG.debug(stderr)
    return status, (stdout + stderr)


def checkEnvironment(envname):
    """ Check if the given name of an environment variable exists and
        if it points to an existing directory.
    """

    dirname = os.environ.get(envname)
    if dirname is None:
        LOG.debug("Environment variable ${} is unset".format(envname))
        return False

    if not os.path.exists(dirname):
        LOG.debug(
            "The directory referenced through the environment "
            "variable ${} does not exit ({})".format(envname, dirname)
        )
        return False
    return True


def which(command):
    """ Implements a functionality similar to the UNIX
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
