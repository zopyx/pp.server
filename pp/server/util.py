################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX,  Tuebingen, Germany
################################################################

import os
import sys
import tempfile
from subprocess import Popen, PIPE
from pp.server.logger import LOG

win32 = (sys.platform=='win32')

def runcmd(cmd):                
    """ Execute a command using the subprocess module """

    cmd = cmd.encode('utf8')
    LOG.info(cmd)
    if win32:
        cmd = cmd.replace('\\', '/')
        s = Popen(cmd, shell=False)
        s.wait()
        return 0, ''
    else:
        stdin = open('/dev/null')
        stdout = stderr = PIPE
        p = Popen(cmd, 
                  shell=True,
                  stdin=stdin,
                  stdout=stdout,
                  stderr=stderr,
                  )

        status = p.wait()
        stdout_ = p.stdout.read().strip()
        stderr_ = p.stderr.read().strip()

        if stdout_:
            LOG.info(stdout_)
        if stderr_:
            LOG.info(stderr_)
        return status, (stdout_ + stderr_).decode('utf-8')


def checkEnvironment(envname):
    """ Check if the given name of an environment variable exists and
        if it points to an existing directory.
    """

    dirname = os.environ.get(envname, None)
    if dirname is None:
        LOG.debug('Environment variable $%s is unset' % envname)
        return False

    if not os.path.exists(dirname):
        LOG.debug('The directory referenced through the environment '
                  'variable $%s does not exit (%s)' % 
                  (envname, dirname))
        return False
    return True


def which(command):
    """ Implements a functionality similar to the UNIX
        ``which`` command. The method checks if ``command``
        is available somewhere within the $PATH and returns
        True or False.
    """
    path_env = os.environ.get('PATH', '') # also on win32?
    for path in path_env.split(':'):
        fullname = os.path.join(path, command)
        if os.path.exists(fullname):
            return True
    return False
