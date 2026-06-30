import click
import uvicorn


@click.command()
@click.option("--host", default="127.0.0.1", help="Host IP to bind to")
@click.option("--port", default=8080, help="Port to bind to")
@click.option("-b", "--bind", default=None, help="Bind to <host>:<port>")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload")
def main(
    host: str = "127.0.0.1",
    port: int = 8080,
    bind: str | None = None,
    reload: bool = False,
) -> None:
    """Start the pp.server"""
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
