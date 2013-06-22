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

    from views import XMLRPC_API
    config.add_view(XMLRPC_API, name='api')
    config.scan()
    return config.make_wsgi_app()
