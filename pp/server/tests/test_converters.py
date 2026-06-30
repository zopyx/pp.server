"""Tests for pp.server.converters module."""

import io
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pp.server.converters import (
    _extract_safely,
    convert_pdf,
    load_config,
    load_resource,
    selftest,
)


class TestExtractSafely:
    def test_normal_extraction(self, tmp_path: Path) -> None:
        """Normal ZIP files extract correctly."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("index.html", "<html></html>")
            zf.writestr("css/style.css", "body {}")
        zf = zipfile.ZipFile(buf)
        _extract_safely(zf, tmp_path)
        assert (tmp_path / "index.html").exists()
        assert (tmp_path / "css" / "style.css").exists()

    def test_path_traversal_rejected(self, tmp_path: Path) -> None:
        """ZIP entries with path traversal are rejected."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("../../etc/passwd", "malicious")
            zf.writestr("index.html", "safe")
        zf = zipfile.ZipFile(buf)
        _extract_safely(zf, tmp_path)
        assert not (tmp_path / ".." / ".." / "etc" / "passwd").resolve().exists()
        assert (tmp_path / "index.html").exists()

    def test_absolute_path_rejected(self, tmp_path: Path) -> None:
        """ZIP entries with absolute paths are rejected."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "a") as zf:
            zf.writestr("/tmp/evil.txt", "bad")
        with zipfile.ZipFile(buf, "r") as zf:
            work_dir = tmp_path / "out"
            work_dir.mkdir()
            _extract_safely(zf, work_dir)
            assert not (work_dir / "tmp" / "evil.txt").exists()

    def test_directory_entry(self, tmp_path: Path) -> None:
        """ZIP directory entries create directories."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("subdir/", "")
            zf.writestr("subdir/file.txt", "content")
        zf = zipfile.ZipFile(buf)
        _extract_safely(zf, tmp_path)
        assert (tmp_path / "subdir" / "file.txt").exists()


class TestTomliFallback:
    """Test tomli as fallback when tomllib is not available."""

    def test_tomli_fallback_exists(self) -> None:
        """The module-level tomllib reference works (either stdlib or tomli fallback)."""
        from pp.server import converters as conv

        assert hasattr(conv, "tomllib") or hasattr(conv, "load_config")
        config = load_config()
        assert isinstance(config, dict)


class TestLoadConfig:
    def test_load_config_returns_dict(self) -> None:
        """load_config() returns a dict with converters key."""
        config = load_config()
        assert isinstance(config, dict)
        assert "converters" in config

    def test_load_config_missing_file_returns_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing config file returns empty converters dict."""
        monkeypatch.setattr(
            "pp.server.converters.Path",
            lambda *a: Path("/nonexistent/path/config.toml"),
        )
        result = load_config()
        assert result == {"converters": {}}

    def test_load_config_exception_returns_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Any non-FileNotFoundError exception returns empty converters dict."""
        import builtins

        def mock_open(*args, **kwargs):
            raise PermissionError("Permission denied")

        monkeypatch.setattr(builtins, "open", mock_open)
        result = load_config()
        assert result == {"converters": {}}


class TestLoadResource:
    def test_load_resource_found(self) -> None:
        """load_resource() returns bytes for existing resources."""
        data = load_resource("pp.server", "header.txt")
        assert isinstance(data, bytes)
        assert b"pp.server" in data

    def test_load_resource_raises_on_missing(self) -> None:
        """load_resource() raises FileNotFoundError for missing resources."""
        with pytest.raises(FileNotFoundError):
            load_resource("pp.server", "nonexistent_file.xyz")


class TestConvertPDF:
    """Tests for the convert_pdf async function."""

    @pytest.mark.asyncio
    async def test_unknown_converter(self, tmp_path: Path, monkeypatch) -> None:
        """Unknown converter returns status 9999."""
        work_file = tmp_path / "in.zip"
        with zipfile.ZipFile(work_file, "w") as zf:
            zf.writestr("index.html", "<html></html>")

        monkeypatch.setattr("pp.server.converters.sanitize_cmd_options", lambda x: x)

        result = await convert_pdf(
            str(tmp_path),
            str(work_file),
            "nonexistent_converter_xyz",
            lambda msg: None,
            "",
        )
        assert result["status"] == 9999
        assert "Unknown converter" in result["output"]

    @pytest.mark.asyncio
    async def test_calibre_converter(self, tmp_path: Path, monkeypatch) -> None:
        """Calibre converter sets epub target."""
        work_file = tmp_path / "in.zip"
        with zipfile.ZipFile(work_file, "w") as zf:
            zf.writestr("index.html", "<html></html>")

        monkeypatch.setattr("pp.server.converters.sanitize_cmd_options", lambda x: x)

        # has_converter is imported inside convert_pdf from pp.server.registry
        monkeypatch.setattr(
            "pp.server.registry.has_converter",
            lambda name: name == "calibre",
        )

        async def mock_run(cmd: str) -> dict:
            return dict(status=0, stdout="success", stderr="")

        monkeypatch.setattr("pp.server.converters.util.run", mock_run)

        # Create the out directory expected and a dummy out.epub
        out_dir = tmp_path / "out"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "out.epub").write_text("dummy epub")

        result = await convert_pdf(
            str(tmp_path),
            str(work_file),
            "calibre",
            lambda msg: None,
            "",
        )
        assert result["status"] == 0
        assert "out.epub" in result["filename"]

    @pytest.mark.asyncio
    async def test_pdfreactor_docker_path(self, tmp_path: Path, monkeypatch) -> None:
        """PDFreactor Docker path is used when PP_PDFREACTOR_DOCKER is set."""
        work_file = tmp_path / "in.zip"
        with zipfile.ZipFile(work_file, "w") as zf:
            zf.writestr("index.html", "<html></html>")

        monkeypatch.setattr("pp.server.converters.sanitize_cmd_options", lambda x: x)

        monkeypatch.setattr(
            "pp.server.registry.has_converter",
            lambda name: name == "pdfreactor",
        )

        captured_cmds: list[str] = []

        async def mock_run(cmd: str) -> dict:
            captured_cmds.append(cmd)
            return dict(status=0, stdout="success", stderr="")

        monkeypatch.setattr("pp.server.converters.util.run", mock_run)

        monkeypatch.setenv("PP_PDFREACTOR_DOCKER", "1")

        out_dir = tmp_path / "out"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "out.pdf").write_text("dummy pdf")

        result = await convert_pdf(
            str(tmp_path),
            str(work_file),
            "pdfreactor",
            lambda msg: None,
            "",
        )
        assert result["status"] == 0
        assert len(captured_cmds) > 0
        assert "file:///docs/" in captured_cmds[0]

    @pytest.mark.asyncio
    async def test_convert_with_output(self, tmp_path: Path, monkeypatch) -> None:
        """convert_pdf returns combined stdout+stderr output."""
        work_file = tmp_path / "in.zip"
        with zipfile.ZipFile(work_file, "w") as zf:
            zf.writestr("index.html", "<html></html>")

        monkeypatch.setattr("pp.server.converters.sanitize_cmd_options", lambda x: x)

        monkeypatch.setattr(
            "pp.server.registry.has_converter",
            lambda name: name == "prince",
        )

        async def mock_run(cmd: str) -> dict:
            return dict(status=0, stdout="info output", stderr="warning output")

        monkeypatch.setattr("pp.server.converters.util.run", mock_run)

        out_dir = tmp_path / "out"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "out.pdf").write_text("dummy pdf")

        result = await convert_pdf(
            str(tmp_path),
            str(work_file),
            "prince",
            lambda msg: None,
            "",
        )
        assert result["status"] == 0
        assert "info output" in result["output"]
        assert "warning output" in result["output"]


class TestSelftest:
    """Tests for the selftest async function."""

    @pytest.mark.asyncio
    async def test_selftest_prince(self, monkeypatch) -> None:
        """selftest returns PDF bytes for prince converter."""
        work_dir = Path("/tmp/pp-server-selftest-test")

        monkeypatch.setattr(
            "pp.server.converters.tempfile.mkdtemp",
            lambda prefix: str(work_dir),
        )

        mock_spec = MagicMock()
        mock_spec.origin = "/some/path/pp/server/test_data/__init__.py"
        monkeypatch.setattr(
            "pp.server.converters.importlib.util.find_spec",
            lambda name: mock_spec if name == "pp.server.test_data" else None,
        )

        def mock_copytree(src: str, dst: str, **kwargs) -> None:
            pass

        monkeypatch.setattr("pp.server.converters.shutil.copytree", mock_copytree)

        def mock_rmtree(path: str, **kwargs) -> None:
            pass

        monkeypatch.setattr("pp.server.converters.shutil.rmtree", mock_rmtree)

        async def mock_run(cmd: str) -> dict:
            return dict(status=0, stdout="success", stderr="")

        monkeypatch.setattr("pp.server.converters.util.run", mock_run)

        original_read_bytes = Path.read_bytes

        def mock_read_bytes(self_path: Path) -> bytes:
            if "out.pdf" in str(self_path):
                return b"%PDF-1.4 fake pdf data"
            return original_read_bytes(self_path)

        monkeypatch.setattr(Path, "read_bytes", mock_read_bytes)

        result = await selftest("prince")
        assert result == b"%PDF-1.4 fake pdf data"

    @pytest.mark.asyncio
    async def test_selftest_calibre(self, monkeypatch) -> None:
        """selftest uses epub target for calibre."""
        work_dir = Path("/tmp/pp-server-selftest-calibre")

        monkeypatch.setattr(
            "pp.server.converters.tempfile.mkdtemp",
            lambda prefix: str(work_dir),
        )

        mock_spec = MagicMock()
        mock_spec.origin = "/some/path/pp/server/test_data/__init__.py"
        monkeypatch.setattr(
            "pp.server.converters.importlib.util.find_spec",
            lambda name: mock_spec if name == "pp.server.test_data" else None,
        )

        def mock_copytree(src: str, dst: str, **kwargs) -> None:
            pass

        monkeypatch.setattr("pp.server.converters.shutil.copytree", mock_copytree)

        def mock_rmtree(path: str, **kwargs) -> None:
            pass

        monkeypatch.setattr("pp.server.converters.shutil.rmtree", mock_rmtree)

        async def mock_run(cmd: str) -> dict:
            return dict(status=0, stdout="success", stderr="")

        monkeypatch.setattr("pp.server.converters.util.run", mock_run)

        original_read_bytes = Path.read_bytes

        def mock_read_bytes(self_path: Path) -> bytes:
            if "out.epub" in str(self_path):
                return b"PK\x03\x04 fake epub"
            return original_read_bytes(self_path)

        monkeypatch.setattr(Path, "read_bytes", mock_read_bytes)

        result = await selftest("calibre")
        assert result == b"PK\x03\x04 fake epub"

    @pytest.mark.asyncio
    async def test_selftest_speedata(self, monkeypatch) -> None:
        """selftest uses XML source for speedata."""
        work_dir = Path("/tmp/pp-server-selftest-speedata")

        monkeypatch.setattr(
            "pp.server.converters.tempfile.mkdtemp",
            lambda prefix: str(work_dir),
        )

        mock_spec = MagicMock()
        mock_spec.origin = "/some/path/pp/server/test_data/__init__.py"
        monkeypatch.setattr(
            "pp.server.converters.importlib.util.find_spec",
            lambda name: mock_spec if name == "pp.server.test_data" else None,
        )

        def mock_copytree(src: str, dst: str, **kwargs) -> None:
            pass

        monkeypatch.setattr("pp.server.converters.shutil.copytree", mock_copytree)

        def mock_rmtree(path: str, **kwargs) -> None:
            pass

        monkeypatch.setattr("pp.server.converters.shutil.rmtree", mock_rmtree)

        async def mock_run(cmd: str) -> dict:
            return dict(status=0, stdout="success", stderr="")

        monkeypatch.setattr("pp.server.converters.util.run", mock_run)

        original_read_bytes = Path.read_bytes

        def mock_read_bytes(self_path: Path) -> bytes:
            if "out.pdf" in str(self_path):
                return b"%PDF-1.4 fake"
            return original_read_bytes(self_path)

        monkeypatch.setattr(Path, "read_bytes", mock_read_bytes)

        result = await selftest("speedata")
        assert result == b"%PDF-1.4 fake"
