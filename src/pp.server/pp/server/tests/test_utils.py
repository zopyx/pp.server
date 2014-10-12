################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX,  Tuebingen, Germany
################################################################

import os
from pp.server import util


def test_which():
    assert util.which('vim') 
    assert not util.which('unknown')

def test_checkEnvironmentNonExisting():
    assert not util.checkEnvironment('FOO') 

def test_checkEnvironmentNonExistingDirectory():
    os.environ['FOO'] = '/foo'
    assert not util.checkEnvironment('FOO') 

def test_checkEnvironmentExistingDirectory():
    os.environ['FOO'] = os.getcwd()
    assert util.checkEnvironment('FOO') 
