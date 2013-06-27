
from pp.server import util


def test_which():
    assert util.which('vim') 
    assert not util.which('unknown')
