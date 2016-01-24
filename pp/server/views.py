################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX,  Tuebingen, Germany
################################################################

import os
import sys
import base64
import time
import uuid
import pkg_resources
import shutil
import tempfile
import zipfile
from pyramid.view import view_config

from pp.server.logger import LOG
from pp.server import converters
from pp.server import tasks
from pp.server import util


queue_dir = os.path.join(os.getcwd(), 'var', 'queue')
if not os.path.exists(queue_dir):
    os.makedirs(queue_dir)


QUEUE_CLEANUP_TIME = 24 * 60 * 60 # 1 day


class WebViews(object):

    def __init__(self, request):
        self.request = request

    def check_authentication(self):

        from pp.server import authorization
        from pyramid.httpexceptions import HTTPForbidden
        from pyramid.httpexceptions import HTTPInternalServerError

        authenticator = self.request.registry.settings.get('pp.authenticator')
        if not authenticator:
            return

        method = getattr(authorization, authenticator, None)
        if method is None:
            raise HTTPInternalServerError
        method(self.request)

    @view_config(route_name='home', renderer='index.pt', request_method='GET')
    def index(self):
        version = pkg_resources.require('pp.server')[0].version
        available_converters = sorted([k for k, v in self.available_converters().items() if v])
        return dict(version=version,
                    python_version=sys.version,
                    available_converters=available_converters
                    )

    @view_config(route_name='version', renderer='json', request_method='GET')
    def version(self):
        version = pkg_resources.require('pp.server')[0].version
        return dict(version=version, module='pp.server')

    @view_config(route_name='available_converters', renderer='json', request_method='GET')
    def available_converters(self):
        from pp.server.converters import princexml
        from pp.server.converters import pdfreactor
        from pp.server.converters import pdfreactor8
        from pp.server.converters import phantomjs
        from pp.server.converters import calibre
        from pp.server.converters import unoconv_bin
        from pp.server.converters import publisher
        from pp.server.converters import wkhtmltopdf
        from pp.server.converters import vivlio
        from pp.server.converters import antennahouse
        return dict(princexml=princexml is not None,
                    pdfreactor=pdfreactor is not None,
                    pdfreactor8=pdfreactor8 is not None,
                    phantomjs=phantomjs is not None,
                    calibre=calibre is not None,
                    unoconv=unoconv_bin is not None,
                    wkhtmltopdf=wkhtmltopdf is not None,
                    vivliostyle=vivlio is not None,
                    antennahouse=antennahouse is not None,
                    publisher=publisher is not None)

    @view_config(route_name='converter_versions', renderer='json', request_method='GET')
    def converter_versions(self):
        from pp.server.converters import princexml
        from pp.server.converters import pdfreactor
        from pp.server.converters import pdfreactor8
        from pp.server.converters import phantomjs
        from pp.server.converters import calibre
        from pp.server.converters import unoconv_bin
        from pp.server.converters import publisher
        from pp.server.converters import wkhtmltopdf
        from pp.server.converters import vivlio
        from pp.server.converters import antennahouse

        result = dict()

        if princexml:
            status, output = util.runcmd('{} --version'.format(princexml))
            result['princexml'] = output if status == 0 else 'n/a'

        if pdfreactor:
            status, output = util.runcmd('{} --version'.format(pdfreactor))
            result['pdfreactor'] = output if status == 1 else 'n/a'

        if pdfreactor8:
            status, output = util.runcmd('{} --version'.format(pdfreactor8))
            result['pdfreactor8'] = output if status == 1 else 'n/a'

        if wkhtmltopdf:
            status, output = util.runcmd('{} --version'.format(wkhtmltopdf))
            result['wkhtmltopdf'] = output if status == 0 else 'n/a'

        if calibre:
            status, output = util.runcmd('{} -convert --version'.format(calibre))
            result['calibre'] = output if status == 0 else 'n/a'

        if unoconv_bin:
            status, output = util.runcmd('{} --version'.format(unoconv_bin))
            result['unoconv'] = output if status == 0 else 'n/a'

        if vivlio:
            status, output = util.runcmd('{} --version'.format(vivlio))
            result['vivliostyle'] = output if status == 0 else 'n/a'

        if antennahouse:
            status, output = util.runcmd('{} -v'.format(antennahouse))
            result['vivliostyle'] = output if status == 0 else 'n/a'

        return result

    @view_config(route_name='cleanup', renderer='json', request_method='GET')
    def cleanup_queue(self):

        try:
            lc = self.request.registry.settings.last_cleanup
        except AttributeError:
            lc = time.time()
            pass

        now = time.time()
        if now - lc < QUEUE_CLEANUP_TIME:
            return
        removed = 0
        for dirname in os.listdir(queue_dir):
            fullname = os.path.join(queue_dir, dirname)
            mtime = os.path.getmtime(fullname)
            if now - mtime > QUEUE_CLEANUP_TIME:
                LOG.debug('Cleanup: {}'.format(fullname))
                shutil.rmtree(fullname)
                removed += 1
        self.request.registry.settings.last_cleanup = time.time()
        return dict(directories_removed=removed)

    @view_config(route_name='poll_api_1', renderer='json', request_method='GET')
    def poll(self):
        """ Poll status of a job by a given ``job_id``"""

        job_id = self.request.matchdict['jobid']
        out_directory = os.path.join(queue_dir, job_id, 'out')
        done_file = os.path.join(out_directory, 'done')
        if os.path.exists(done_file):
            files = [fname for fname in os.listdir(out_directory) if fname.startswith('out.')]
            if files:
                bin_data = base64.encodestring(open(os.path.join(out_directory, files[0]), 'rb').read())
                bin_data = bin_data.decode('ascii')
                output_data = open(os.path.join(out_directory, 'output.txt'), 'r').read()
                return dict(done=True,
                            status=0,
                            data=bin_data,
                            output=output_data)
            else:
                output_data = open(os.path.join(out_directory, 'output.txt'), 'r').read()
                return dict(done=True,
                            status=-1,
                            output=output_data)
        return dict(done=False)


    @view_config(route_name='unoconv_api_1', request_method='POST', renderer='json')
    def unoconv(self):
        """ Convert office formats using ``unoconv`` """

        self.check_authentication()
        self.cleanup_queue()

        params = self.request.params
        input_filename = params['filename']
        input_data = params['file'].file.read()
        output_format = params.get('output_format', 'pdf')
        cmd_options = params.get('cmd_options', '')
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
            result = converters.unoconv(work_dir, work_file, output_format, cmd_options)
            duration = time.time() - ts
            LOG.info('END : unoconv({} {} sec): {}'.format(new_id, duration, result['status']))
            if result['output']:
                LOG.info('OUTPUT: unoconv({}):\n{}'.format(new_id, result['output']))
            if result['status'] == 0: #OK
                out_directory = result['out_directory']
                zip_name = tempfile.mktemp()
                zip_out = zipfile.ZipFile(zip_name, 'w')
                for fn in os.listdir(out_directory):
                    if fn in ('done', 'output.txt'):
                        continue
                    zip_out.write(os.path.join(out_directory, fn), fn)
                zip_out.close()
                bin_data = base64.encodestring(open(zip_name, 'rb').read())
                os.unlink(zip_name)
                return dict(status='OK',
                            data=bin_data,
                            output=result['output'])
            else: # error
                return dict(status='ERROR',
                            output=result['output'])

    @view_config(route_name='pdf_api_1', request_method='POST', renderer='json')
    def pdf(self):

        self.check_authentication()
        self.cleanup_queue()

        params = self.request.params
        zip_data = params['file'].file.read()
        async = int(params.get('async', '0'))
        converter = params.get('converter', 'princexml')
        cmd_options = params.get('cmd_options', '')

        new_id = str(uuid.uuid4())
        work_dir = os.path.join(queue_dir, new_id)
        out_dir = os.path.join(work_dir, 'out')
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
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
            result = converters.pdf(work_dir, work_file, converter, cmd_options)
            duration = time.time() - ts
            LOG.info('END : pdf({} {} sec): {}'.format(new_id, duration, result['status']))
            if result['output']:
                LOG.info('OUTPUT: pdf({}):\n{}'.format(new_id, result['output']))
            output = result['output']
            if result['status'] == 0: #OK
                pdf_data = open(result['filename'], 'rb').read()
                pdf_data = base64.encodestring(pdf_data).decode('ascii')
                return dict(status='OK',
                            data=pdf_data,
                            output=output)
            else: # error
                return dict(status='ERROR',
                            output=output)
