################################################################
# pp.server - Produce & Publish Server
# (C) 2013, ZOPYX,  Tuebingen, Germany
################################################################

"""
Celery tasks
"""

from celery import Celery, current_task
from pp.server import converters

# Connector to Celery broker
celery = Celery('tasks', broker='sqla+sqlite:///celerydb.sqlite')

@celery.task
def unoconv(job_id, work_dir, input_filename, output_format):
    """ asyncronous Unoconv processing """
    current_task.update_state(state='PROGRESS',
                              meta=dict(job_id=job_id, work_dir=work_dir))
    result = converters.unoconv(work_dir, input_filename, output_format, cmd_options='')
    if result['status'] == 0:
        current_task.update_state(state='OK', meta=result)
    else:
        current_task.update_state(state='ERROR', meta=result)
    return result

@celery.task
def pdf(job_id, work_dir, work_file, converter):
    """ asyncronous PDF processing """
    current_task.update_state(state='PROGRESS',
                              meta=dict(job_id=job_id, work_dir=work_dir))
    result = converters.pdf(work_dir, work_file, converter, cmd_options='')
    if result['status'] == 0:
        current_task.update_state(state='OK', meta=result)
    else:
        current_task.update_state(state='ERROR', meta=result)
    return result
