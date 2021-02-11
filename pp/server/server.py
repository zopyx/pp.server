# -*- coding: utf-8 -*-

import os
import sys
import base64
import time
import datetime
import functools
import pkg_resources
from typing import Optional

from fastapi import FastAPI
from fastapi import Form
from fastapi import Body
from fastapi import File
from fastapi import UploadFile
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pp.server import registry
from pp.server.converters import convert_pdf
from pp.server.logger import LOG

QUEUE_CLEANUP_TIME = 24 * 60 * 60  # 1 day
LAST_CLEANUP = time.time() - 3600 * 24 * 10

# bootstrap
registry._register_converters()

app = FastAPI()

dirname = os.path.dirname(__file__)
static_dir = os.path.join(dirname, 'static')
templates_dir = os.path.join(dirname, 'templates')

templates = Jinja2Templates(directory=templates_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

queue_dir = os.path.join(os.getcwd(), "var", "queue")
queue_dir = os.environ.get('PP_SPOOL_DIRECTORY', queue_dir)
if not os.path.exists(queue_dir):
    try:
        os.makedirs(queue_dir)
    except FileExistsError:
        pass

print('PP_SPOOL_DIRECTORY:', queue_dir)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    version = pkg_resources.require("pp.server")[0].version
    params = {
        "request": request,
        "converters": registry.available_converters(),
        "converter_versions": registry.converter_versions(),
        "version": version,
        "python_version": sys.version,}
    return templates.TemplateResponse("index.html", params)


@app.get("/converters")
async def converters():
    """ Return names of all converters """
    return dict(converters=registry.available_converters())


@app.get("/converter-versions")
async def converters():
    """ Return names of all converters """
    return dict(converters=registry.converter_versions())


@app.get("/converter")
async def has_converter(converter_name):
    """ Return names of all converters """
    return dict(has_converter=registry.has_converter(converter_name))


@app.get("/version")
async def version():
    version = pkg_resources.require("pp.server")[0].version
    return dict(version=version, module="pp.server")


@app.post("/convert")
async def pdf(converter: str = '', file: bytes = File(...)):

    cleanup_queue()

    zip_data = file
    converter = 'typesetsh'
    cmd_options = ''

    new_id = new_converter_id(converter)
    work_dir = os.path.join(queue_dir, new_id)
    out_dir = os.path.join(work_dir, "out")
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    work_file = os.path.join(work_dir, "in.zip")
    with open(work_file, "wb") as fp:
        fp.write(zip_data)

    log = functools.partial(converter_log, work_dir)

    ts = time.time()
    msg = "START: pdf({}, {}, {})".format(new_id, work_file, converter)
    log(msg)
    LOG.info(msg)
    result = convert_pdf(work_dir, work_file, converter, log, cmd_options)

    duration = time.time() - ts
    msg = "END : pdf({} {} sec): {}".format(new_id, duration, result["status"])
    log(msg)
    LOG.info(msg)

    output = result["output"]
    if result["status"] == 0:  # OK
        pdf_data = open(result["filename"], "rb").read()
        pdf_data = base64.encodebytes(pdf_data).decode("ascii")
        return dict(status="OK", data=pdf_data, output=output)
    else:  # error
        return dict(status="ERROR", output=output)


def cleanup_queue():

    global LAST_CLEANUP

    if not os.path.exists(queue_dir):
        os.makedirs(queue_dir)

    now = time.time()
    if now - LAST_CLEANUP < QUEUE_CLEANUP_TIME:
        return
    removed = 0
    for dirname in os.listdir(queue_dir):
        fullname = os.path.join(queue_dir, dirname)
        mtime = os.path.getmtime(fullname)
        if now - mtime > QUEUE_CLEANUP_TIME:
            LOG.debug("Cleanup: {}".format(fullname))
            if os.path.isdir(fullname):
                shutil.rmtree(fullname)
            elif os.path.isfile(fullname):
                os.unlink(fullname)
            removed += 1

    LAST_CLEANUP = time.time()
    return dict(directories_removed=removed)


def new_converter_id(converter):
    """ New converter id based on timestamp + converter name """
    return datetime.datetime.now().strftime("%Y%m%dT%H%M%S.%f") + "-" + converter


def converter_log(work_dir, msg):
    """ Logging per conversion (by work dir) """
    converter_logfile = os.path.join(work_dir, "converter.log")
    msg = datetime.datetime.now().strftime("%Y%m%dT%H%M%S") + " " + msg
    with open(converter_logfile, "a") as fp:
        try:
            fp.write(msg + "\n")
        except UnicodeError:
            fp.write(msg.encode("ascii", "replace").decode("ascii", "replace") + "\n")
