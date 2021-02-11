# -*- coding: utf-8 -*-

import os
import sys
import pkg_resources
from typing import Optional

from fastapi import FastAPI
from fastapi import Request 
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pp.server import registry

# bootstrap
registry._register_converters()

app = FastAPI()

dirname = os.path.dirname(__file__)
static_dir = os.path.join(dirname, 'static')
templates_dir = os.path.join(dirname, 'templates')


templates = Jinja2Templates(directory=templates_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")




@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    version = pkg_resources.require("pp.server")[0].version
    params = {
        "request": request, 
        "converters": registry.available_converters(),
        "version": version,
        "python_version": sys.version,
    }
    return templates.TemplateResponse("index.html", params)


@app.get("/converters")
def converters():
    """ Return names of all converters """
    return dict(converters=registry.available_converters())


@app.get("/converter")
def has_converter(converter_name):
    """ Return names of all converters """
    return dict(has_converter=registry.has_converter(converter_name))


