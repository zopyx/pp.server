################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX,  Tuebingen, Germany
################################################################

__import__("pkg_resources").declare_namespace(__name__)

from pyramid.config import Configurator
import pyramid.threadlocal
from pyramid.settings import asbool

from pp.server.logger import LOG


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include("pyramid_chameleon")
    config.add_static_view("static", "static", cache_max_age=3600)
    config.add_route("home", "/")
    config.scan()
    config.add_route("unoconv_api_1", "/api/1/unoconv")
    config.add_route("pdf_api_1", "/api/1/pdf")
    config.add_route("poll_api_1", "/api/1/poll/{jobid}")
    config.add_route("version", "/api/version")
    config.add_route("cleanup", "/api/cleanup")
    config.add_route("available_converters", "/api/converters")
    config.add_route("converter_versions", "/api/converter-versions")

    from pp.server.views import WebViews

    v = WebViews(request=None)
    installed = [c for c, avail in v.available_converters().items() if avail]
    LOG.info("Installed: {}".format(", ".join(installed)))

    remote_exec = asbool(settings.get("remote_execution", "false"))
    settings["remote_exec"] = remote_exec
    LOG.info("Remote execution enabled: {0}".format(remote_exec))

    return config.make_wsgi_app()
