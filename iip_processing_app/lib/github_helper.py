# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import base64, datetime, json, logging, os, pprint
import requests
from django.http import HttpResponse
from iip_processing_app.lib import processor


log = logging.getLogger(__name__)


class GHValidator( object ):
    """ Contains functions to validate incoming request. """

    def __init__( self ):
        self.AUTH_USERNAME = unicode( os.environ['IIP_PRC__BASIC_AUTH_USERNAME'] )
        self.AUTH_PASSWORD = unicode( os.environ['IIP_PRC__BASIC_AUTH_PASSWORD'] )
        self.DEV_URL = unicode( os.environ['IIP_PRC__DEV_URL'] )
        self.PRODUCTION_HOSTNAME = unicode( os.environ['IIP_PRC__PRODUCTION_HOSTNAME'] )

    def parse_http_basic_auth( self, basic_auth_header_text ):
        """ Returns parsed username and password. """
        log.debug( 'starting parse_http_basic_auth()' )
        userpass_dct = { 'username': None, 'password': None }
        auth = basic_auth_header_text.split()
        if len(auth) == 2:
            if auth[0].lower() == 'basic':
                ( received_username, received_password ) = base64.b64decode( auth[1] ).split( ':' )
                userpass_dct = { 'received_username': received_username, 'received_password': received_password }
        return userpass_dct

    def validate_credentials( self, received_auth_dct ):
        """ Checks credentials. """
        return_val = False
        if received_auth_dct['received_username'] == self.AUTH_USERNAME and received_auth_dct['received_password'] == self.AUTH_PASSWORD:
            return_val = True
        log.debug( 'return_val, ```{}```'.format(return_val) )
        return return_val

    def make_unauthenticated_response( self ):
        """ Returns proper 401 response. """
        log.debug( 'preparing 401 response' )
        resp = HttpResponse( '401 / Not Authenticated' )
        resp.status_code = 401
        resp['WWW-Authenticate'] = 'Basic realm="iip_processor"'
        return resp

    ## end class GHValidator()


class GHHelper( object ):
    """ Contains support functions for views.git_watcher() """

    def __init__( self ):
        """ Grabs env-vars.
            Note: auth-username and auth-password no longer used for validation here, but still needed for dev pass-through. """
        self.AUTH_USERNAME = unicode( os.environ['IIP_PRC__BASIC_AUTH_USERNAME'] )
        self.AUTH_PASSWORD = unicode( os.environ['IIP_PRC__BASIC_AUTH_PASSWORD'] )
        self.DEV_URL = unicode( os.environ['IIP_PRC__DEV_URL'] )
        self.PRODUCTION_HOSTNAME = unicode( os.environ['IIP_PRC__PRODUCTION_HOSTNAME'] )

    # def parse_http_basic_auth( self, basic_auth_header_text ):
    #     """ Returns parsed username and password. """
    #     log.debug( 'starting parse_http_basic_auth()' )
    #     userpass_dct = { 'username': None, 'password': None }
    #     auth = basic_auth_header_text.split()
    #     if len(auth) == 2:
    #         if auth[0].lower() == 'basic':
    #             ( received_username, received_password ) = base64.b64decode( auth[1] ).split( ':' )
    #             userpass_dct = { 'received_username': received_username, 'received_password': received_password }
    #     return userpass_dct

    # def validate_credentials( self, received_auth_dct ):
    #     """ Checks credentials. """
    #     return_val = False
    #     if received_auth_dct['received_username'] == self.AUTH_USERNAME and received_auth_dct['received_password'] == self.AUTH_PASSWORD:
    #         return_val = True
    #     log.debug( 'return_val, ```{}```'.format(return_val) )
    #     return return_val

    # def make_unauthenticated_response( self ):
    #     """ Returns proper 401 response. """
    #     log.debug( 'preparing 401 response' )
    #     resp = HttpResponse( '401 / Not Authenticated' )
    #     resp.status_code = 401
    #     resp['WWW-Authenticate'] = 'Basic realm="iip_processor"'
    #     return resp

    def handle_inscription_update( self, request_body, host ):
        """ Enqueues first of a series of processing jobs. """
        log.debug( 'request_body, ```{}```'.format(request_body) )
        data_dct = json.loads( request_body )
        to_process_dct = self.prep_files_to_process( data_dct['commits'] )
        processor.run_call_git_pull( to_process_dct )
        self.trigger_dev_if_production( request_body, host )
        return

    def prep_files_to_process( self, commits_lst ):
        """ Prepares the data-dict to be sent to the first rq job.
            Called by handle_inscription_update() """
        files_to_process = { 'files_updated': [], 'files_removed': [], 'timestamp': unicode(datetime.datetime.now()) }
        ( added, modified, removed ) = self.examine_commits( commits_lst )
        files_to_process['files_updated'] = added
        files_to_process['files_updated'].extend( modified )  # solrization same for added or modified
        files_to_process['files_removed'] = removed
        log.debug( 'files_to_process, ```{}```'.format(pprint.pformat(files_to_process)) )
        return files_to_process

    def examine_commits( self, commits_lst ):
        """ Extracts and returns file-paths for the different kinds of commits.
            Called by prep_files_to_process(). """
        ( added, modified, removed ) = ( [], [], [] )
        for commit in commits_lst:
            added.extend( commit['added'] )
            modified.extend( commit['modified'] )
            removed.extend( commit['removed'] )
        cleaned_added = sorted( self.clean_list(added) )
        cleaned_modified = sorted( self.clean_list(modified) )
        cleaned_removed = sorted( self.clean_list(removed) )
        log.debug( 'cleaned_added, ```{add}```; cleaned_modified, ```{mod}```; cleaned_removed, ```{rem}```'.format(add=cleaned_added, mod=cleaned_modified, rem=cleaned_removed) )
        return ( cleaned_added, cleaned_modified, cleaned_removed )

    def clean_list( self, initial_list ):
        """ Ensures only inscriptions are returned, and that directory-string, and '.xml' are removed.
            Called by examine_commits() """
        log.debug( 'initial_list, ```{}```'.format(initial_list) )
        cleaned = []
        dir_segment = 'epidoc-files/'
        for entry in initial_list:
            if dir_segment in entry:  ## good inscription
                cleaned.append( entry.replace(dir_segment, '').replace('.xml', '') )
        log.debug( 'cleaned, ```{}```'.format(cleaned) )
        return cleaned

    def trigger_dev_if_production( self, request_body, host ):
        """ Sends github `data` to dev-server (which github can't hit) if this is the production-server.
            Called by handle_inscription_update() """
        log.debug( 'starting' )
        if host == self.PRODUCTION_HOSTNAME:
            log.debug( 'gonna hit dev' )
            try:
                r = requests.post( self.DEV_URL, data=request_body, auth=(self.AUTH_USERNAME, self.AUTH_PASSWORD), timeout=10 )
                log.debug( 'status_code, `{}`'.format(r.status_code) )
            except Exception as e:
                log.error( 'exception, ```{}```'.format(unicode(repr(e))) )
        log.debug( 'leaving' )
        return

    ## end class GHHelper()



