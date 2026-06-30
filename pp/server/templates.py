"""Entry poing for generating circusd template ini"""

import os
import pkgutil


def load_resource(package: str, resource_name: str) -> bytes:
    data = pkgutil.get_data(package, resource_name)
    assert data is not None, f"Resource {package}/{resource_name} not found"
    return data


def main() -> None:
    """Generate circusd.ini and server.ini"""

    for filename in ("circusd.ini", "server.ini"):
        data = load_resource("pp.server._templates", filename)
        output_filename = os.path.join(os.path.abspath(os.getcwd()), filename)
        print("Generating ", output_filename)

        with open(output_filename, "wb") as fp:
            fp.write(data)
