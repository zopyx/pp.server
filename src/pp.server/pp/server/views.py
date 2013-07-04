################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX Ltd, Tuebingen, Germany
################################################################

import os
import base64
import time
import uuid
import xmlrpclib
import pkg_resources
from pyramid_xmlrpc import XMLRPCView
from pyramid.view import view_config
from logger import LOG

import converters
import tasks

queue_dir = os.path.join(os.getcwd(), 'var', 'queue')
if not os.path.exists(queue_dir):
    os.makedirs(queue_dir)

class WebViews(object):

    def __init__(self, request):
        self.request = request

    @view_config(route_name='home', renderer='index.pt', request_method='GET')
    def index(self):
        version = pkg_resources.require('pp.server')[0].version
        return dict(version=version)

    @view_config(route_name='poll_api_1', renderer='json', request_method='GET')
    def poll(self):

        job_id = self.request.matchdict['jobid']
        out_directory = os.path.join(queue_dir, job_id, 'out')
        done_file = os.path.join(out_directory, 'done')
        if os.path.exists(done_file):
            files = [fname for fname in os.listdir(out_directory) if fname.startswith('out.')]
            if files:
                bin_data = base64.encodestring(open(os.path.join(out_directory, files[0]), 'rb').read())
                output_data = open(os.path.join(out_directory, 'output.txt'), 'rb').read()
                return dict(done=True,
                            status=0,
                            data=bin_data,
                            compression='zlib',
                            output=output_data)
            else:
                output_data = open(os.path.join(out_directory, 'output.txt'), 'rb').read()
                return dict(done=True,
                            status=-1,
                            output=output_data)
        return dict(done=False)


    @view_config(route_name='unoconv_api_1', request_method='POST', renderer='json')
    def unoconv(self):
        """ Convert office formats using ``unoconv`` """

        params = self.request.params
        input_filename = params['filename']
        input_data = params['file'].file.read()
        output_format = params.get('output_format', 'pdf')
        async = int(params.get('async', '0'))

        new_id = str(uuid.uuid4())
        work_dir = os.path.join(queue_dir, new_id)
        os.mkdir(work_dir)
        os.mkdir(os.path.join(work_dir, 'out'))
        work_file = os.path.join(work_dir, os.path.basename(input_filename))
        with open(work_file, 'wb') as fp:
            fp.write(input_data)

        if async:
            tasks.unoconv.delay(job_id=new_id,
                                work_dir=work_dir,
                                input_filename=work_file,
                                output_format=output_format)
            LOG.info('Queued unoconv request({})'.format(new_id))
            return dict(id=new_id, message=u'Conversion request queued')
        else:
            ts = time.time()
            LOG.info('START: unoconv({}, {}, {}, {})'.format(new_id, work_file, output_format, async))
            result = converters.unoconv(work_dir, work_file, output_format)
            duration = time.time() - ts
            LOG.info('END : unoconv({} {} sec): {}'.format(new_id, duration, result['status']))
            if result['output']:
                LOG.info('OUTPUT: unoconv({}):\n{}'.format(new_id, result['output']))
            if result['status'] == 0: #OK
                bin_data = base64.encodestring(open(result['filename'], 'rb').read())
                return dict(status='OK',
                            data=bin_data,
                            output=result['output'])
            else: # error
                return dict(status='ERROR',
                            output=result['output'])

    @view_config(route_name='pdf_api_1', request_method='POST', renderer='json')
    def pdf(self):

        params = self.request.params
        zip_data = params['file'].file.read()
        async = int(params.get('async', '0'))
        converter = params.get('converter', 'princexml')

        new_id = str(uuid.uuid4())
        work_dir = os.path.join(queue_dir, new_id)
        os.mkdir(work_dir)
        os.mkdir(os.path.join(work_dir, 'out'))
        work_file = os.path.join(work_dir, 'in.zip')
        with open(work_file, 'wb') as fp:
            fp.write(zip_data)

        if async:
            result = tasks.pdf.delay(job_id=new_id,
                            work_dir=work_dir,
                            work_file=work_file,
                            converter=converter)
            LOG.info('Queued pdf request({})'.format(new_id))
            return dict(id=new_id, message=u'Conversion request queued')
        else:
            ts = time.time()                                               
            LOG.info('START: pdf({}, {}, {}, {})'.format(new_id, work_file, converter, async))
            result = converters.pdf(work_dir, work_file, converter)
            duration = time.time() - ts
            LOG.info('END : pdf({} {} sec): {}'.format(new_id, duration, result['status']))
            if result['output']:
                LOG.info('OUTPUT: pdf({}):\n{}'.format(new_id, result['output']))
            output = result['output']
            if result['status'] == 0: #OK
                pdf_data = open(result['filename'], 'rb').read()
                pdf_data = base64.encodestring(pdf_data)
                return dict(status='OK',
                            data=pdf_data,
                            output=output)
            else: # error
                return dict(status='ERROR',
                            output=output)


