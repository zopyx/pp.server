################################################################
# pp.server - Produce & Publish Server
# (C) 2021, ZOPYX,  Tuebingen, Germany
################################################################
"""Entry poing for generating circusd template ini"""

import os

import pkgutil


def load_resource(package, resource_name):
    data = pkgutil.get_data(package, resource_name)
    return data


def main():
    """Generate circusd.ini and server.ini"""

    for filename in ("circusd.ini", "server.ini"):
        data = load_resource("pp.server._templates", filename)
        output_filename = os.path.join(os.path.abspath(os.getcwd()), filename)
        print("Generating ", output_filename)

        with open(output_filename, "wb") as fp:
            fp.write(data)
