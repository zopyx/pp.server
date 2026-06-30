"""Tests for pp.server.util module."""

import os
import sys
from pathlib import Path

import pytest

from pp.server import util


def test_which_existing_command() -> None:
    """Test that which() finds existing commands."""
    assert util.which("ls") or util.which("dir")


def test_which_nonexistent_command() -> None:
    """Test that which() returns False for non-existent commands."""
    assert not util.which("this_command_does_not_exist_12345")


def test_check_environment_missing_var() -> None:
    """Test check_environment with missing environment variable."""
    assert not util.check_environment("THIS_VAR_DOES_NOT_EXIST")


def test_check_environment_existing_var(tmp_path: Path) -> None:
    """Test check_environment with existing env var pointing to existing directory."""
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()

    os.environ["TEST_PP_SERVER_DIR"] = str(test_dir)
    try:
        assert util.check_environment("TEST_PP_SERVER_DIR")
    finally:
        del os.environ["TEST_PP_SERVER_DIR"]


def test_check_environment_existing_var_nonexistent_path(tmp_path: Path) -> None:
    """Test check_environment with existing env var pointing to non-existent dir."""
    os.environ["TEST_PP_SERVER_DIR_NONEXIST"] = str(tmp_path / "nonexistent")
    try:
        assert not util.check_environment("TEST_PP_SERVER_DIR_NONEXIST")
    finally:
        del os.environ["TEST_PP_SERVER_DIR_NONEXIST"]


@pytest.mark.asyncio
async def test_run_with_stdout() -> None:
    """run() handles stdout from a command."""
    result = await util.run(["echo", "hello"])
    assert result["status"] == 0
    assert "hello" in str(result.get("stdout", ""))


@pytest.mark.asyncio
async def test_run_with_stderr() -> None:
    """run() handles stderr from a command."""
    result = await util.run(["sh", "-c", "echo stderr output >&2"])
    assert result["status"] == 0 or result["status"] is not None
    # stderr should contain the output
    combined = str(result.get("stdout", "") or "") + str(result.get("stderr", "") or "")
    assert "stderr" in combined


@pytest.mark.asyncio
async def test_run_empty_command_raises() -> None:
    """run() rejects empty argv lists."""
    with pytest.raises(ValueError, match="must not be empty"):
        await util.run([])


@pytest.mark.asyncio
async def test_run_timeout_terminates_process() -> None:
    """run() raises TimeoutError when a process exceeds the timeout."""
    with pytest.raises(TimeoutError):
        await util.run(
            [sys.executable, "-c", "import time; time.sleep(10)"],
            timeout=0.01,
        )


def test_build_subprocess_env_allowlist_and_extra(monkeypatch) -> None:
    """Subprocess env includes only allowlisted vars plus explicit extras."""
    monkeypatch.setenv("KEEP_THIS", "1")
    monkeypatch.setenv("DROP_THIS", "2")
    env = util._build_subprocess_env(
        extra_vars={"EXTRA": "3"},
        allowlist={"KEEP_THIS"},
    )
    assert env == {"KEEP_THIS": "1", "EXTRA": "3"}


class TestSanitizeCmdOptions:
    """Tests for the sanitize_cmd_options function."""

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert util.sanitize_cmd_options("") == ""

    def test_whitespace_only(self) -> None:
        """A single space is returned as-is (not stripped)."""
        assert util.sanitize_cmd_options(" ") == " "

    def test_normal_options(self) -> None:
        """Normal safe options pass through."""
        result = util.sanitize_cmd_options("--verbose --output=test.pdf")
        assert "--verbose --output=test.pdf" in result

    def test_newline_replaced(self) -> None:
        """Newlines are replaced with spaces."""
        result = util.sanitize_cmd_options("--verbose\n--debug")
        assert "\n" not in result
        assert "--verbose --debug" in result

    def test_tab_replaced(self) -> None:
        """Tabs are replaced with spaces."""
        result = util.sanitize_cmd_options("--verbose\t--debug")
        assert "\t" not in result
        assert "--verbose --debug" in result

    def test_carriage_return_replaced(self) -> None:
        """Carriage returns are replaced with spaces."""
        result = util.sanitize_cmd_options("--verbose\r--debug")
        assert "\r" not in result
        assert "--verbose --debug" in result

    def test_unsafe_characters_raise_error(self) -> None:
        """Unsafe shell characters raise ValueError."""
        with pytest.raises(ValueError, match="unsafe characters"):
            util.sanitize_cmd_options("--option; rm -rf /")

    def test_unsafe_pipe_raises_error(self) -> None:
        """Pipe character raises ValueError."""
        with pytest.raises(ValueError, match="unsafe characters"):
            util.sanitize_cmd_options("--option | cat")

    def test_unsafe_backtick_raises_error(self) -> None:
        """Backtick character raises ValueError."""
        with pytest.raises(ValueError, match="unsafe characters"):
            util.sanitize_cmd_options("--option `id`")

    def test_unsafe_dollar_raises_error(self) -> None:
        """Dollar sign raises ValueError."""
        with pytest.raises(ValueError, match="unsafe characters"):
            util.sanitize_cmd_options("--option $HOME")

    def test_double_dash_allowed(self) -> None:
        """Double dash is allowed."""
        result = util.sanitize_cmd_options("--option --value")
        assert result == "--option --value"

    def test_equals_and_colon_allowed(self) -> None:
        """Equals sign and colon are allowed."""
        result = util.sanitize_cmd_options("--option=value:2")
        assert result == "--option=value:2"

    def test_parentheses_allowed(self) -> None:
        """Parentheses in options are allowed."""
        result = util.sanitize_cmd_options("--page-size (A4)")
        assert "--page-size (A4)" in result

    def test_brackets_allowed(self) -> None:
        """Brackets in options are allowed."""
        result = util.sanitize_cmd_options("--set [value]")
        assert "--set [value]" in result

    def test_quotes_allowed(self) -> None:
        """Quotes in options are allowed."""
        result = util.sanitize_cmd_options('--format "pdf"')
        assert '--format "pdf"' in result
