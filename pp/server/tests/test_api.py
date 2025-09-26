################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX,  Tuebingen, Germany
################################################################

import os
import base64
import zipfile
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pp.server.server import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestPDFAPI:
    def test_index(self, client):
        result = client.get("/")
        assert result.status_code == 200
        assert "2021" in result.text

    def test_has_converter(self, client):
        result = client.get("/converter?converter_name=prince")
        assert result.status_code == 200
        body = result.json()
        assert body["has_converter"] == True

    def test_has_converter_missing(self, client):
        result = client.get("/converter?converter_name=dummy")
        assert result.status_code == 200
        assert result.json() == {"has_converter": False, "converter": "dummy"}

    @pytest.mark.parametrize("converter", ["prince", "weasyprint"])
    def test_convert_pdf(self, client, converter):
        """Test PDF conversion for available converters."""
        # Check if converter is available first
        result = client.get(f"/converter?converter_name={converter}")
        if result.json()["has_converter"]:
            self._convert_pdf(client, converter)
        else:
            pytest.skip(f"Converter {converter} not available")

    def test_convert_pdf_unavailable_converter(self, client):
        """Test PDF conversion with unavailable/unlicensed converter."""
        self._convert_pdf(client, "antennahouse", expected="ERROR")

    def _convert_pdf(self, client, converter, expected="OK"):
        # Generate ZIP file with sample data first
        index_html = Path(__file__).parent / "index.html"
        zip_path = Path(tempfile.mktemp(suffix=".zip"))

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.write(index_html, "index.html")

        zip_data = zip_path.read_bytes()
        zip_path.unlink()

        params = dict(
            converter=converter, cmd_options=" ", data=base64.encodebytes(zip_data).decode('ascii')
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
