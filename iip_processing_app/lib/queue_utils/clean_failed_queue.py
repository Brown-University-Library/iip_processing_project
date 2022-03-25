# -*- coding: utf-8 -*-

""" Cleans up default rq failed-queue.
    Only cleans up jobs from a target queue.
    Useful for experimenting with rq & redis.
    """

import logging, os, pprint
import redis, rq


log = logging.getLogger(__name__)


try:

    QUEUE_NAME = os.environ['IIP_PRC__QUEUE_NAME']

    failed_queue = rq.queue.get_failed_queue( connection=redis.Redis('localhost') )

    output_dct: dict = {}
    failed_iip_count: int = 0
    failed_iip_jobs: list = []
    for job in failed_queue.jobs:
        if not job.origin == QUEUE_NAME:
            print( f'job.id, ``{job._id}`` not a failed iip job; skipping' )
            continue
        failed_iip_count += 1
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
        failed_iip_jobs.append( job_d )
        job.delete()
    output_dct['failed_iip_jobs'] = failed_iip_jobs
    output_dct['number_of_failed_iip_jobs_deleted'] = failed_iip_count
    output_dct['number_of_non_iip_failed_jobs'] = len( failed_queue.jobs ) - failed_iip_count

    # q2 = rq.Queue( QUEUE_NAME, connection=redis.Redis() )
    # d['current_failed_target_count'] = len(q2.jobs)

    pprint.pprint( output_dct )

except Exception as e:
    message = f'Exception cleaning failed queue, ``{repr(e)}``'
    print( message )
    log.exception( message )
