"""FastAPI application and HTTP route handlers.

The main entry point for the Produce & Publish Server. Defines the
FastAPI application, all REST API endpoints, and internal helper
functions for queue management and conversion logging.

Module-level bootstrap:
    1. Registers all available converters (via ``registry._register_converters``)
    2. Creates the FastAPI app, mounts static files, and configures Jinja2
    3. Initializes the spool directory from ``PP_SPOOL_DIRECTORY`` (or default)
"""

import base64
import binascii
import datetime
import io
import os
import shutil
import sys
import time
import uuid
import zipfile
from collections import defaultdict
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pp.server import registry
from pp.server.converters import convert_pdf, selftest
from pp.server.logger import LOG
from pp.server.models import (
    ConverterDetailResponse,
    ConvertersResponse,
    ConvertResponse,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    ReadyResponse,
    VersionResponse,
)

# ---------------------------------------------------------------------------
# Configuration defaults (overridable via environment variables)
# ---------------------------------------------------------------------------
# How often to cleanup the queue directory?
QUEUE_CLEANUP_TIME = int(
    os.environ.get("PP_QUEUE_CLEANUP_INTERVAL", str(24 * 60 * 60))
)  # 1 day

# Internal timestamp for the last cleanup action
LAST_CLEANUP = time.time() - 3600 * 24 * 10

# Bootstrap: register all converters
registry._register_converters()

# Bootstrap: FastAPI App
app = FastAPI(
    title="Produce & Publish Server",
    description="This server provides a REST interface for most common PrintCSS converters",
)

# Bootstrap: register resources for HTML view
dirname = Path(__file__).parent
static_dir = dirname / "static"
templates_dir = dirname / "templates"
templates = Jinja2Templates(directory=templates_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Bootstrap: spool directory
queue_dir = Path.cwd() / "var" / "queue"
queue_dir = Path(os.environ.get("PP_SPOOL_DIRECTORY", str(queue_dir)))
queue_dir.mkdir(parents=True, exist_ok=True)

VERSION = _pkg_version("pp.server")
LOG.info(f"QUEUE: {queue_dir}")
LOG.info(f"pp.server V {VERSION}")

# ---------------------------------------------------------------------------
# Active job registry (in-memory set for cleanup safety)
# ---------------------------------------------------------------------------
_active_jobs: set[str] = set()

# ---------------------------------------------------------------------------
# Request ID middleware
# ---------------------------------------------------------------------------


@app.middleware("http")
async def add_request_id(request: Request, call_next: Any) -> Response:
    """Attach a unique request ID to every request.

    The ID is set on ``request.state.request_id`` and returned as the
    ``X-Request-ID`` response header for correlation.
    """
    request_id = uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ---------------------------------------------------------------------------
# Error helper
# ---------------------------------------------------------------------------


def _http_error(
    status_code: int,
    code: str,
    message: str,
    details: str | None = None,
    request_id: str | None = None,
    job_id: str | None = None,
) -> HTTPException:
    """Raise a structured HTTP exception with an :class:`ErrorDetail` body."""
    detail = ErrorDetail(
        code=code,
        message=message,
        details=details,
        request_id=request_id,
        job_id=job_id,
    ).model_dump(exclude_none=True)
    return HTTPException(status_code=status_code, detail=detail)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

_conversion_counts: dict[tuple[str, str], int] = defaultdict(
    int
)  # (converter, status) -> count
_conversion_durations: dict[str, list[float]] = defaultdict(
    list
)  # converter -> durations
_metric_timeouts: int = 0
_metric_errors: int = 0


def _record_conversion(converter: str, status: int, duration: float) -> None:
    """Record a conversion metric."""
    status_label = (
        "success" if status == 0 else "timeout" if status == 9997 else "error"
    )
    _conversion_counts[(converter, status_label)] += 1
    _conversion_durations[converter].append(duration)
    if status == 9997:
        global _metric_timeouts
        _metric_timeouts += 1
    if status != 0 and status != 9997:
        global _metric_errors
        _metric_errors += 1


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, show_versions: bool = False) -> HTMLResponse:
    """Render the server status web page.

    Args:
        request: FastAPI request object (required by Jinja2Templates).
        show_versions: When True, fetches and displays version info
            for each converter alongside the availability status.

    Returns:
        Rendered HTML page with converter cards and API documentation links.
    """
    converter_versions: dict[str, str] = {}
    if show_versions:
        converter_versions = await registry.converter_versions()

    params = {
        "request": request,
        "converters": ", ".join(registry.available_converters()),
        "show_versions": show_versions,
        "converter_versions": converter_versions,
        "version": VERSION,
        "python_version": sys.version,
    }
    return templates.TemplateResponse(request, "index.html", params)


@app.get("/converters", response_model=ConvertersResponse)
async def converters() -> ConvertersResponse:
    """List all available converter names.

    Returns converters whose binaries were found in the system PATH.
    """
    return ConvertersResponse(converters=registry.available_converters())


@app.get("/converter-versions")
async def converter_versions() -> dict[str, Any]:
    """Return version strings for all available converters.

    Runs ``--version`` for each converter in parallel and returns results.
    Converters that fail to report a version are omitted.
    """
    versions = await registry.converter_versions()
    return dict(converters=versions)


@app.get("/converter", response_model=ConverterDetailResponse)
async def has_converter(converter_name: str) -> ConverterDetailResponse:
    """Check if a specific converter is available.

    Args:
        converter_name: Name of the converter to check.

    Returns:
        Availability status for the requested converter.
    """
    return ConverterDetailResponse(
        has_converter=registry.has_converter(converter_name),
        converter=converter_name,
    )


@app.get("/version", response_model=VersionResponse)
async def get_version() -> VersionResponse:
    """Return the server version and module name."""
    return VersionResponse(version=VERSION, module="pp.server")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint for load balancers and orchestrators.

    Returns a simple status response. Does not verify converter health.
    """
    return HealthResponse(status="healthy", version=VERSION)


@app.get("/ready", response_model=ReadyResponse)
async def ready() -> ReadyResponse | JSONResponse:
    """Readiness check endpoint.

    Verifies that the spool directory is writable. Returns 200 when
    ready, 503 when the spool is not writable.
    """
    spool_writable = os.access(str(queue_dir), os.W_OK)
    response = ReadyResponse(
        status="ready" if spool_writable else "not_ready",
        spool_writable=spool_writable,
    )
    if not spool_writable:
        return JSONResponse(status_code=503, content=response.model_dump())
    return response


@app.get("/cleanup")
async def cleanup() -> dict[str, Any]:
    """Remove stale conversion queue data older than one day.

    Triggers :func:`cleanup_queue` and returns the result.
    """
    cleanup_queue()
    return dict(status="OK")


@app.get("/selftest")
async def converter_selftest(converter: str) -> Response:
    """Run a self-test for a specific converter.

    Downloads a generated PDF (or EPUB for Calibre) as a file attachment.

    Args:
        converter: Name of the converter to test.

    Returns:
        PDF or EPUB file as a downloadable response.

    Raises:
        HTTPException 404: Converter not found or not available.
        HTTPException 500: Self-test execution failed.
    """
    available_converters = registry.available_converters()
    if converter not in available_converters:
        raise _http_error(
            404,
            "converter_not_available",
            f"Converter {converter} is not available or not installed",
        )

    try:
        pdf_data = await selftest(converter)
    except FileNotFoundError as e:
        raise _http_error(
            500,
            "selftest_file_not_found",
            f"Self-test for {converter} failed - file not found: {e}",
        )
    except OSError as e:
        raise _http_error(
            500,
            "selftest_os_error",
            f"Self-test for {converter} failed - OS error: {e}",
        )
    except Exception as e:
        raise _http_error(
            500,
            "selftest_failed",
            f"Self-test for {converter} failed: {e}",
        )

    if converter == "calibre":
        return Response(
            content=pdf_data,
            media_type="application/epub+zip",
            headers={
                "content-disposition": "attachment; filename=selftest-calibre.epub"
            },
        )

    return Response(
        content=pdf_data,
        media_type="application/pdf",
        headers={
            "content-disposition": f"attachment; filename=selftest-{converter}.pdf"
        },
    )


@app.get("/metrics")
async def metrics() -> JSONResponse:
    """Return basic operational metrics as JSON.

    Exposes conversion counts by converter/status, average durations,
    active job count, and timeout/error counts.
    """
    durations: dict[str, dict[str, float]] = {}
    for conv, vals in _conversion_durations.items():
        if vals:
            durations[conv] = {
                "count": len(vals),
                "avg_seconds": sum(vals) / len(vals),
                "max_seconds": max(vals),
            }
        else:
            durations[conv] = {"count": 0, "avg_seconds": 0.0, "max_seconds": 0.0}

    # Aggregate counts by status across converters
    counts_by_status: dict[str, int] = defaultdict(int)
    counts_by_converter: dict[str, dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    for (conv, status_label), count in _conversion_counts.items():
        counts_by_status[status_label] += count
        counts_by_converter[conv][status_label] += count

    return JSONResponse(
        content={
            "conversions": {
                "total": sum(counts_by_status.values()),
                "by_status": dict(counts_by_status),
                "by_converter": {
                    conv: dict(labels) for conv, labels in counts_by_converter.items()
                },
            },
            "durations": durations,
            "active_jobs": len(_active_jobs),
            "timeouts": _metric_timeouts,
            "errors": _metric_errors,
        }
    )


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    413: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
    504: {"model": ErrorResponse},
}


@app.post("/convert", response_model=ConvertResponse, responses=ERROR_RESPONSES)
async def convert(
    converter: str = Form(
        "prince",
        title="Converter name",
        description=(
            "`converter` must be the name of a registered converter "
            "e.g. `prince` or `antennahouse`"
        ),
    ),
    cmd_options: str = Form(
        " ",
        title="Converter commandline options",
        description=(
            "`cmd_options` can be used to specify converter specific "
            "commandline options"
        ),
    ),
    data: str = Form(
        ...,
        title="Content to be converted",
        description=(
            "`data` must be a base64 encoded ZIP archive containing "
            "your index.html and all related assets like CSS, images, etc."
        ),
    ),
    request: Request = None,  # type: ignore[assignment]  # ty: ignore
) -> ConvertResponse:
    """Convert a ZIP archive to PDF using the specified converter.

    Accepts a base64-encoded ZIP file containing an ``index.html``
    together with all required assets (CSS, images, fonts).

    Validates input before any disk operations, rejecting invalid
    payloads with structured HTTP errors.
    """
    request_id: str | None = (
        getattr(request.state, "request_id", None) if request else None
    )

    # Periodic queue cleanup (runs once per interval)
    cleanup_queue()

    # --- Input validation ---

    # 1. Validate converter
    if converter not in registry.available_converters():
        raise _http_error(
            404,
            "converter_not_available",
            f"Converter {converter!r} is not available or not installed",
            request_id=request_id,
        )

    # 2. Validate cmd_options at the route layer
    from pp.server.util import parse_cmd_options as _parse_cmd_options

    try:
        _parse_cmd_options(cmd_options)
    except ValueError as e:
        raise _http_error(
            400,
            "invalid_cmd_options",
            f"Invalid command options: {e}",
            request_id=request_id,
        )

    # 3. Data is required (FastAPI Form(...) handles None, but be explicit)
    if not data:
        raise _http_error(
            400,
            "missing_data",
            "The `data` field is required and must contain a base64-encoded ZIP archive",
            request_id=request_id,
        )

    # 4. Decode base64 with strict validation
    try:
        data_bytes = data.encode("ascii")
    except (binascii.Error, UnicodeEncodeError, ValueError, TypeError) as e:
        raise _http_error(
            400,
            "invalid_base64",
            f"Failed to decode base64 data: {e}",
            request_id=request_id,
        )
    max_encoded_request_size = int(
        os.environ.get("PP_MAX_ENCODED_REQUEST_SIZE", "146800640")
    )
    if len(data_bytes) > max_encoded_request_size:
        raise _http_error(
            413,
            "payload_too_large",
            f"Encoded request size {len(data_bytes)} exceeds limit "
            f"{max_encoded_request_size} bytes",
            request_id=request_id,
        )
    try:
        normalized_data = b"".join(data_bytes.split())
        zip_data = base64.b64decode(normalized_data, validate=True)
    except (binascii.Error, ValueError, TypeError) as e:
        raise _http_error(
            400,
            "invalid_base64",
            f"Failed to decode base64 data: {e}",
            request_id=request_id,
        )

    # 5. Verify the decoded payload is a ZIP
    if not zip_data.startswith(b"PK\x03\x04"):
        raise _http_error(
            400,
            "invalid_zip",
            "The decoded payload is not a valid ZIP archive (missing PK\\x03\\x04 magic)",
            request_id=request_id,
        )
    try:
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            zf.testzip()
    except zipfile.BadZipFile as e:
        raise _http_error(
            400,
            "invalid_zip",
            f"The decoded payload is not a valid ZIP archive: {e}",
            request_id=request_id,
        )

    # 6. Check max request size
    max_request_size = int(
        os.environ.get("PP_MAX_REQUEST_SIZE", str(104_857_600))  # 100 MB
    )
    if len(zip_data) > max_request_size:
        raise _http_error(
            413,
            "payload_too_large",
            f"Request payload size {len(zip_data)} exceeds limit {max_request_size} bytes",
            request_id=request_id,
        )

    # --- Job setup ---
    new_id = new_converter_id(converter)
    work_dir = queue_dir / new_id
    out_dir = work_dir / "out"

    try:
        work_dir.mkdir(parents=False, exist_ok=False)
        out_dir.mkdir(parents=False, exist_ok=False)
    except OSError as e:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise _http_error(
            500,
            "workdir_creation_failed",
            f"Failed to create working directory: {e}",
            request_id=request_id,
            job_id=new_id,
        )

    work_file = work_dir / "in.zip"

    try:
        work_file.write_bytes(zip_data)
    except OSError as e:
        # Clean up the empty directory we just created
        shutil.rmtree(work_dir, ignore_errors=True)
        raise _http_error(
            500,
            "workfile_write_failed",
            f"Failed to write input ZIP: {e}",
            request_id=request_id,
            job_id=new_id,
        )

    # Register as active job
    _active_jobs.add(new_id)

    try:
        conversion_log = _make_converter_log(str(work_dir))

        ts = time.time()
        log_msg = (
            f"START: pdf(ID {new_id}, workfile {work_file}, "
            f"converter {converter}, cmd_options {cmd_options})"
        )
        conversion_log(log_msg)
        LOG.bind(
            request_id=request_id,
            job_id=new_id,
            converter=converter,
            input_size=len(zip_data),
            status="start",
        ).info(log_msg)

        result = await convert_pdf(
            str(work_dir), str(work_file), converter, conversion_log, cmd_options
        )

        duration = time.time() - ts

        # Record metrics
        _record_conversion(converter, result["status"], duration)
        status_label = "OK" if result["status"] == 0 else "ERROR"
        output_size = 0

        log_msg = f"END : pdf({new_id} {duration:.3f} sec): {status_label}"
        conversion_log(log_msg)

        output = result["output"]

        if result["status"] == 0:  # OK
            pdf_bytes = Path(str(result["filename"])).read_bytes()
            output_size = len(pdf_bytes)
            LOG.bind(
                request_id=request_id,
                job_id=new_id,
                converter=converter,
                duration=duration,
                status="success",
                timeout=False,
                input_size=len(zip_data),
                output_size=output_size,
            ).info(log_msg)
            pdf_b64 = base64.encodebytes(pdf_bytes).decode("ascii")
            return ConvertResponse(status="OK", data=pdf_b64, output=output)

        # Converter process failure
        error_code = (
            "conversion_timeout"
            if result["status"] == 9997
            else "zip_limit_exceeded"
            if result["status"] == 9989
            else "invalid_zip"
            if result["status"] == 9988
            else "unknown_converter"
            if result["status"] == 9999
            else "conversion_failed"
        )
        status_code = (
            504
            if result["status"] == 9997
            else 413
            if result["status"] == 9989
            else 400
            if result["status"] == 9988
            else 502
        )
        LOG.bind(
            request_id=request_id,
            job_id=new_id,
            converter=converter,
            duration=duration,
            status="timeout" if result["status"] == 9997 else "error",
            timeout=result["status"] == 9997,
            input_size=len(zip_data),
            output_size=output_size,
        ).error(f"Conversion failed: {output}")
        raise _http_error(
            status_code,
            error_code,
            f"Conversion failed with status {result['status']}",
            details=output[:2000] if output else None,
            request_id=request_id,
            job_id=new_id,
        )
    finally:
        _active_jobs.discard(new_id)


# ---------------------------------------------------------------------------
# Queue cleanup
# ---------------------------------------------------------------------------


def cleanup_queue() -> dict[str, int] | None:
    """Remove expired entries from the conversion queue directory.

    Cleans up subdirectories and files older than ``QUEUE_CLEANUP_TIME``
    (24 hours by default). Skips directories currently in the active job
    registry. Runs at most once per interval (tracked by ``LAST_CLEANUP``).

    Returns:
        Dictionary with ``directories_removed`` count, or ``None`` if
        the cleanup interval has not elapsed since the last run.
    """
    global LAST_CLEANUP

    queue_dir.mkdir(parents=True, exist_ok=True)

    now = time.time()
    if now - LAST_CLEANUP < QUEUE_CLEANUP_TIME:
        return None

    removed = 0
    for item in list(queue_dir.iterdir()):
        # Skip active jobs
        if item.name in _active_jobs:
            LOG.debug(f"Skipping active job during cleanup: {item.name}")
            continue

        try:
            mtime = item.stat().st_mtime
            if now - mtime > QUEUE_CLEANUP_TIME:
                LOG.debug(f"Cleanup: {item}")
                if item.is_dir():
                    shutil.rmtree(item)
                elif item.is_file():
                    item.unlink()
                removed += 1
        except OSError as e:
            LOG.warning(f"Cleanup error for {item}: {e}")

    LAST_CLEANUP = time.time()
    return dict(directories_removed=removed)


# ---------------------------------------------------------------------------
# Job ID generation
# ---------------------------------------------------------------------------


def new_converter_id(converter: str) -> str:
    """Generate a unique conversion job ID with UUID.

    Format: ``<uuid_hex>-<sanitized_converter_name>``

    Uses a UUID hex string instead of a timestamp to prevent
    collisions and path confusion.

    Args:
        converter: Converter name to include in the ID.

    Returns:
        Unique job identifier string safe for use as a directory name.
    """
    # Sanitize converter name to prevent path traversal in job IDs
    safe_converter = converter.replace("/", "_").replace("\\", "_")
    return f"{uuid.uuid4().hex}-{safe_converter}"


# ---------------------------------------------------------------------------
# Conversion logging
# ---------------------------------------------------------------------------


def _make_converter_log(work_dir: str) -> Any:
    """Create a per-job log function that writes to ``converter.log``."""

    def _log(msg: str) -> None:
        converter_log(work_dir, msg)

    return _log


def converter_log(work_dir: str, msg: str) -> None:
    """Write a timestamped log entry for a conversion job.

    Args:
        work_dir: Working directory of the conversion job.
        msg: Log message to write.
    """
    converter_logfile = Path(work_dir) / "converter.log"
    msg = datetime.datetime.now().strftime("%Y%m%dT%H%M%S") + " " + msg
    with open(converter_logfile, "a") as fp:
        try:
            fp.write(msg + "\n")
        except (UnicodeEncodeError, UnicodeDecodeError):
            fp.write(msg.encode("ascii", "replace").decode("ascii", "replace") + "\n")
