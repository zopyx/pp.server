import os
import plac
import time
import pymongo
from pdfreactor.html_prepare import html_prepare
import multiprocessing


conn = pymongo.MongoClient()
db = conn['pp']
jobs = db.jobs


def setJobStatus(job, status):
    jobs.update({'_id' : job['_id']}, {'$set' : {'status' : status}})

def prepare(job):
    
    print 'got job', job['job_id'], job['status']
    setJobStatus(job, 'PREPARING')
    input_filename = job['filename']
    basename, ext = os.path.splitext(os.path.basename(input_filename))
    output_filename = os.path.join(os.path.dirname(input_filename), 'out_%s.html' % basename)
    base = 'file://%s' % os.path.dirname(input_filename)


    try:
        result = html_prepare(input_filename=input_filename, 
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
                              checks=True)
    except Exception as e:
        print e

    print 'done'
    P
    print result
    setJobStatus(job, 'PREPARED')
    print 'terminated', job['job_id']


def main():
    prepare_pool = multiprocessing.Pool(30)
    while 1:
        job = jobs.find_one({'status' : 'CREATED'})
        if job:
            print job['job_id'], job['status']
            prepare_pool.apply_async(prepare, [job])
        time.sleep(5)


if __name__ == '__main__':
    main()

