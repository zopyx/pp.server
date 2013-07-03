################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX Ltd, Tuebingen, Germany
################################################################

from pyramid.config import Configurator

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')

    config.scan()
    config.add_route('unoconv_api_1', '/api/1/unoconv')
    config.add_route('pdf_api_1', '/api/1/pdf')
    return config.make_wsgi_app()


