"""pp.server — Produce & Publish Server.

Pydantic models for request/response schemas and structured error handling.
"""

from pydantic import BaseModel, Field


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


class ReadyResponse(BaseModel):
    """Readiness check response."""

    status: str
    spool_writable: bool


class ErrorDetail(BaseModel):
    """Single structured error detail."""

    code: str = Field(description="Stable error code for programmatic handling")
    message: str = Field(description="Human-readable error description")
    details: str | None = Field(None, description="Additional context or debug info")
    request_id: str | None = Field(None, description="Correlation ID for the request")
    job_id: str | None = Field(None, description="Conversion job ID if applicable")


class ErrorResponse(BaseModel):
    """Standard error response body."""

    detail: ErrorDetail
