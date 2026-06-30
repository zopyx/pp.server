"""Tests for pp.server.cli module."""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from pp.server.cli import main


def test_cli_defaults() -> None:
    """Test CLI with default options."""
    runner = CliRunner()
    with patch("pp.server.cli.uvicorn.run") as mock_run:
        result = runner.invoke(main, [])
    assert result.exit_code == 0
    mock_run.assert_called_once_with(
        "pp.server.server:app",
        host="127.0.0.1",
        port=8080,
        reload=False,
    )


def test_cli_custom_host_port() -> None:
    """Test CLI with custom host and port."""
    runner = CliRunner()
    with patch("pp.server.cli.uvicorn.run") as mock_run:
        result = runner.invoke(main, ["--host", "0.0.0.0", "--port", "9090"])
    assert result.exit_code == 0
    mock_run.assert_called_once_with(
        "pp.server.server:app",
        host="0.0.0.0",
        port=9090,
        reload=False,
    )


def test_cli_bind_host_port() -> None:
    """Test CLI with --bind option (host:port format)."""
    runner = CliRunner()
    with patch("pp.server.cli.uvicorn.run") as mock_run:
        result = runner.invoke(main, ["--bind", "0.0.0.0:9090"])
    assert result.exit_code == 0
    mock_run.assert_called_once_with(
        "pp.server.server:app",
        host="0.0.0.0",
        port=9090,
        reload=False,
    )


def test_cli_bind_host_only() -> None:
    """Test CLI with --bind option (host only, no port)."""
    runner = CliRunner()
    with patch("pp.server.cli.uvicorn.run") as mock_run:
        result = runner.invoke(main, ["--bind", "192.168.1.1"])
    assert result.exit_code == 0
    mock_run.assert_called_once_with(
        "pp.server.server:app",
        host="192.168.1.1",
        port=8080,
        reload=False,
    )


def test_cli_reload_flag() -> None:
    """Test CLI with --reload flag enabled."""
    runner = CliRunner()
    with patch("pp.server.cli.uvicorn.run") as mock_run:
        result = runner.invoke(main, ["--reload"])
    assert result.exit_code == 0
    mock_run.assert_called_once_with(
        "pp.server.server:app",
        host="127.0.0.1",
        port=8080,
        reload=True,
    )


def test_cli_all_options() -> None:
    """Test CLI with all options combined."""
    runner = CliRunner()
    with patch("pp.server.cli.uvicorn.run") as mock_run:
        result = runner.invoke(
            main, ["--host", "0.0.0.0", "--port", "3000", "--reload"]
        )
    assert result.exit_code == 0
    mock_run.assert_called_once_with(
        "pp.server.server:app",
        host="0.0.0.0",
        port=3000,
        reload=True,
    )


def test_cli_bind_overrides_host_port() -> None:
    """Test CLI where --bind overrides --host and --port."""
    runner = CliRunner()
    with patch("pp.server.cli.uvicorn.run") as mock_run:
        result = runner.invoke(
            main,
            [
                "--host",
                "127.0.0.1",
                "--port",
                "8080",
                "--bind",
                "10.0.0.1:5000",
            ],
        )
    assert result.exit_code == 0
    mock_run.assert_called_once_with(
        "pp.server.server:app",
        host="10.0.0.1",
        port=5000,
        reload=False,
    )
