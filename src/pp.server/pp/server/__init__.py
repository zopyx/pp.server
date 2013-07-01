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



# Monkey patch pyramid_xmlrpc.parse_xmlrpc_request in order
# to avoid (stupid) DOS request body size check.
import xmlrpclib
import pyramid_xmlrpc

def parse_xmlrpc_request(request):
    """ Deserialize the body of a request from an XML-RPC request
    document into a set of params and return a two-tuple.  The first
    element in the tuple is the method params as a sequence, the
    second element in the tuple is the method name."""
    params, method = xmlrpclib.loads(request.body)
    return params, method
pyramid_xmlrpc.parse_xmlrpc_request = parse_xmlrpc_request
