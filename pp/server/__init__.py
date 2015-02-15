################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX,  Tuebingen, Germany
################################################################

__import__('pkg_resources').declare_namespace(__name__)

from pyramid.config import Configurator

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include('pyramid_chameleon')
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')
    config.scan()
    config.add_route('unoconv_api_1', '/api/1/unoconv')
    config.add_route('pdf_api_1', '/api/1/pdf')
    config.add_route('poll_api_1', '/api/1/poll/{jobid}')
    config.add_route('version', '/api/version')
    config.add_route('cleanup', '/api/cleanup')
    config.add_route('available_converters', '/api/converters')
    config.add_route('converter_versions', '/api/converter-versions')
    return config.make_wsgi_app()
