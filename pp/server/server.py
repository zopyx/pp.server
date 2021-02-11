# -*- coding: utf-8 -*-

from typing import Optional

from fastapi import FastAPI
from fastapi import Request 
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pp.server import registry

templates = Jinja2Templates(directory="templates")

# bootstrap
registry._register_converters()

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    params = {
        "request": request, 
        "converters": registry.available_converters()
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


