
import os
import json
import uuid
import pprint
import pymongo
from bson.son import SON
from webob import Response
from datetime import datetime
from pyramid.view import view_config

queue_dir = os.path.join(os.getcwd(), 'var', 'queue')
if not os.path.exists(queue_dir):
    os.makedirs(queue_dir)

conn = pymongo.MongoClient()
db = conn['pp']
jobs = db.jobs
jobs.create_index([('status', pymongo.ASCENDING)])

STATUS = [
    'CREATED', 
    'PREPARE-RUNNING', 
    'PREPARE-DONE', 
    'PREPARE-ERROR', 
    'PDF-CONVERSION-RUNNING', 
    'PDF-CONVERSION-DONE', 
    'PDF-CONVERSION-ERROR',
    'SEND-PDF-RUNNING',
    'SEND-PDF-DONE',
    'SEND-PDF-ERROR',
]

class View(object):

    def __init__(self, request):
        self.request = request

    def cr2br(self, text):
        if isinstance(text, basestring):
            return text.replace('\n', '<br/>')
        return text

    @view_config(route_name='home', renderer='index.pt', request_method='GET')
    def index(self):
        return {}

    @view_config(name='stats', renderer='json', request_method='GET')
    def stats(self):
        result = dict()
        for status in STATUS:
            result[status] = jobs.find({'status' : status}).count()        
        return result

    @view_config(name='stats-html', renderer='stats.pt', request_method='GET')
    def stats_html(self):
        return dict(keys=STATUS, stats=self.stats())

    @view_config(route_name='job_status', renderer='json', request_method='GET')
    def job_status(self):
        job_id = self.request.matchdict['job_id']
        job =  jobs.find_one({'_id' : job_id})
        if not job:
            return None
        del job['_id']
        del job['created']

        dirname = job['directory']
        if os.path.exists(os.path.join(dirname, 'out.pdf.log')):
            job['pdf_log'] = open(os.path.join(dirname, 'out.pdf.log')).read()
        if os.path.exists(os.path.join(dirname, 'prepare.log')):
            job['prepare_log'] = open(os.path.join(dirname, 'prepare.log')).read()
        return job

    @view_config(route_name='job_status_html', renderer='job_status.pt', request_method='GET')
    def job_status_html(self):
        return dict(job=self.job_status())

    def error_response(msg):
        response = Response()
        response.status = 400 
        response.body = msg
        return response

    @view_config(name='new-conversion', request_method='POST', renderer='json')
    def new_conversion(self):

        # parameter parsing
        body = json.loads(self.request.body)

        pdf_resolution = body.get('pdf_resolution')
        if not pdf_resolution :
            return error_response('Missing parameter: pdf_resolution')
        if pdf_resolution not in ('low', 'high'):
            return error_response('Invalid parameter: pdf_resolution must be either "high" or "low"')

        callback_url = body.get('callback_url')
        if not callback_url:
            return error_response('Missing parameter: callback_url')

        quality = int(body.get('quality', '100'))
        max_size = body.get('max_size')

        # store input
        job_id = str(uuid.uuid1())
        os.makedirs(os.path.join(queue_dir, job_id))
        index_html = os.path.join(queue_dir, job_id, 'index.html')
        open(index_html, 'wb').write(body['html'])

        # save job data in MongoDB
        job = dict(_id=str(uuid.uuid1()),
                   filename=index_html,
                   directory=os.path.join(queue_dir, job_id),
                   created=datetime.utcnow(),
                   pdf_resolution=pdf_resolution,
                   callback_url=callback_url,
                   quality=quality,
                   max_size=max_size,
                   tries_prepare=0,
                   tries_pdf=0,
                   tries_pdf_send=0,
                   job_id=job_id,
                   tries=0,
                   status='CREATED')
        jobs.save(job)

        # Queue request in Celery
        import tasks
        tasks.html_prepare.delay(job['_id'])

        # Return JSON result 
        return dict(status='OK',
                    id=job_id,
                    message='Input file queued for conversion')
