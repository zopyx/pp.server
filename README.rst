pp.server — Produce & Publish Server
====================================

``pp.server`` is a FastAPI-based REST server for converting HTML/XML to PDF
using various external PrintCSS converters. It is the server-side component
of the **Produce & Publish** platform.

Features
--------

- **Shell-free subprocess execution** — converter commands run via
  ``create_subprocess_exec`` with argv lists, eliminating shell injection risk.
- **Structured API errors** — all errors return consistent JSON bodies with
  error codes, messages, and request correlation IDs.
- **Resource limits** — configurable limits on ZIP size, entries, and
  file sizes prevent resource exhaustion.
- **Conversion timeouts** — configurable per-conversion timeout with
  automatic process termination.
- **Process isolation** — subprocesses run with a minimal environment,
  preventing credential leakage.
- **Concurrency-safe cleanup** — UUID-based job IDs and an active-job
  registry prevent cleanup from deleting in-progress conversions.
- **Observability** — request ID middleware, structured logging, metrics
  endpoint, and separate health/readiness checks.
- **Request ID correlation** — all responses include ``X-Request-ID``
  headers; logs include ``request_id`` and ``job_id`` for tracing.

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
    GET  /health       Health check (lightweight)
    GET  /ready        Readiness check (spool writability)
    GET  /metrics      Operational metrics
    GET  /cleanup      Clean up queue directory
    GET  /selftest     Run converter self-test

Interactive API documentation is available at http://localhost:8000/docs
when the server is running.

### POST /convert — Convert ZIP to PDF

**Request** (multipart form data):

- ``converter`` (string, required) — Name of the registered converter.
- ``cmd_options`` (string, optional, default: ``" "``) — Command-line options
  for the converter. Only safe characters are allowed (alphanumerics,
  spaces, ``.``, ``,``, ``-``, ``_``, ``+``, ``=``, ``:``, ``/``, ``\``,
  ``@``, ``(``, ``)``, ``[``, ``]``, ``"``). Shell metacharacters
  (``;``, ``|``, ``$``, `` ` ``, etc.) are rejected.
- ``data`` (string, required) — Base64-encoded ZIP archive containing
  ``index.html`` and all related assets (CSS, images, fonts).

**Success response** (HTTP 200):

.. code-block:: json

    {
      "status": "OK",
      "data": "<base64-encoded PDF>",
      "output": "<conversion transcript>"
    }

**Error responses** (structured JSON body):

.. code-block:: json

    {
      "detail": {
        "code": "converter_not_available",
        "message": "Converter 'prince' is not available or not installed",
        "request_id": "a1b2c3d4e5f6"
      }
    }

**Error codes:**

============ ====== ================================================================
HTTP Status  Code   Description
============ ====== ================================================================
400          ``missing_data``         The ``data`` field was not provided.
400          ``invalid_base64``       The ``data`` field is not valid base64.
400          ``invalid_zip``          The decoded payload is not a ZIP archive.
400          ``invalid_cmd_options``  ``cmd_options`` contains unsafe characters.
404          ``converter_not_available``  The specified converter is not installed.
413          ``payload_too_large``    Request exceeds maximum payload size.
413          ``zip_limit_exceeded``   ZIP archive exceeds configured resource limits.
502          ``conversion_failed``    The converter process returned an error.
504          ``conversion_timeout``   The converter process exceeded the timeout.
500          ``workdir_creation_failed``  Could not create working directory.
500          ``workfile_write_failed``    Could not write input ZIP to disk.
============ ====== ================================================================

### GET /health — Health Check

Returns HTTP 200 with::

    {"status": "healthy", "version": "4.0.0"}

### GET /ready — Readiness Check

Returns HTTP 200 when the spool directory is writable, HTTP 503 otherwise::

    {"status": "ready", "spool_writable": true}

### GET /metrics — Operational Metrics

Returns JSON with conversion counts, durations, active jobs, and error counts::

    {
      "conversions": {
        "total": 42,
        "by_status": {"success": 40, "error": 1, "timeout": 1},
        "by_converter": {"prince": {"success": 40}}
      },
      "durations": {
        "prince": {"count": 40, "avg_seconds": 1.23, "max_seconds": 5.67}
      },
      "active_jobs": 0,
      "timeouts": 1,
      "errors": 1
    }

### GET /converters — List Converters

::

    {"converters": ["prince", "weasyprint"]}

### GET /converter?converter_name=<name> — Check Converter

::

    {"has_converter": true, "converter": "prince"}

### GET /version — Server Version

::

    {"version": "4.0.0", "module": "pp.server"}

### GET /cleanup — Trigger Queue Cleanup

::

    {"status": "OK"}

### GET /selftest?converter=<name> — Run Self-Test

Returns a PDF (or EPUB for Calibre) file as a download.

Environment variables
---------------------

======================== ========= ===============================================================
Variable                 Default   Description
======================== ========= ===============================================================
``PP_SPOOL_DIRECTORY``   ``var/queue``    Custom spool directory for conversion working files.
``PP_PDFREACTOR_DOCKER``           Set to ``1`` to enable PDFreactor Docker execution path.
``PP_MAX_ENCODED_REQUEST_SIZE`` ``146800640`` Maximum size (bytes) of the encoded base64
                                         form value before decoding (140 MB).
``PP_MAX_REQUEST_SIZE``  ``104857600``    Maximum size (bytes) of the base64-decoded request
                                         payload (100 MB).
``PP_MAX_ZIP_SIZE``      ``104857600``    Maximum size (bytes) of the decoded ZIP payload (100 MB).
``PP_MAX_ZIP_ENTRIES``   ``1000``         Maximum number of entries in a ZIP archive.
``PP_MAX_ZIP_TOTAL_UNCOMPRESSED`` ``524288000`` Maximum total uncompressed size (500 MB).
``PP_MAX_ZIP_FILE_SIZE`` ``104857600``    Maximum uncompressed size for a single ZIP entry (100 MB).
``PP_MAX_ZIP_PATH_LENGTH`` ``255``        Maximum path length for extracted ZIP entries.
``PP_CONVERSION_TIMEOUT_SECONDS`` ``300``      Maximum seconds for a single conversion (5 min).
``PP_QUEUE_CLEANUP_INTERVAL`` ``86400``        Queue cleanup interval in seconds (24 h).
``PP_CONVERTER_EXTRA_ENV``       Comma-separated list of additional env var names to pass
                                         to converter subprocesses (e.g. ``HOME,LD_LIBRARY_PATH``).
======================== ========= ===============================================================

Security & Trust Model
----------------------

- **Command injection** — Not possible. All converter commands are executed
  as argv lists via ``create_subprocess_exec``, not via a shell.
- **Path traversal** — ZIP entries with ``../`` or absolute paths are
  rejected during extraction.
- **Resource exhaustion** — ZIP size, entry count, and file size limits
  are enforced before extraction begins.
- **Process isolation** — Converter subprocesses receive a minimal
  environment (only ``PATH``, ``HOME``, ``USER``, ``LANG``, ``TMPDIR``).
  Additional vars can be allowed via ``PP_CONVERTER_EXTRA_ENV``.
  Sensitive credentials are never passed to converter processes.
- **Timeout protection** — All conversions have a configurable timeout.
  Hanging processes are terminated, then killed after a grace period.

Production Deployment
---------------------

### Reverse Proxy

For production, run behind a reverse proxy (nginx, Caddy, Traefik) with:

- Maximum upload body size set to at least ``PP_MAX_REQUEST_SIZE`` + overhead.
- WebSocket support is not required (the API is REST-only).

### Worker Count

Hypercorn worker count should match available CPU cores::

    hypercorn pp.server.server:app --worker-class uvloop --workers 4

### Spool Volume Sizing

Each conversion creates a working directory under ``PP_SPOOL_DIRECTORY``.
Allow at least ``PP_MAX_ZIP_SIZE * PP_MAX_ZIP_ENTRIES`` per concurrent job.
Cleanup runs automatically (see ``PP_QUEUE_CLEANUP_INTERVAL``).

### Cleanup Policy

The cleanup function runs on every ``/convert`` call (throttled to once per
``PP_QUEUE_CLEANUP_INTERVAL``). It removes directories and files older than
the cleanup interval. Active jobs (those currently running) are skipped.

### Container Isolation

For maximum security, run each converter in a separate container with:

- Non-root user.
- Read-only filesystem (except the spool directory).
- Network egress policy that blocks outbound connections if converters
  do not need network access.

### Converter Installation

Each converter's binary must be discoverable in ``PATH`` on the server.
Run ``pp-server --check-converters`` or visit the server's root page
to verify availability.

Troubleshooting
---------------

**Converter not found** — Verify the binary is installed and in ``PATH``.
Check ``GET /converters`` or the root page.

**Conversion timeout** — Increase ``PP_CONVERSION_TIMEOUT_SECONDS`` or
optimize the input document (fewer pages, smaller images, fewer fonts).

**Malformed ZIP** — Ensure the uploaded data is a valid base64-encoded ZIP
archive containing ``index.html`` at the root level.

**Permission problems** — The spool directory (``PP_SPOOL_DIRECTORY``)
must be writable by the server process. Check ``GET /ready``.

**Missing fonts/assets** — All referenced resources (CSS, images, fonts)
must be included in the ZIP archive. External URLs are not resolved by
most PrintCSS converters.

**Type checking** — Use ``make type-check`` (``ty``, not mypy).
Suppressions: ``# ty: ignore[error-code]``.

Development
-----------

See ``DEVELOPMENT.md`` for the full developer guide.

Quick start::

    make dev-setup     # install dev dependencies
    make test          # run tests
    make quality       # lint + type-check + test
    make coverage      # run tests with HTML coverage report
    make build         # build distribution packages
    make ci            # full CI pipeline (lint + type + sast + audit + coverage)

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
