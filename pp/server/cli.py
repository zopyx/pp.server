"""Command-line interface for the Produce & Publish Server.

Provides the ``pp-server`` CLI command for starting the HTTP server
with configurable host, port, and reload options.
"""

import click
import uvicorn


@click.command()
@click.option("--host", default="127.0.0.1", help="Host IP to bind to")
@click.option("--port", default=8080, help="Port to bind to")
@click.option("-b", "--bind", default=None, help="Bind to <host>:<port> (overrides --host/--port)")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload on code changes")
def main(
    host: str = "127.0.0.1",
    port: int = 8080,
    bind: str | None = None,
    reload: bool = False,
) -> None:
    """Start the Produce & Publish HTTP server.

    Launches a Uvicorn ASGI server running the FastAPI application.
    Use ``--bind host:port`` as a shorthand for setting both host and port.

    Examples::

        pp-server
        pp-server --host 0.0.0.0 --port 9000
        pp-server --bind 0.0.0.0:8000 --reload
    """
    if bind:
        if ":" in bind:
            parts = bind.split(":")
            host = parts[0]
            port = int(parts[1])
        else:
            host = bind

    uvicorn.run(
        "pp.server.server:app",
        host=host,
        port=port,
        reload=reload,
    )
