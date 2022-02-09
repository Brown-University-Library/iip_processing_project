# -*- coding: utf-8 -*-

import os, pprint
import redis, rq


QUEUE_NAME = os.environ['IIP_PRC__QUEUE_NAME']


failed_queue = rq.queue.get_failed_queue( connection=redis.Redis('localhost') )

d = { 'failed_target_count': None, 'jobs': [] }
failed_count = 0
for job in failed_queue.jobs:
    if not job.origin == QUEUE_NAME:
        continue
    failed_count += 1
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
    d['jobs'].append( job_d )
d['failed_target_count'] = failed_count
pprint.pprint( d )
