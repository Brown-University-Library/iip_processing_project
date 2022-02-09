# -*- coding: utf-8 -*-

import os, pprint
import redis, rq


QUEUE_NAME = os.environ['IIP_PRC__QUEUE_NAME']


q = rq.Queue( QUEUE_NAME, connection=redis.Redis() )

print '- initial number of jobs in queue `%s`: %s' % ( QUEUE_NAME, len(q.jobs) )

for job in q.jobs:
    job_d = {
        'args': job._args,
        'kwargs': job._kwargs,
        'function': job._func_name,
        'description': job.description,
        'dt_created': job.created_at,
        'dt_enqueued': job.enqueued_at,
        'dt_ended': job.ended_at,
        'origin': job.origin,
        'id': job._id,
        'traceback': job.exc_info
    }
    print '- job info...'; pprint.pprint( job_d )
    job.delete()
    print '- deleted.'
    print '---'

print '- current number of jobs in queue `%s`: %s' % ( QUEUE_NAME, len(q.jobs) )
