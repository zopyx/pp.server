################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX,  Tuebingen, Germany
################################################################


import os
import pkg_resources


def main():
    """ Generate circusd.ini and server.ini """

    for fn in ("circusd.ini", "server.ini"):
        data = pkg_resources.resource_string("pp.server._templates", fn)
        output_fn = os.path.join(os.path.abspath(os.getcwd()), fn)
        print("Generating ", output_fn)

        with open(output_fn, "wb") as fp:
            fp.write(data)
