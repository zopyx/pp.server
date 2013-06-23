################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX Ltd, Tuebingen, Germany
################################################################

""" 
Celery tasks 
"""

from celery import Celery
import converters

# Connector to Celery broker
celery = Celery('tasks', broker='sqla+sqlite:///celerydb.sqlite')

@celery.task
def unoconv(job_id, work_dir, input_filename, output_format):
    """ asyncronous Unoconv processing """
    return converters.unoconv(work_dir, input_filename, output_format)

@celery.task
def pdf(job_id, work_dir, work_file, converter):
    """ asyncronous PDF processing """
    return converters.pdf(work_dir, work_file, converter)
