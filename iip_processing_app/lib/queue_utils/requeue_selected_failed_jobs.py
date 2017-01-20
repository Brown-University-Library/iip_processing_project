# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os, sys
import redis, rq


QUEUE_NAME = unicode( os.environ['IIP_PRC__QUEUE_NAME'] )


failed_queue = rq.queue.get_failed_queue( connection=redis.Redis(u'localhost') )

for job in failed_queue.jobs:
    if not job.origin == QUEUE_NAME:
        print( u'skipping non-iip function call: %s' % job.func_name )
        continue
    else:
        print( u'function call: %s' % job.func_name )
        action_val = raw_input( u'Action (use first lowercase letter from the following, default is nothing): [Nothing/Requeue/Delete] ' )
        if action_val.lower() == u'r':
            print('requeuing job...')
            failed_queue.requeue( job.id )
        elif action_val.lower() == 'd':
            print('deleting job...')
            failed_queue.remove( job.id )
        else:
            print('skipping job...')
            pass

sys.exit()
