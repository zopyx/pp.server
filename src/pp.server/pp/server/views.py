
import os
import json
import uuid
import pprint
from pyramid_xmlrpc import xmlrpc_view
from webob import Response
from datetime import datetime
from pyramid.view import view_config

queue_dir = os.path.join(os.getcwd(), 'var', 'queue')
if not os.path.exists(queue_dir):
    os.makedirs(queue_dir)


class View(object):

    def __init__(self, request):
        self.request = request

    @view_config(route_name='home', renderer='index.pt', request_method='GET')
    def index(self):
        return {}

@view_config(name='unoconv')
@xmlrpc_view
def unoconv(context, bin_input, output_format='pdf', async=False):
    print bin_input.__class__, output_format, async
    return 42
