################################################################
# pp.server - Produce & Publish Server
# (C) 2021, ZOPYX,  Tuebingen, Germany
################################################################

import base64
import datetime
import functools
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, Any

from importlib.metadata import version

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pp.server import registry
from pp.server.converters import convert_pdf, selftest
from pp.server.logger import LOG

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

VERSION = version("pp.server")
LOG.info(f"QUEUE: {queue_dir}")
LOG.info(f"pp.server V {VERSION}")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, show_versions: bool = False):
    """Produce & Publish web view"""

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


@app.get("/converters")
async def converters() -> Dict[str, Any]:
    """Return names of all converters"""
    return dict(converters=registry.available_converters())


@app.get("/converter-versions")
async def converter_versions() -> Dict[str, Any]:
    """Return names of all converters"""
    versions = await registry.converter_versions()
    return dict(converters=versions)


@app.get("/converter")
async def has_converter(converter_name: str) -> Dict[str, Any]:
    """Return names of all converters"""
    return dict(
        has_converter=registry.has_converter(converter_name), converter=converter_name
    )


@app.get("/version")
async def version() -> Dict[str, Any]:
    """Return the version of the pp.server module"""
    return dict(version=VERSION, module="pp.server")


@app.get("/cleanup")
async def cleanup() -> Dict[str, Any]:
    """Cleanup up the internal queue"""
    cleanup_queue()
    return dict(status="OK")


@app.get("/selftest")
async def converter_selftest(converter: str):
    """Perform a PDF selftest for a given `converter`"""

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
            status_code=500, detail=f"Self-test for {converter} failed - file not found: {e}"
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


@app.post("/convert")
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
    """The /convert endpoint implements the PrinceCSS to PDF conversion

    The "converter" parameter must be the name of a registered/installed PrinceCSS
    tool (see /converters endpoint)

    The "cmd_options" parameter can be used to specify converter specific
    command line parameters. "cmd_options" can not be omitted. If you want
    to omit the parameter, please specify a string with one whitespace
    (known bug :-)).

    The "data" parameter is a base64 encoded ZIP archive that contains the
    index.html together with all other assets required to perform the
    conversion.
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
        pdf_data = Path(result["filename"]).read_bytes()
        pdf_data = base64.encodebytes(pdf_data).decode("ascii")
        return dict(status="OK", data=pdf_data, output=output)
    else:  # error
        LOG.error(f"Conversion failed: {output}")
        return dict(status="ERROR", output=output)


def cleanup_queue() -> Dict[str, int]:
    global LAST_CLEANUP

    queue_dir.mkdir(parents=True, exist_ok=True)

    now = time.time()
    if now - LAST_CLEANUP < QUEUE_CLEANUP_TIME:
        return
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
    """New converter id based on timestamp + converter name"""
    return datetime.datetime.now().strftime("%Y%m%dT%H%M%S.%f") + "-" + converter


def converter_log(work_dir: str, msg: str) -> None:
    """Logging per conversion (by work dir)"""
    converter_logfile = Path(work_dir) / "converter.log"
    msg = datetime.datetime.now().strftime("%Y%m%dT%H%M%S") + " " + msg
    with open(converter_logfile, "a") as fp:
        try:
            fp.write(msg + "\n")
        except UnicodeEncodeError:
            # Handle specific Unicode encoding errors
            fp.write(msg.encode("ascii", "replace").decode("ascii", "replace") + "\n")
        except UnicodeDecodeError:
            # Handle specific Unicode decoding errors
            fp.write(msg.encode("ascii", "replace").decode("ascii", "replace") + "\n")
