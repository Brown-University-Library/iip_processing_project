# -*- coding: utf-8 -*-

""" Cleans up default rq failed-queue.
    Only cleans up jobs from a target queue.
    Useful for experimenting with rq & redis.
    """

import os, pprint
import redis, rq


QUEUE_NAME = os.environ['IIP_PRC__QUEUE_NAME']


failed_queue = rq.queue.get_failed_queue( connection=redis.Redis('localhost') )

d = { 'jobs': [] }
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
    job.delete()
d['initial_failed_target_count'] = failed_count

q2 = rq.Queue( QUEUE_NAME, connection=redis.Redis() )
d['current_failed_target_count'] = len(q2.jobs)

pprint.pprint( d )
