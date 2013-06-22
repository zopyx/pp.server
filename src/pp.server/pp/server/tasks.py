""" 
Celery tasks 
"""


from celery import Celery
import converters

# Connector to local MongoDB database/queue
celery = Celery('tasks', broker='sqla+sqlite:///celerydb.sqlite')

@celery.task
def unoconv(job_id, work_dir, input_filename, output_format):
    """ asyncronous Unoconv processing """
    print 1
    return converters.unoconv(input_filename, output_format)

@celery.task
def pdf(job_id, work_dir, work_file, converter):
    """ asyncronous PDF processing """
    print 2
    return converters.pdf(work_dir, work_file, converter)
