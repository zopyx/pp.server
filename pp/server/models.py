"""pp.server — Produce & Publish Server.

Conversion REST API for HTML/XML to PDF using external PrintCSS converters.
"""

from pydantic import BaseModel


class ConvertResponse(BaseModel):
    """Response from the /convert endpoint."""

    status: str  # "OK" or "ERROR"
    data: str | None = None  # base64-encoded PDF (only on success)
    output: str = ""


class VersionResponse(BaseModel):
    """Server version info."""

    version: str
    module: str = "pp.server"


class ConvertersResponse(BaseModel):
    """List of available converters."""

    converters: list[str]


class ConverterDetailResponse(BaseModel):
    """Availability of a single converter."""

    has_converter: bool
    converter: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str


class CleanupResponse(BaseModel):
    """Cleanup operation result."""

    status: str = "OK"
