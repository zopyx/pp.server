import os
import uuid
import requests
import pymongo
import subprocess
import tempfile
import commands
import pdfreactor.html_prepare
from celery import Celery

import logging

# Connector to local MongoDB database/queue
celery = Celery('tasks', broker='sqla+sqlite:///celerydb.sqlite')

# Timeouts and retries
MAX_TRIES_HTML_PREPARE = 3
RETRY_DELAY_HTML_PREPARE = 60 # seconds

MAX_TRIES_PDF_SEND = 3
RETRY_DELAY_PDF_SEND = 60 # seconds


# Logger stuff
LOG = logging.getLogger()

def log_info(job, msg):
    LOG.info('%s - %s' % (job['_id'], msg))

def log_error(job, msg):
    LOG.error('%s - %s' % (job['_id'], msg))

# helper methods for updating job information in MongoDB
def setJobStatus(job, status):
    """ Set the job status """
    jobs.update({'_id' : job['_id']}, {'$set' : {'status' : status}})

def incrementCounter(job, counter):
    """ Increment a tries counter """
    jobs.update({'_id' : job['_id']}, {'$inc' : {counter: 1}})


@celery.task
def html_prepare(job_id):
    """ Prepare HTML (fetching images from remote sources etc.) """

    job = jobs.find_one({'_id' : job_id})
    incrementCounter(job, 'tries_prepare')
    setJobStatus(job, 'PREPARE-RUNNING')

    input_filename = job['filename']
    basename, ext = os.path.splitext(os.path.basename(input_filename))
    output_filename = os.path.join(os.path.dirname(input_filename), 'out_%s.html' % basename)
#    base = 'file://%s' % os.path.dirname(input_filename)
    base = 'file:///Users/ajung/sandboxes/locandy/examples'

    try:
        result = pdfreactor.html_prepare.html_prepare(input_filename=input_filename, 
                              output_filename=output_filename, 
                              base=base,
                              quality='100',
                              border_effect=False,
                              max_size=None,
                              verbose=True, 
                              keep_images=False,
                              error_logfile=None, 
                              write_errorlog=True,
                              show_errorlog=True,
                              checks=False)

    except Exception, e:
        if job['tries_prepare'] >= MAX_TRIES_HTML_PREPARE: 
            # final failure
            setJobStatus(job, 'PREPARE-ERROR')
            raise RuntimeError('Maximum numbers of HTML prepare tries exceeded (%s)' % e)
        else:
            # retry after N seconds
            html_prepare.apply_async((job_id,), countdown=RETRY_DELAY_HTML_PREPARE)

    convert_pdf.delay(job['_id'])
    setJobStatus(job, 'PREPARE-DONE')

@celery.task
def convert_pdf(job_id):
    """ Convert prepared HTML file to PDF using PDFreactor"""

    job = jobs.find_one({'_id' : job_id})
    incrementCounter(job, 'tries_pdf')
    setJobStatus(job, 'PDF-CONVERSION-RUNNING')

    out_pdf = os.path.join(job['directory'], 'out.pdf')

    cmd = 'bin/pdfreactor -v debug "%s/out_index.html" "%s"' % (job['directory'], out_pdf)
    log_info(job, cmd)
    stdin = open('/dev/null')
    stdout = subprocess.PIPE
    stderr = subprocess.PIPE
    p = subprocess.Popen(cmd,
        shell=True,
        stdout=stdout,
        stderr=stderr,
    )

    status = p.wait()
    log_info(job, 'Exit code: %d' % status)
    stdout_ = p.stdout.read().strip()
    stderr_ = p.stderr.read().strip()

    # store PDF conversion log 
    open(out_pdf + '.log', 'w').write(stdout_ + stderr_)

    setJobStatus(job, 'foo')
    if os.path.exists(out_pdf) and os.stat(out_pdf).st_size > 0:
        setJobStatus(job, 'PDF-CONVERSION-DONE')
        send_pdf.delay(job['_id'])
    else:
        setJobStatus(job, 'PDF-CONVERSION-ERROR')
        raise RuntimeError('Error converting job %s' % job_id)

@celery.task
def send_pdf(job_id):
    """ POST converted PDF to callback URL """

    job = jobs.find_one({'_id' : job_id})
    incrementCounter(job, 'tries_pdf_send')
    setJobStatus(job, 'SEND-PDF-RUNNING')

    out_pdf = os.path.join(job['directory'], 'out.pdf')   
    log_info(job, 'Posting PDF %d/%d,  (%s)' % (job['tries_pdf_send']+1, MAX_TRIES_PDF_SEND, job['callback_url']))

    # HTTP post back to the caller
    r = requests.post(job['callback_url'], data=open(out_pdf, 'rb').read())

    if r.status_code == 200:
        # final success
        log_info(job, 'OK Posting PDF')
        setJobStatus(job, 'SEND-PDF-DONE')
        return

    log_info(job, 'FAILED Posting PDF for job (HTTP status %d) ' % r.status_code)
    if job['tries_pdf_send']+1 >= MAX_TRIES_PDF_SEND: 
        # final failure
        setJobStatus(job, 'SEND-PDF-ERROR')
        raise RuntimeError('Maximum numbers of PDF conversion tries exceeded')
    else:
        # retry after N seconds
        send_pdf.apply_async((job_id,), countdown=RETRY_DELAY_PDF_SEND)
