# -*- coding: utf-8 -*-

"""
Triggered by:
-  views.gh_inscription_watcher() -> GHHelper.handle_inscription_update()
Contains:
- Puller(), to call git-pull.
- StatusBackupper(), to make and save the local and gist backups.
- Prepper(), to prepare the data to be posted to solr.
- Indexer(), to send updates and deletions to solr.
- job-queue caller functions.
"""

import datetime, json, logging, logging.config, os, pprint, time
import envoy, redis, requests, rq, solr
from lxml import etree


log = logging.getLogger(__name__)
if not logging._handlers:  # true when module accessed by queue-jobs
    worker_config_dct = json.loads( os.environ['IIP_PRC__JOB_LOG_CONFIG_JSON'] )
    worker_config_dct['loggers']['iip_processing_app']['level'] = os.environ[u'IIP_PRC__LOG_LEVEL']
    logging.config.dictConfig( worker_config_dct )


class Puller( object ):
    """ Contains funcions for executing git-pull. """

    def __init__( self ):
        """ Settings. """
        self.GIT_CLONED_DIR_PATH = os.environ['IIP_PRC__CLONED_INSCRIPTIONS_PATH']

    # def call_git_pull( self ):
    #     """ Runs git_pull.
    #             Returns list of filenames.
    #         Called by run_call_git_pull(). """
    #     log.debug( 'starting call_git_pull()' )
    #     original_directory = os.getcwd()
    #     log.debug( 'original_directory, ```{}```'.format(original_directory) )
    #     os.chdir( self.GIT_CLONED_DIR_PATH )
    #     log.debug( 'temp directory, ```{}```'.format(os.getcwd()) )
    #     command = 'git pull'
    #     r = envoy.run( command.encode('utf-8') )  # envoy requires strings
    #     track_dct = self.track_envoy_call( r )
    #     os.chdir( original_directory )
    #     log.debug( 'directory after change-back, ```{}```'.format(os.getcwd()) )
    #     return track_dct['status_code']

    def call_git_pull( self ):
        """ Runs git_pull.
                Returns list of filenames.
            Called by run_call_git_pull(). """
        log.debug( 'starting call_git_pull()' )
        original_directory = os.getcwd()
        log.debug( f'original_directory, ``{original_directory}``' )
        os.chdir( self.GIT_CLONED_DIR_PATH )
        log.debug( f'temp directory, ``{os.getcwd()}``' )
        command = 'git pull'
        # r = envoy.run( command.encode('utf-8') )  # envoy requires bytes
        r = envoy.run( command )
        track_dct = self.track_envoy_call( r )
        os.chdir( original_directory )
        log.debug( 'directory after change-back, ```{}```'.format(os.getcwd()) )
        return track_dct['status_code']

    def track_envoy_call( self, envoy_response ):
        """ Creates dct convenient for logging and status_code access.
            Called by call_git_pull() """
        track_dct = {
            'status_code': envoy_response.status_code,  # int
            'std_out': envoy_response.std_out,
            'std_err': envoy_response.std_err,
            'command': envoy_response.command,          # list
            'history': envoy_response.history           # list
        }
        log.debug( 'envoy response, ```{}```'.format(pprint.pformat(track_dct)) )
        return track_dct

    ## end class Puller()


class StatusBackupper( object ):
    """ Manages creation and storage of json file of backup statuses.
        Note that backup statuses are returned, and used in indexing. """

    def __init__( self ):
        """ Settings. """
        self.SOLR_URL = os.environ['IIP_PRC__SOLR_URL']
        self.DISPLAY_STATUSES_BACKUP_DIR = os.environ['IIP_PRC__DISPLAY_STATUSES_BACKUP_DIR']
        self.STATUSES_GIST_URL = os.environ['IIP_PRC__STATUSES_GIST_URL']
        self.STATUSES_GIST_USERNAME = os.environ['IIP_PRC__STATUSES_GIST_USERNAME']
        self.STATUSES_GIST_PASSWORD = os.environ['IIP_PRC__STATUSES_GIST_PASSWORD']
        self.DISPLAY_STATUSES_BACKUP_TIMEFRAME_IN_DAYS = int( os.environ['IIP_PRC__DISPLAY_STATUSES_BACKUP_TIMEFRAME_IN_DAYS'] )

    def make_backup( self ):
        """ Manages the backup process.
            Called by run_backup_statuses(). """
        log.debug( 'starting backup' )
        response_dct = self.query_solr()
        status_dct = self.make_status_dct( response_dct )
        status_json = json.dumps( status_dct, sort_keys=True, indent=2 )
        try:
            self.update_github( status_json )
        except:
            log.exception( 'problem updating github; traceback follows; processing will continue' )
        self.save_locally( status_json )
        self.delete_old_backups()
        return status_json

    def query_solr( self ):
        """ Queries solr for current display-statuses and returns dct.
            Called by make_backup(). """
        url = '{}/select?q=*:*&rows=6000&fl=inscription_id,display_status&wt=json&indent=true'.format( self.SOLR_URL )
        log.debug( 'url, ```{}```'.format(url) )
        r = requests.get( url )
        response_dct = json.loads( r.content )
        log.debug( 'response_dct, ```{}```'.format(pprint.pformat(response_dct)) )
        return response_dct

    def make_status_dct( self, response_dct ):
        """ Simplifies hash; returns dct.
            Called by make_backup(). """
        status_dct = {
            'counts': { 'approved': 0, 'to_approve': 0, 'to_correct': 0, 'total': 0 },
            'statuses': {}
        }
        status_dct = self.run_loop( response_dct, status_dct )
        log.debug( 'status_dct, ```{}```'.format(pprint.pformat(status_dct)) )
        return status_dct

    def run_loop( self, response_dct, status_dct ):
        """ Updates status_dct from response_dct.
            Called by make_status_json() """
        for entry in response_dct['response']['docs']:
            status_dct['statuses'][ entry['inscription_id'] ] = entry['display_status']
            status_dct['counts']['total'] += 1
            if entry['display_status'] == 'approved':
                status_dct['counts']['approved'] += 1
            elif entry['display_status'] == 'to_approve':
                status_dct['counts']['to_approve'] += 1
            elif entry['display_status'] == 'to_correct':
                status_dct['counts']['to_correct'] += 1
        return status_dct

    def update_github( self, status_json ):
        """ Saves statuses to gist.
            Called by make_backup(). """
        log.debug( 'starting gist update' )
        auth = requests.auth.HTTPBasicAuth( self.STATUSES_GIST_USERNAME, self.STATUSES_GIST_PASSWORD )
        json_payload = json.dumps( {
            'description': '{} -- iip display statuses'.format(str(datetime.datetime.now())),
            'files': {
                'iip_display_statuses.json': { 'content': status_json },
            }
        } )
        r = requests.patch( url=self.STATUSES_GIST_URL, auth=auth, data=json_payload )
        log.debug( 'patch result, `%s`' % r.status_code )
        return

    def save_locally( self, status_json ):
        """ Saves data locally.
            Called by make_backup().
            TODO: eventually commit status_json to a repo, and push to github, streamlining local and external backup. """
        log.debug( 'starting local save' )
        # filename = 'display_statuses_backup_{}.json'.format( unicode(datetime.datetime.now()) ).replace( ' ', '_' )
        filename = 'display_statuses_backup_{}.json'.format( str(datetime.datetime.now()) ).replace( ' ', '_' )
        filepath = '{dir}/{fname}'.format( dir=self.DISPLAY_STATUSES_BACKUP_DIR, fname=filename )
        log.debug( 'filepath, ```{}```'.format(filepath) )
        with open( filepath, 'w' ) as f:
            f.write( status_json )
        return

    def delete_old_backups( self ):
        """ Deletes old backup display status files.
            Called by make_backup() """
        log.debug( 'starting old-backup deletion' )
        now = time.time()
        seconds_in_day = 60 * 60 * 24
        timeframe_days = seconds_in_day * self.DISPLAY_STATUSES_BACKUP_TIMEFRAME_IN_DAYS
        backup_files = os.listdir( self.DISPLAY_STATUSES_BACKUP_DIR )
        backup_files = [ x for x in backup_files ]
        for backup_filename in backup_files:
            backup_filepath = '{dir}/{fname}'.format( dir=self.DISPLAY_STATUSES_BACKUP_DIR, fname=backup_filename )
            if os.stat( backup_filepath ).st_mtime < (now - timeframe_days):
                os.remove( backup_filepath )
        return

    ## end class StatusBackupper()


class Prepper( object ):
    """ Manages prep for solr post. """

    def __init__( self ):
        self.XML_DIR = os.environ['IIP_PRC__CLONED_INSCRIPTIONS_PATH']
        self.STYLESHEET_PATH = os.environ['IIP_PRC__SOLR_DOC_STYLESHEET_PATH']
        self.TRANSFORMER_URL = os.environ['IIP_PRC__TRANSFORMER_URL']
        self.TRANSFORMER_AUTH_KEY = os.environ['IIP_PRC__TRANSFORMER_AUTH_KEY']

    def make_solr_data( self, file_id, status_json ):
        """ Manages preparation of solr data.
            Called by run_prep_file() """
        display_status = self.determine_display_status( file_id, status_json )
        source_xml = self.grab_inscription( file_id )
        initial_solr_doc = self.make_initial_solr_doc( source_xml )
        statused_solr_doc = self.update_status( display_status, initial_solr_doc )
        process_status_updater.update_single_status( inscription_id=file_id, status='data-prepared', status_detail='' )
        return statused_solr_doc

    def determine_display_status( self, file_id, status_json ):
        """ Returns display_status
            Called by make_solr_data() """
        status_dct = json.loads( status_json )
        if file_id in status_dct['statuses'].keys():
            display_status = status_dct['statuses'][file_id]
        else:
            display_status = 'to_approve'
        log.debug( 'display_status, `{}`'.format(display_status) )
        return display_status

    def grab_inscription( self, file_id ):
        """ Returns inscription xml.
            Called by make_solr_data() """
        filepath = '{dir}/epidoc-files/{file_id}.xml'.format( dir=self.XML_DIR, file_id=file_id )
        with open( filepath ) as f:
            xml_utf8 = f.read()
        xml = xml_utf8.decode( 'utf-8' )
        log.debug( 'source_xml, ```{}```'.format(xml) )
        return xml

    # def make_initial_solr_doc( self, source_xml ):
    #     """ Returns result of xsl transform.
    #         Called by make_solr_data() """
    #     log.debug( 'stylesheet_path, ```{}```'.format(self.STYLESHEET_PATH) )
    #     log.debug( 'transformer url, ```{}```'.format(self.TRANSFORMER_URL) )
    #     try:
    #         with open( self.STYLESHEET_PATH ) as f:
    #             stylesheet_utf8 = f.read()
    #         stylesheet = stylesheet_utf8.decode( 'utf-8' )
    #         payload = {
    #             'xml': source_xml, 'xsl': stylesheet, 'auth_key': self.TRANSFORMER_AUTH_KEY }
    #         r = requests.post( self.TRANSFORMER_URL, data=payload )
    #         transformed_xml = r.content.decode( 'utf-8' )
    #     except Exception as e:
    #         message = 'exception making initial_solr_doc, ```%s```' % e
    #         log.error( message )
    #         raise Exception( message )
    #     log.debug( 'transformed_xml, ```{}```'.format(transformed_xml) )
    #     return transformed_xml

    def make_initial_solr_doc( self, source_xml ):
        """ Returns result of xsl transform.
            Called by make_solr_data() """
        assert type(source_xml) == str, type(source_xml)
        log.debug( f'stylesheet_path, ``{self.STYLESHEET_PATH}``' )
        log.debug( f'transformer url, ``{self.TRANSFORMER_URL}``' )
        try:
            stylesheet = ''
            with open( self.STYLESHEET_PATH ) as f:
                stylesheet = f.read()
            payload = {
                'xml': source_xml, 'xsl': stylesheet, 'auth_key': self.TRANSFORMER_AUTH_KEY }
            r = requests.post( self.TRANSFORMER_URL, data=payload )
            transformed_xml = r.content.decode( 'utf-8' )
        except Exception as e:
            message = 'exception making initial_solr_doc, ``%s``' % repr(e)
            log.exception( message )
            raise Exception( message )
        log.debug( f'transformed_xml, ``{transformed_xml}``' )
        return transformed_xml

    def update_status( self, display_status, initial_solr_xml ):
        """ Updates initial solr-xml with display-status.
            Called by make_solr_data() """
        doc = etree.fromstring( initial_solr_xml.encode('utf-8') )  # can't take unicode string due to xml file's encoding declaration
        node = doc.xpath( '//doc' )[0]
        new_field = etree.SubElement( node, 'field' )
        new_field.attrib['name'] = 'display_status'
        new_field.text = display_status
        utf8_xml = etree.tostring( doc, encoding='UTF-8', xml_declaration=True, pretty_print=False )
        statused_xml = utf8_xml.decode( 'utf-8' )
        log.debug( 'statused_xml, ```{}```'.format(statused_xml) )
        return statused_xml

    ## end class Prepper()


class Indexer( object ):
    """ Manages solr calls. """

    def __init__( self ):
        self.SOLR_URL = os.environ['IIP_PRC__SOLR_URL']

    def update_entry( self, inscription_id, solr_xml ):
        """ Posts xml to solr.
            Called by run_update_index_file() """
        update_url = '{}/update/?commit=true'.format( self.SOLR_URL )
        log.debug( 'solr update url, ```{}```'.format(update_url) )
        headers = { 'content-type'.encode('utf-8'): 'text/xml; charset=utf-8'.encode('utf-8') }  # from testing, NON-unicode-string posts were bullet-proof
        r = requests.post(
            update_url.encode(u'utf-8'), headers=headers, data=solr_xml.encode('utf-8') )
        result_dct = {
            'response_status_code': r.status_code, 'response_text': r.content.decode('utf-8') }
        log.debug( 'solr response result_dct, ```{}```'.format(pprint.pformat(result_dct)) )
        process_status_updater.update_single_status( inscription_id=inscription_id, status='update-processed', status_detail=result_dct )
        return

    def delete_entry( self, file_id ):
        """ Deletes solr entry.
            Called by run_remove_index_file(() """
        log.debug( 'file_id, `{}`'.format(file_id) )
        s = solr.Solr( self.SOLR_URL )
        response = s.delete( file_id )
        s.commit()
        s.close()
        log.debug( 'deletion-post complete; response, ```{}```'.format(response) )
        process_status_updater.update_single_status( inscription_id=file_id, status='deletion-processed', status_detail=response )
        return

    ## end class Indexer()


class ProcessStatusUpdater( object ):
    """ Manages update of status table. """

    def __init__( self ):
        self.PROCESS_STATUS_UPDATER_URL = os.environ['IIP_PRC__PROCESS_STATUS_UPDATER_URL']

    def make_status_enqueued( self, to_process_dct ):
        """ Sends all to-process data to processing-status listener.
            Called by run_call_git_pull() """
        log.debug( 'url, ```{}```'.format(self.PROCESS_STATUS_UPDATER_URL) )
        payload = {
            'to_process_dct': to_process_dct }
        log.debug( 'payload, ```{}```'.format(pprint.pformat(payload)) )
        r = requests.post( self.PROCESS_STATUS_UPDATER_URL, data=json.dumps(payload) )
        # log.debug( 'post-content, ```{}```'.format(r.content.decode('utf-8')) )
        log.debug( 'post-status_code, ```{}```'.format(r.status_code) )
        return

    def update_single_status( self, inscription_id, status, status_detail='' ):
        """ Updates status.
            Called when job is completed, by Indexer.indexer.update_entry()
            Eventually can be updated along the way. """
        log.debug( 'url, ```{}```'.format(self.PROCESS_STATUS_UPDATER_URL) )
        payload = {
            'inscription_id': inscription_id, 'status_summary': status, 'status_detail': status_detail }
        log.debug( 'payload, ```{}```'.format(pprint.pformat(payload)) )
        r = requests.post( self.PROCESS_STATUS_UPDATER_URL, data=json.dumps(payload) )
        log.debug( 'post-result, ```{}```'.format(r.status_code) )
        return

    ## end class ProcessStatusUpdater()


## runners ##

q = rq.Queue( u'iip_prc', connection=redis.Redis() )
puller = Puller()
backupper = StatusBackupper()
prepper = Prepper()
indexer = Indexer()
process_status_updater = ProcessStatusUpdater()


def run_call_git_pull( to_process_dct ):
    """ Initiates a git pull update.
            Eventually spawns a call to indexer.run_update_index() which handles each result found.
        Called by github_helper.GHHelper.handle_inscription_update(). """
    log.debug( 'to_process_dct, ```{}```'.format(pprint.pformat(to_process_dct)) )  # keys: [ 'files_removed', 'files_updated', 'timestamp']
    time.sleep( 2 )  # let any existing in-process pull finish
    puller.call_git_pull()
    if to_process_dct['files_updated'] or to_process_dct['files_removed']:
        log.debug( 'about to enqueue job, passing in `to_process_dct`' )
        q.enqueue_call(
            func=u'iip_processing_app.lib.processor.run_update_process_tracker',
            kwargs={'to_process_dct': to_process_dct} )
    else:
        log.debug( 'no files to update; done' )
    return


def run_update_process_tracker( to_process_dct ):
    """ Updates the process-tracker table with enqueued status.
        Called by run_call_git_pull(). """
    process_status_updater.make_status_enqueued( to_process_dct )
    q.enqueue_call(
        func=u'iip_processing_app.lib.processor.run_backup_statuses',
        kwargs={u'files_to_update': to_process_dct['files_updated'], u'files_to_remove': to_process_dct['files_removed']} )
    return


# def run_backup_statuses( files_to_update, files_to_remove ):
#     """ Backs up statuses.
#         Called by run_call_git_pull()
#         Note: Files to remove will be enqueued first.
#               This will properly handle a file that is removed, then re-added. """
#     log.debug( 'starting run_backup_statuses()' )
#     try:
#         status_json = backupper.make_backup()
#         log.debug( 'status_json, ``%s``' % status_json )
#     except:
#         log.exception( 'problem making `status_json`' )
#     for file_to_remove in files_to_remove:
#         q.enqueue_call(
#             func='iip_processing_app.lib.processor.run_remove_index_file',
#             kwargs={'file_id': file_to_remove} )
#     log.debug( 'all files_to_remove enqueued' )
#     for file_to_update in files_to_update:
#         log.debug( 'processing file_to_update, ``%s``' % file_to_update )
#         q.enqueue_call(
#             func='iip_processing_app.lib.processor.run_prep_file',
#             kwargs={'file_id': file_to_update, 'status_json': status_json} )
#     log.debug( 'all files_to_update enqueued' )
#     return


# def run_backup_statuses( files_to_update, files_to_remove ):
#     """ Backs up statuses.
#         Called by run_call_git_pull()
#         Note: Files to remove will be enqueued first.
#               This will properly handle a file that is removed, then re-added. """
#     log.debug( 'starting run_backup_statuses()' )
#     try:
#         status_json = backupper.make_backup()
#         log.debug( 'original_status_json, ``%s``' % status_json )
#         # log.debug( 'original status_json, ``%s``' % status_json )
#         # temp_status_dct = json.loads( status_json )
#         # temp_status_dct['statuses'] = { 'abur0001': 'approved' }
#         # status_json = json.dumps( temp_status_dct, sort_keys=True, indent=2 )
#         # log.debug( 'updated status_json, ``%s``' % status_json )
#     except:
#         log.exception( 'problem making `status_json`' )
#     for file_to_remove in files_to_remove:
#         q.enqueue_call(
#             func='iip_processing_app.lib.processor.run_remove_index_file',
#             kwargs={'file_id': file_to_remove} )
#     log.debug( 'all files_to_remove enqueued' )
#     for file_to_update in files_to_update:
#         log.debug( 'processing file_to_update, ``%s``' % file_to_update )
#         """ Temporary hack-fix to prevent problem of big 'status_json' causing error. """
#         temp_status_dct = json.loads( status_json )
#         status = temp_status_dct['statuses'][file_to_update]
#         temp_status_dct['statuses'] = { file_to_update : status }
#         temp_status_json = json.dumps( temp_status_dct, sort_keys=True, indent=2 )
#         log.debug( 'updated status_json, ``%s``' % temp_status_json )
#         q.enqueue_call(
#             func='iip_processing_app.lib.processor.run_prep_file',
#             kwargs={'file_id': file_to_update, 'status_json': temp_status_json} )
#             # kwargs={'file_id': file_to_update, 'status_json': status_json} )
#     log.debug( 'all files_to_update enqueued' )
#     return


def run_backup_statuses( files_to_update, files_to_remove ):
    """ Backs up statuses.
        Called by run_call_git_pull()
        Note: Files to remove will be enqueued first.
              This will properly handle a file that is removed, then re-added. """
    log.debug( 'starting run_backup_statuses()' )
    try:
        status_json = backupper.make_backup()  # includes all statuses of all known files
        log.debug( 'original_status_json, ``%s``' % status_json )
    except:
        log.exception( 'problem making `status_json`' )
    for file_to_remove in files_to_remove:
        q.enqueue_call(
            func='iip_processing_app.lib.processor.run_remove_index_file',
            kwargs={'file_id': file_to_remove} )
    log.debug( 'all files_to_remove enqueued' )
    for file_to_update in files_to_update:
        log.debug( 'processing file_to_update, ``%s``' % file_to_update )
        """ Hack-fix to prevent problem of big 'status_json' causing error. """
        status = prepper.determine_display_status( file_to_update, status_json )  # normally called by Prepper.make_solr_data(), but I need it here because I'm sending a subset (only the relevant status) of all the statuses to the queue.
        temp_status_dct = json.loads( status_json )
        temp_status_dct['statuses'] = { file_to_update : status }
        temp_status_json = json.dumps( temp_status_dct, sort_keys=True, indent=2 )
        log.debug( 'updated status_json, ``%s``' % temp_status_json )
        q.enqueue_call(
            func='iip_processing_app.lib.processor.run_prep_file',
            kwargs={'file_id': file_to_update, 'status_json': temp_status_json} )
            # kwargs={'file_id': file_to_update, 'status_json': status_json} )
    log.debug( 'all files_to_update enqueued' )
    return


def run_remove_index_file( file_id ):
    """ Removes file from index.
        Called by run_backup_statuses() """
    log.debug( 'file_id, ```{}```'.format(file_id) )
    indexer.delete_entry( file_id )
    log.debug( 'done processing file' )


def run_prep_file( file_id, status_json ):
    """ Prepares file for indexing.
        Called by run_backup_statuses() """
    log.debug( 'file_id, ```{}```'.format(file_id) )
    solr_xml = prepper.make_solr_data( file_id, status_json )
    log.debug( 'enqueuing next job' )
    q.enqueue_call(
        func='iip_processing_app.lib.processor.run_update_index_file',
        kwargs={'inscription_id': file_id, 'solr_xml': solr_xml} )


def run_update_index_file( inscription_id, solr_xml ):
    """ Updates index with new or changed info.
        Called by run_prep_file() """
    log.debug( 'partial solr_xml, ```{}```'.format(solr_xml[0:100]) )
    indexer.update_entry( inscription_id, solr_xml )
    log.debug( 'done processing file' )
