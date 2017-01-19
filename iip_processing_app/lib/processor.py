# -*- coding: utf-8 -*-

from __future__ import unicode_literals

"""
Contains:
- Puller() class, for running git-pull.
- A job-queue caller function.
"""

import datetime, json, logging, os, pprint, shutil, time
import envoy, redis, rq


log = logging.getLogger(__name__)


class Puller( object ):
    """ Contains funcions for executing git-pull. """

    def __init__( self ):
        """ Settings. """
        self.GIT_CLONED_DIR_PATH = unicode( os.environ['IIP_PRC__CLONED_INSCRIPTIONS_PATH'] )

    def call_git_pull( self ):
        """ Runs git_pull.
                Returns list of filenames.
            Called by run_call_git_pull(). """
        log.debug( 'starting call_git_pull()' )
        original_directory = os.getcwd()
        os.chdir( self.GIT_CLONED_DIR_PATH )
        command = 'git pull'
        r = envoy.run( command.encode('utf-8') )  # envoy requires strings
        self.track_envoy_call( r )
        os.chdir( original_directory )
        return

    def track_envoy_call( self, envoy_response ):
        """ Returns dct convenient for logging.
            Called by call_git_pull() """
        track_dct = {
            'status_code': envoy_response.status_code,  # int
            'std_out': envoy_response.std_out.decode(u'utf-8'),
            'std_err': envoy_response.std_err.decode(u'utf-8'),
            'command': envoy_response.command,  # list
            'history': envoy_response.history  # list
            }
        log.debug( 'envoy response, ```{}```'.format(pprint.pformat(track_dct)) )
        return

    ## end class Puller()


## runners ##

q = rq.Queue( u'iip_processing', connection=redis.Redis() )

def run_call_git_pull( to_process_dct ):
    """ Initiates a git pull update.
            Eventually spawns a call to indexer.run_update_index() which handles each result found.
        Triggered by views.gh_inscription_watcher(). """
    assert sorted( to_process_dct.keys() ) == [ 'files_removed', 'files_updated', 'timestamp']
    log.debug( 'to_process_dct, ```{}```'.format(pprint.pformat(to_process_dct)) )
    time.sleep( 2 )  # let any existing in-process pull finish
    puller = Puller()
    puller.call_git_pull()
    log.debug( 'enqueuing next job' )
    # q.enqueue_call(
    #     func=u'iip_processing_app.lib.processor.run_some_step',
    #     kwargs={u'files_to_update': files_to_update, u'files_to_remove': files_to_remove} )
    return
