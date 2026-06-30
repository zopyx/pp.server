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
import datetime
import functools
import os
import shutil
import sys
import time
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pp.server import registry
from pp.server.converters import convert_pdf, selftest
from pp.server.logger import LOG
from pp.server.models import (
    ConverterDetailResponse,
    ConvertersResponse,
    ConvertResponse,
    HealthResponse,
    VersionResponse,
)

# How often to cleanup the queue directory?
QUEUE_CLEANUP_TIME = 24 * 60 * 60  # 1 day

# Internal timestamp for the last cleanup action
LAST_CLEANUP = time.time() - 3600 * 24 * 10

# Bootstrap: register all convertes
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
    converter_versions = {}
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
        has_converter=registry.has_converter(converter_name), converter=converter_name
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
        raise HTTPException(
            status_code=404,
            detail=f"Converter {converter} is not available or not installed",
        )

    try:
        pdf_data = await selftest(converter)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Self-test for {converter} failed - file not found: {e}",
        )
    except OSError as e:
        raise HTTPException(
            status_code=500, detail=f"Self-test for {converter} failed - OS error: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Self-test for {converter} failed: {e}"
        )

    if converter == "calibre":
        return Response(
            content=pdf_data,
            media_type="application/epub+zip",
            headers={
                "content-disposition": "attachment; filename=selftest-calibre.epub"
            },
        )

    else:
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={
                "content-disposition": f"attachment; filename=selftest-{converter}.pdf"
            },
        )


@app.post("/convert", response_model=ConvertResponse)
async def convert(
    converter: str = Form(
        "prince",
        title="Converter name",
        description="`converter` must be the name of a registered converter e.g. `prince` or `antennahouse`",
    ),
    cmd_options: str = Form(
        " ",
        title="Converter commandline options",
        description="`cmd_options` can be used to specify converter specify commandline options. Bug: you need to specify a string of at lease one byte length (e.g. a whitespace)",
    ),
    data: str = Form(
        None,
        title="Content to be converted",
        description="`data` must be a base64 encoded ZIP archive containing your index.html and all related assets like CSS, images etc.",
    ),
):
    """Convert a ZIP archive to PDF using the specified converter.

    Accepts a base64-encoded ZIP file containing an ``index.html``
    together with all required assets (CSS, images, fonts).

    Args:
        converter: Name of the registered converter to use.
        cmd_options: Additional command-line flags for the converter.
            Must be at least one character (use a space as placeholder).
        data: Base64-encoded ZIP archive with the document and assets.

    Returns:
        JSON with ``status`` (``OK`` or ``ERROR``), ``data`` (base64 PDF
        on success), and ``output`` (conversion transcript).
    """
    cleanup_queue()

    zip_data = base64.decodebytes(data.encode("ascii"))

    new_id = new_converter_id(converter)
    work_dir = queue_dir / new_id
    out_dir = work_dir / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    work_file = work_dir / "in.zip"
    work_file.write_bytes(zip_data)

    conversion_log = functools.partial(converter_log, str(work_dir))

    ts = time.time()
    msg = f"START: pdf(ID {new_id}, workfile {work_file}, converter {converter}, cmd_options {cmd_options})"
    conversion_log(msg)
    LOG.info(msg)
    result = await convert_pdf(
        str(work_dir), str(work_file), converter, conversion_log, cmd_options
    )

    duration = time.time() - ts
    msg = f"END : pdf({new_id} {duration} sec): {result['status']}"
    conversion_log(msg)
    LOG.info(msg)

    output = result["output"]
    if result["status"] == 0:  # OK
        pdf_bytes = Path(result["filename"]).read_bytes()
        pdf_b64 = base64.encodebytes(pdf_bytes).decode("ascii")
        return dict(status="OK", data=pdf_b64, output=output)
    else:  # error
        LOG.error(f"Conversion failed: {output}")
        return dict(status="ERROR", output=output)


def cleanup_queue() -> dict[str, int] | None:
    """Remove expired entries from the conversion queue directory.

    Cleans up subdirectories and files older than ``QUEUE_CLEANUP_TIME``
    (24 hours). Runs at most once per interval (tracked by ``LAST_CLEANUP``).

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
    for item in queue_dir.iterdir():
        mtime = item.stat().st_mtime
        if now - mtime > QUEUE_CLEANUP_TIME:
            LOG.debug(f"Cleanup: {item}")
            if item.is_dir():
                shutil.rmtree(item)
            elif item.is_file():
                item.unlink()
            removed += 1

    LAST_CLEANUP = time.time()
    return dict(directories_removed=removed)


def new_converter_id(converter: str) -> str:
    """Generate a unique conversion job ID.

    Format: ``YYYYMMDDTHHMMSS.ffffff-<converter_name>``

    Args:
        converter: Converter name to include in the ID.

    Returns:
        Unique job identifier string.
    """
    return datetime.datetime.now().strftime("%Y%m%dT%H%M%S.%f") + "-" + converter


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
