
import os
import time
import uuid
import xmlrpclib
import zlib
from pyramid_xmlrpc import XMLRPCView
from webob import Response
from datetime import datetime
from pyramid.view import view_config
from logger import LOG

import converters
import tasks

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
            tasks.unoconv.delay(job_id=new_id,
                                work_dir=work_dir,
                                input_filename=work_file,
                                output_format=output_format)
            return dict(id=new_id, message=u'Conversion request queued')
        else:
            ts = time.time()
            LOG.info('START: unoconv({}, {}, {}, {})'.format(new_id, work_file, output_format, async))
            result = converters.unoconv(work_file, output_format)
            duration = time.time() - ts
            LOG.info('END : unoconv({} {} sec): {}'.format(new_id, duration, result['status']))
            if result['output']:
                LOG.info('OUTPUT: unoconv({}):\n{}'.format(new_id, result['output']))
            if result['status'] == 0: #OK
                return dict(status='OK',
                            data=xmlrpclib.Binary(open(result['filename'], 'rb').read()),
                            output=result['output'])
            else: # error
                return dict(status='ERROR',
                            output=result['output'])

    def pdf(self,
            zip_data, 
            converter='princexml',
            async=False):

        new_id = str(uuid.uuid4())
        work_dir = os.path.join(queue_dir, new_id)
        os.mkdir(work_dir)
        work_file = os.path.join(work_dir, 'in.zip')
        with open(work_file, 'wb') as fp:
            fp.write(zip_data.data)

        if async:
            raise NotImplementedError
            tasks.unoconv.delay(job_id=new_id,
                                work_dir=work_dir,
                                input_filename=work_file,
                                output_format=output_format)
            return dict(id=new_id, message=u'Conversion request queued')
        else:
            ts = time.time()
            LOG.info('START: pdf({}, {}, {}, {})'.format(new_id, work_file, converter, async))
            result = converters.pdf(work_dir, work_file, converter)
            duration = time.time() - ts
            LOG.info('END : pdf({} {} sec): {}'.format(new_id, duration, result['status']))
            if result['output']:
                LOG.info('OUTPUT: pdf({}):\n{}'.format(new_id, result['output']))
            if result['status'] == 0: #OK
                pdf_data = open(result['filename'], 'rb').read()
                pdf_data = zlib.compress(pdf_data)
                return dict(status='OK',
                            data=xmlrpclib.Binary(pdf_data),
                            compression='zlib',
                            output=result['output'])
            else: # error
                return dict(status='ERROR',
                            output=result['output'])

