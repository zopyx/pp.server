################################################################
# pp.server - Produce & Publish Server
# (C) 2021, ZOPYX,  Tuebingen, Germany
################################################################

import click
import uvicorn


@click.command()
@click.option("--host", default="127.0.0.1", help="Host IP to bind to")
@click.option("--port", default=8080, help="Port to bind to")
@click.option("-b", "--bind", default=None, help="Bind to <host>:<port>")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload")
def main(host, port, bind, reload):
    """Start the pp.server"""
    if bind:
        if ":" in bind:
            host, port = bind.split(":")
            port = int(port)
        else:
            host = bind

    uvicorn.run(
        "pp.server.server:app",
        host=host,
        port=port,
        reload=reload,
    )
