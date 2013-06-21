
import os
import uuid
import xmlrpclib
from pyramid_xmlrpc import XMLRPCView
from webob import Response
from datetime import datetime
from pyramid.view import view_config
import converters

queue_dir = os.path.join(os.getcwd(), 'var', 'queue')
if not os.path.exists(queue_dir):
    os.makedirs(queue_dir)


class StandardView(object):

    def __init__(self, request):
        self.request = request

    @view_config(route_name='home', renderer='index.pt', request_method='GET')
    def index(self):
        return {}


class XMLRPC(XMLRPCView):

    def unoconv(self,
                input_filename,
                input_data, 
                output_format='pdf', 
                async=False):

        new_id = str(uuid.uuid4())
        work_dir = os.path.join(queue_dir, new_id)
        os.mkdir(work_dir)
        work_file = os.path.join(work_dir, os.path.basename(input_filename))
        with open(work_file, 'wb') as fp:
            fp.write(input_data.data)

        if async:
            return dict(id=new_id, message=u'Conversion request queued')
        else:
            result = converters.unoconv(work_file, output_format)
            if result['status'] == 0: #OK
                return dict(status='OK',
                            data=xmlrpclib.Binary(open(result['filename'], 'rb').read()),
                            output=result['output'])
            else: # error
                return dict(status='ERROR',
                            output=result['output'])

