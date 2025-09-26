################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX,  Tuebingen, Germany
################################################################

import pytest
from pathlib import Path
from pp.server import util


def test_which_existing_command():
    """Test that which() finds existing commands."""
    # Use 'ls' as it's available on most Unix systems
    assert util.which("ls") or util.which("dir")  # dir for Windows


def test_which_nonexistent_command():
    """Test that which() returns False for non-existent commands."""
    assert not util.which("this_command_does_not_exist_12345")


def test_check_environment_missing_var():
    """Test checkEnvironment with missing environment variable."""
    assert not util.checkEnvironment("THIS_VAR_DOES_NOT_EXIST")


def test_check_environment_existing_var(tmp_path: Path):
    """Test checkEnvironment with existing environment variable pointing to existing directory."""
    import os

    # Create a temporary directory and set environment variable
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()

    # Temporarily set environment variable
    os.environ["TEST_PP_SERVER_DIR"] = str(test_dir)

    try:
        assert util.checkEnvironment("TEST_PP_SERVER_DIR")
    finally:
        # Clean up
        del os.environ["TEST_PP_SERVER_DIR"]
