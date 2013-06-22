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

    result = converters.unoconv(input_filename, output_format)
    print result
    return result
