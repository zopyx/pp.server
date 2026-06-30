"""Tests for pp.server.templates module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from pp.server.templates import load_resource, main


class TestLoadResource:
    """Tests for load_resource()."""

    def test_load_resource_circusd_ini(self) -> None:
        """Test loading an existing circusd.ini resource."""
        data = load_resource("pp.server._templates", "circusd.ini")
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_load_resource_server_ini(self) -> None:
        """Test loading an existing server.ini resource."""
        data = load_resource("pp.server._templates", "server.ini")
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_load_resource_nonexistent(self) -> None:
        """Test loading a nonexistent resource raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_resource("pp.server._templates", "nonexistent.ini")


class TestMain:
    """Tests for main()."""

    def test_main_creates_config_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that main() generates circusd.ini and server.ini in CWD."""
        monkeypatch.chdir(tmp_path)

        main()

        circusd_ini = tmp_path / "circusd.ini"
        server_ini = tmp_path / "server.ini"

        assert circusd_ini.exists(), "circusd.ini was not created"
        assert server_ini.exists(), "server.ini was not created"

        circusd_content = circusd_ini.read_bytes()
        server_content = server_ini.read_bytes()

        assert len(circusd_content) > 0
        assert len(server_content) > 0

    def test_main_output_is_writable_binary(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that generated files contain valid binary content."""
        monkeypatch.chdir(tmp_path)

        main()

        circusd_ini = tmp_path / "circusd.ini"
        server_ini = tmp_path / "server.ini"

        circusd_content = circusd_ini.read_bytes()
        server_content = server_ini.read_bytes()

        assert isinstance(circusd_content, bytes)
        assert isinstance(server_content, bytes)

    def test_main_prints_filenames(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Test that main() prints the generated filenames."""
        monkeypatch.chdir(tmp_path)

        main()

        captured = capsys.readouterr()
        assert "circusd.ini" in captured.out
        assert "server.ini" in captured.out
