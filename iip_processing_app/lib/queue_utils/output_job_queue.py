"""
Usage: % python3 ./iip_processing_app/lib/queue_utils/output_job_queue.py
"""

import os, pprint
import redis, rq


QUEUE_NAME = os.environ['IIP_PRC__QUEUE_NAME']


q = rq.Queue( QUEUE_NAME, connection=redis.Redis() )

print( f'- initial number of jobs in queue ``{QUEUE_NAME}``: ``{len(q.jobs)}``' )

for job in q.jobs:
    job_d = {
        '_args': job._args,
        '_kwargs': job._kwargs,
        '_func_name': job._func_name,
        'description': job.description,
        'dt_created': job.created_at,
        'dt_enqueued': job.enqueued_at,
        'dt_ended': job.ended_at,
        'origin': job.origin,
        'id': job._id,
        'traceback': job.exc_info,
        'meta': job.meta,
        '_result': job._result,
        '_status': job._status,
    }
    print( '- job info...' )
    pprint.pprint( job_d )
    print( '---' )
