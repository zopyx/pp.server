"""Generate server configuration template files.

Provides the ``pp-server-templates`` CLI command to generate
Circus process manager and Hypercorn ASGI server configuration
files in the current working directory.
"""

import os
import pkgutil


def load_resource(package: str, resource_name: str) -> bytes:
    """Load a package resource as bytes.

    Args:
        package: Dotted package path (e.g. ``pp.server._templates``).
        resource_name: Filename of the resource within the package.

    Returns:
        Raw bytes content of the resource.

    Raises:
        AssertionError: If the resource does not exist.
    """
    data = pkgutil.get_data(package, resource_name)
    assert data is not None, f"Resource {package}/{resource_name} not found"
    return data


def main() -> None:
    """Generate circusd.ini and server.ini in the current directory.

    Reads template files from the ``pp.server._templates`` package
    and writes them to the working directory for use with Circus
    process management and Hypercorn ASGI server.
    """
    for filename in ("circusd.ini", "server.ini"):
        data = load_resource("pp.server._templates", filename)
        output_filename = os.path.join(os.path.abspath(os.getcwd()), filename)
        print("Generating ", output_filename)

        with open(output_filename, "wb") as fp:
            fp.write(data)
