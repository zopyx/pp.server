################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX,  Tuebingen, Germany
################################################################

import os
from pp.server import util


def test_which():
    assert util.which('vim') 
    assert not util.which('unknown')

