import base64
import os
import tempfile
import time
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from pp.server.server import (
    app,
    cleanup_queue,
    converter_log,
    new_converter_id,
)


def _zip_payload() -> str:
    """Return base64 ZIP payload containing a minimal index.html."""
    zip_path = Path(tempfile.mkstemp(suffix=".zip")[1])
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("index.html", "<html></html>")
    zip_data = zip_path.read_bytes()
    zip_path.unlink()
    return base64.encodebytes(zip_data).decode("ascii")


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestIndexEndpoint:
    def test_index(self, client: TestClient) -> None:
        result = client.get("/")
        assert result.status_code == 200
        assert "Produce &amp; Publish Server" in result.text
        assert "v4.0.0" in result.text

    def test_index_with_versions(self, client: TestClient, monkeypatch) -> None:
        """Index with show_versions=true calls converter_versions."""

        async def mock_converter_versions() -> dict[str, str]:
            return {"prince": "15.0"}

        monkeypatch.setattr(
            "pp.server.server.registry.converter_versions",
            mock_converter_versions,
        )

        result = client.get("/?show_versions=true")
        assert result.status_code == 200
        assert "Produce &amp; Publish Server" in result.text


class TestConvertersEndpoint:
    def test_converters_endpoint(self, client: TestClient) -> None:
        result = client.get("/converters")
        assert result.status_code == 200
        data = result.json()
        assert "converters" in data
        assert isinstance(data["converters"], list)


class TestConverterVersionsEndpoint:
    def test_converter_versions_endpoint(self, client: TestClient, monkeypatch) -> None:
        """Test the /converter-versions endpoint."""

        async def mock_converter_versions() -> dict[str, str]:
            return {"prince": "15.0", "weasyprint": "60.0"}

        monkeypatch.setattr(
            "pp.server.server.registry.converter_versions",
            mock_converter_versions,
        )

        result = client.get("/converter-versions")
        assert result.status_code == 200
        data = result.json()
        assert "converters" in data
        assert data["converters"] == {"prince": "15.0", "weasyprint": "60.0"}


class TestHasConverterEndpoint:
    def test_has_converter_missing(self, client: TestClient) -> None:
        result = client.get("/converter?converter_name=dummy")
        assert result.status_code == 200
        assert result.json() == {"has_converter": False, "converter": "dummy"}


class TestVersionEndpoint:
    def test_version_endpoint(self, client: TestClient) -> None:
        """Test the /version endpoint."""
        result = client.get("/version")
        assert result.status_code == 200
        data = result.json()
        assert "version" in data
        assert "module" in data
        assert data["module"] == "pp.server"


class TestHealthReadyMetricsEndpoints:
    def test_health_endpoint(self, client: TestClient) -> None:
        """Health endpoint returns lightweight process health."""
        result = client.get("/health")
        assert result.status_code == 200
        assert result.json()["status"] == "healthy"

    def test_ready_endpoint_ok(self, client: TestClient, monkeypatch) -> None:
        """Readiness returns 200 when the spool is writable."""
        monkeypatch.setattr("pp.server.server.os.access", lambda path, mode: True)
        result = client.get("/ready")
        assert result.status_code == 200
        assert result.json() == {"status": "ready", "spool_writable": True}

    def test_ready_endpoint_not_writable(self, client: TestClient, monkeypatch) -> None:
        """Readiness returns 503 when the spool is not writable."""
        monkeypatch.setattr("pp.server.server.os.access", lambda path, mode: False)
        result = client.get("/ready")
        assert result.status_code == 503
        assert result.json() == {"status": "not_ready", "spool_writable": False}

    def test_metrics_endpoint(self, client: TestClient) -> None:
        """Metrics endpoint exposes conversion counters."""
        result = client.get("/metrics")
        assert result.status_code == 200
        data = result.json()
        assert "conversions" in data
        assert "active_jobs" in data

    def test_openapi_documents_convert_error_responses(
        self, client: TestClient
    ) -> None:
        """OpenAPI includes the structured error response model for /convert."""
        schema = client.get("/openapi.json").json()
        responses = schema["paths"]["/convert"]["post"]["responses"]
        assert "ErrorResponse" in schema["components"]["schemas"]
        for status_code in ("400", "404", "413", "422", "500", "502", "504"):
            ref = responses[status_code]["content"]["application/json"]["schema"][
                "$ref"
            ]
            assert ref.endswith("/ErrorResponse")


class TestCleanupEndpoint:
    def test_cleanup_endpoint(self, client: TestClient, monkeypatch) -> None:
        """Test the /cleanup endpoint."""
        monkeypatch.setattr("pp.server.server.cleanup_queue", lambda: None)
        result = client.get("/cleanup")
        assert result.status_code == 200
        assert result.json() == {"status": "OK"}


class TestSelftestEndpoint:
    def test_selftest_unknown_converter(self, client: TestClient) -> None:
        """Unknown converter returns 404."""
        result = client.get("/selftest?converter=nonexistent_converter")
        assert result.status_code == 404

    def test_selftest_success(self, client: TestClient, monkeypatch) -> None:
        """Successful selftest returns PDF data."""
        monkeypatch.setattr(
            "pp.server.server.registry.available_converters",
            lambda: ["test_selftest_prince"],
        )

        async def mock_selftest(converter: str) -> bytes:
            return b"%PDF-1.4 selftest data"

        monkeypatch.setattr("pp.server.server.selftest", mock_selftest)

        result = client.get("/selftest?converter=test_selftest_prince")
        assert result.status_code == 200
        assert result.content == b"%PDF-1.4 selftest data"
        assert result.headers["content-type"] == "application/pdf"
        assert "selftest-test_selftest_prince.pdf" in result.headers.get(
            "content-disposition", ""
        )

    def test_selftest_calibre(self, client: TestClient, monkeypatch) -> None:
        """Calibre selftest returns epub data (converter name must be 'calibre')."""
        monkeypatch.setattr(
            "pp.server.server.registry.available_converters",
            lambda: ["calibre"],
        )

        async def mock_selftest(converter: str) -> bytes:
            return b"PK\x03\x04 epub data"

        monkeypatch.setattr("pp.server.server.selftest", mock_selftest)

        result = client.get("/selftest?converter=calibre")
        assert result.status_code == 200
        assert result.headers["content-type"] == "application/epub+zip"

    def test_selftest_filenotfound(self, client: TestClient, monkeypatch) -> None:
        """FileNotFoundError during selftest returns 500."""
        monkeypatch.setattr(
            "pp.server.server.registry.available_converters",
            lambda: ["test_selftest_bad"],
        )

        async def mock_selftest(converter: str) -> bytes:
            msg = "Missing file"
            raise FileNotFoundError(msg)

        monkeypatch.setattr("pp.server.server.selftest", mock_selftest)

        result = client.get("/selftest?converter=test_selftest_bad")
        assert result.status_code == 500
        assert "file not found" in result.json()["detail"]["message"].lower()

    def test_selftest_oserror(self, client: TestClient, monkeypatch) -> None:
        """OSError during selftest returns 500."""
        monkeypatch.setattr(
            "pp.server.server.registry.available_converters",
            lambda: ["test_selftest_os"],
        )

        async def mock_selftest(converter: str) -> bytes:
            msg = "OS error occurred"
            raise OSError(msg)

        monkeypatch.setattr("pp.server.server.selftest", mock_selftest)

        result = client.get("/selftest?converter=test_selftest_os")
        assert result.status_code == 500
        assert "OS error" in result.json()["detail"]["message"]

    def test_selftest_generic_exception(self, client: TestClient, monkeypatch) -> None:
        """Generic exception during selftest returns 500."""
        monkeypatch.setattr(
            "pp.server.server.registry.available_converters",
            lambda: ["test_selftest_exc"],
        )

        async def mock_selftest(converter: str) -> bytes:
            msg = "Something went wrong"
            raise RuntimeError(msg)

        monkeypatch.setattr("pp.server.server.selftest", mock_selftest)

        result = client.get("/selftest?converter=test_selftest_exc")
        assert result.status_code == 500
        assert (
            "Self-test for test_selftest_exc failed"
            in result.json()["detail"]["message"]
        )


class TestConvertEndpoint:
    @pytest.mark.parametrize("converter", ["prince", "weasyprint"])
    def test_convert_pdf(self, client: TestClient, converter: str) -> None:
        """Test PDF conversion for available converters."""
        # Check if converter is available first
        result = client.get(f"/converter?converter_name={converter}")
        if result.json()["has_converter"]:
            self._convert_pdf(client, converter)
        else:
            pytest.skip(f"Converter {converter} not available")

    def test_convert_pdf_unavailable_converter(self, client: TestClient) -> None:
        """Test PDF conversion with a converter that's not in PATH."""
        # Use a name that definitely won't be found
        index_html = Path(__file__).parent / "index.html"
        zip_path = Path(tempfile.mkstemp(suffix=".zip")[1])
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(index_html, "index.html")
        zip_data = zip_path.read_bytes()
        zip_path.unlink()

        params = dict(
            converter="this_converter_does_not_exist_12345",
            cmd_options=" ",
            data=base64.encodebytes(zip_data).decode("ascii"),
        )
        result = client.post("/convert", data=params)
        assert result.status_code == 404
        assert result.json()["detail"]["code"] == "converter_not_available"

    def test_convert_invalid_base64(self, client: TestClient, monkeypatch) -> None:
        """Invalid base64 returns a structured 400 with request ID."""
        monkeypatch.setattr(
            "pp.server.server.registry.available_converters",
            lambda: ["prince"],
        )
        result = client.post(
            "/convert",
            data={"converter": "prince", "cmd_options": " ", "data": "not valid %%%"},
        )
        assert result.status_code == 400
        body = result.json()["detail"]
        assert body["code"] == "invalid_base64"
        assert body["request_id"] == result.headers["x-request-id"]

    def test_convert_non_zip_payload(self, client: TestClient, monkeypatch) -> None:
        """Base64 non-ZIP payload returns 400 invalid_zip."""
        monkeypatch.setattr(
            "pp.server.server.registry.available_converters",
            lambda: ["prince"],
        )
        result = client.post(
            "/convert",
            data={
                "converter": "prince",
                "cmd_options": " ",
                "data": base64.b64encode(b"plain text").decode("ascii"),
            },
        )
        assert result.status_code == 400
        assert result.json()["detail"]["code"] == "invalid_zip"

    def test_convert_encoded_payload_too_large(
        self, client: TestClient, monkeypatch
    ) -> None:
        """Oversized encoded request bodies are rejected before decoding."""
        monkeypatch.setattr(
            "pp.server.server.registry.available_converters",
            lambda: ["prince"],
        )
        monkeypatch.setenv("PP_MAX_ENCODED_REQUEST_SIZE", "3")
        result = client.post(
            "/convert",
            data={"converter": "prince", "cmd_options": " ", "data": _zip_payload()},
        )
        assert result.status_code == 413
        assert result.json()["detail"]["code"] == "payload_too_large"

    def test_convert_corrupt_zip_payload(self, client: TestClient, monkeypatch) -> None:
        """Corrupt payloads with ZIP magic still return 400."""
        monkeypatch.setattr(
            "pp.server.server.registry.available_converters",
            lambda: ["prince"],
        )
        result = client.post(
            "/convert",
            data={
                "converter": "prince",
                "cmd_options": " ",
                "data": base64.b64encode(b"PK\x03\x04broken").decode("ascii"),
            },
        )
        assert result.status_code == 400
        assert result.json()["detail"]["code"] == "invalid_zip"

    def test_convert_unsafe_cmd_options(self, client: TestClient, monkeypatch) -> None:
        """Unsafe command options are rejected at the route layer."""
        monkeypatch.setattr(
            "pp.server.server.registry.available_converters",
            lambda: ["prince"],
        )
        result = client.post(
            "/convert",
            data={
                "converter": "prince",
                "cmd_options": "--debug; id",
                "data": _zip_payload(),
            },
        )
        assert result.status_code == 400
        assert result.json()["detail"]["code"] == "invalid_cmd_options"

    @pytest.mark.parametrize(
        ("status", "expected_http", "expected_code"),
        [
            (9997, 504, "conversion_timeout"),
            (9989, 413, "zip_limit_exceeded"),
            (9988, 400, "invalid_zip"),
            (1, 502, "conversion_failed"),
        ],
    )
    def test_convert_failure_status_mapping(
        self,
        client: TestClient,
        monkeypatch,
        status: int,
        expected_http: int,
        expected_code: str,
    ) -> None:
        """Conversion failures map to documented HTTP statuses."""
        monkeypatch.setattr(
            "pp.server.server.registry.available_converters",
            lambda: ["prince"],
        )

        async def mock_convert_pdf(*args, **kwargs):
            return {"status": status, "output": "failed", "filename": ""}

        monkeypatch.setattr("pp.server.server.convert_pdf", mock_convert_pdf)

        result = client.post(
            "/convert",
            data={"converter": "prince", "cmd_options": " ", "data": _zip_payload()},
        )
        assert result.status_code == expected_http
        assert result.json()["detail"]["code"] == expected_code

    def _convert_pdf(
        self, client: TestClient, converter: str, expected: str = "OK"
    ) -> None:
        # Generate ZIP file with sample data first
        index_html = Path(__file__).parent / "index.html"
        zip_path = Path(tempfile.mkstemp(suffix=".zip")[1])

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(index_html, "index.html")

        zip_data = zip_path.read_bytes()
        zip_path.unlink()

        params = dict(
            converter=converter,
            cmd_options=" ",
            data=base64.encodebytes(zip_data).decode("ascii"),
        )
        result = client.post("/convert", data=params)
        params = result.json()

        if expected == "OK":
            assert params["status"] == "OK"
            assert "output" in params
            pdf_data = base64.decodebytes(params["data"].encode("ascii"))
            assert pdf_data.startswith(b"%PDF-1.")
        else:
            assert params["status"] == "ERROR"
            assert "output" in params


class TestCleanupQueue:
    """Tests for the cleanup_queue function."""

    def test_cleanup_queue_too_soon(self, monkeypatch) -> None:
        """cleanup_queue returns None when called too soon after last cleanup."""
        monkeypatch.setattr("pp.server.server.LAST_CLEANUP", time.time())
        result = cleanup_queue()
        assert result is None

    def test_cleanup_queue_removes_old_dirs(self, tmp_path: Path, monkeypatch) -> None:
        """Old directories are removed during cleanup."""
        monkeypatch.setattr("pp.server.server.QUEUE_CLEANUP_TIME", 0)
        monkeypatch.setattr("pp.server.server.LAST_CLEANUP", 0)
        monkeypatch.setattr("pp.server.server.queue_dir", tmp_path)

        old_dir = tmp_path / "old_dir"
        old_dir.mkdir()
        old_time = time.time() - 100000
        os.utime(str(old_dir), (old_time, old_time))

        old_file = tmp_path / "old_file.txt"
        old_file.write_text("old data")
        os.utime(str(old_file), (old_time, old_time))

        result = cleanup_queue()
        assert result is not None
        assert result["directories_removed"] >= 1
        assert not old_dir.exists()
        assert not old_file.exists()

    def test_cleanup_queue_removes_old_files(self, tmp_path: Path, monkeypatch) -> None:
        """Old files are removed during cleanup."""
        monkeypatch.setattr("pp.server.server.QUEUE_CLEANUP_TIME", 0)
        monkeypatch.setattr("pp.server.server.LAST_CLEANUP", 0)
        monkeypatch.setattr("pp.server.server.queue_dir", tmp_path)

        old_file = tmp_path / "old_file.txt"
        old_file.write_text("old data")
        old_time = time.time() - 100000
        os.utime(str(old_file), (old_time, old_time))

        result = cleanup_queue()
        assert result is not None
        assert not old_file.exists()

    def test_cleanup_queue_tolerates_race_like_missing_path(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Cleanup continues if a path disappears between iteration and stat."""
        monkeypatch.setattr("pp.server.server.QUEUE_CLEANUP_TIME", 0)
        monkeypatch.setattr("pp.server.server.LAST_CLEANUP", 0)
        monkeypatch.setattr("pp.server.server.queue_dir", tmp_path)

        old_file = tmp_path / "old_file.txt"
        old_file.write_text("old data")

        original_stat = Path.stat

        def disappearing_stat(self_path: Path, *args, **kwargs):
            if self_path == old_file:
                old_file.unlink(missing_ok=True)
            return original_stat(self_path, *args, **kwargs)

        monkeypatch.setattr(Path, "stat", disappearing_stat)

        result = cleanup_queue()
        assert result is not None
        assert result["directories_removed"] == 0


class TestConverterLog:
    """Tests for the converter_log function."""

    def test_converter_log_normal(self, tmp_path: Path) -> None:
        """Normal logging writes to converter.log."""
        converter_log(str(tmp_path), "Test message")
        log_file = tmp_path / "converter.log"
        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content

    def test_converter_log_unicode_encode_error(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """UnicodeEncodeError is caught and handled."""
        log_file_path = tmp_path / "converter.log"
        calls: list[str] = []

        original_open = (
            __builtins__["open"]
            if isinstance(__builtins__, dict)
            else __builtins__.open
        )

        def mock_open_write(path, mode="r", **kwargs):
            if str(path) == str(log_file_path) and "a" in mode:
                mock_fp = MagicMock()
                call_count = [0]

                def write(data):
                    call_count[0] += 1
                    if call_count[0] == 1:
                        raise UnicodeEncodeError(
                            "ascii",
                            data,
                            0,
                            1,
                            "ordinal not in range",
                        )
                    calls.append(data)
                    return len(data)

                mock_fp.write = write
                mock_fp.__enter__ = MagicMock(return_value=mock_fp)
                mock_fp.__exit__ = MagicMock(return_value=None)
                return mock_fp
            return original_open(path, mode, **kwargs)

        monkeypatch.setattr("builtins.open", mock_open_write)

        # Should not raise despite UnicodeEncodeError on first write
        converter_log(str(tmp_path), "Test message")
        # Verify exception handler was triggered (data was written via fallback)
        assert len(calls) >= 1, "Fallback write should have succeeded"

    def test_converter_log_unicode_decode_error(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """UnicodeDecodeError is caught and handled."""
        log_file_path = tmp_path / "converter.log"
        calls: list[str] = []

        original_open = (
            __builtins__["open"]
            if isinstance(__builtins__, dict)
            else __builtins__.open
        )

        def mock_open_write(path, mode="r", **kwargs):
            if str(path) == str(log_file_path) and "a" in mode:
                mock_fp = MagicMock()
                call_count = [0]

                def write(data):
                    call_count[0] += 1
                    if call_count[0] == 1:
                        raise UnicodeDecodeError(
                            "ascii",
                            b"\xff",
                            0,
                            1,
                            "invalid start byte",
                        )
                    calls.append(data)
                    return len(data)

                mock_fp.write = write
                mock_fp.__enter__ = MagicMock(return_value=mock_fp)
                mock_fp.__exit__ = MagicMock(return_value=None)
                return mock_fp
            return original_open(path, mode, **kwargs)

        monkeypatch.setattr("builtins.open", mock_open_write)

        # Should not raise despite UnicodeDecodeError on first write
        converter_log(str(tmp_path), "Test message")


class TestNewConverterId:
    def test_new_converter_id_format(self) -> None:
        """new_converter_id creates properly formatted UUID-based IDs."""
        result = new_converter_id("prince")
        assert "-prince" in result
        parts = result.split("-")
        assert len(parts) >= 2
        # First part should be a valid 32-char hex UUID
        assert len(parts[0]) == 32
        int(parts[0], 16)  # raises ValueError if not hex
