pp.server - Produce & Publish Server
====================================

``pp.server`` is a FastAPI-based REST server for converting HTML/XML to PDF
using various external PrintCSS converters. It is the server-side component
of the **Produce & Publish** platform.

Supported converters
--------------------

- PrinceXML (www.princexml.com, commercial)
- PDFreactor (www.realobjects.com, commercial)
- Speedata Publisher (www.speedata.de, open-source)
- WKHTMLTOPDF (www.wkhtmltopdf.org, open-source)
- Vivliostyle Formatter (www.vivliostyle.com, commercial)
- VersaType Formatter (www.trim-marks.com, commercial)
- Antennahouse 7 (www.antennahouse.com, commercial)
- Weasyprint (free)
- Typeset.sh (www.typeset.sh, commercial)
- PagedJS (www.pagedjs.org, free)
- Calibre (www.calibre.org, open-source, EPUB only)

Requirements
------------

- Python 3.12 or higher
- External converter binaries must be in ``$PATH`` (see list above)

Installation
------------

This project uses `uv` as package and virtualenv manager::

    git clone https://github.com/zopyx/pp.server
    cd pp.server
    uv venv --python 3.12
    uv sync --all-extras

Running the server
------------------

::

    pp-server --host 0.0.0.0 --port 8000

Or using the Makefile::

    make serve

The server runs on **Hypercorn** (HTTP/2-capable ASGI server).
For production::

    make serve-prod

Process management with Circus::

    pp-server-templates   # generates circusd.ini + server.ini
    circusd circusd.ini   # managed daemon

Docker
------

Dockerfiles are provided under ``docker/`` for various converter combinations:

- ``docker/weasyprint/`` — pp.server + WeasyPrint
- ``docker/speedata/`` — pp.server + Speedata Publisher
- ``docker/speedata-princexml-weasyprint/`` — all three

Build::

    cd docker/weasyprint
    docker build -t pp-server .
    docker run -p 8000:8000 pp-server

REST API
--------

All API methods are available via REST endpoints::

    POST /convert      Convert ZIP archive to PDF
    GET  /converters   List available converters
    GET  /version      Server version info
    GET  /health       Health check
    GET  /cleanup      Clean up queue directory
    GET  /selftest     Run converter self-test

Interactive API documentation is available at http://localhost:8000/docs
when the server is running.

Environment variables
---------------------

- ``PP_SPOOL_DIRECTORY`` — custom spool directory (default: ``var/queue``)
- ``PP_PDFREACTOR_DOCKER`` — set to ``1`` for PDFreactor under Docker

Development
-----------

See ``DEVELOPMENT.md`` for the full developer guide.

Quick start::

    make dev-setup     # install dev dependencies
    make test          # run tests
    make quality       # lint + type-check + test
    make coverage      # run tests with HTML coverage report
    make build         # build distribution packages

Source code
-----------

https://github.com/zopyx/pp.server

License
-------

``pp.server`` is published under the GNU Public License V2 (GPL 2).

Contact
-------

| ZOPYX
| Hundskapfklinge 33
| D-72074 Tuebingen, Germany
| info@zopyx.com
| www.zopyx.com
