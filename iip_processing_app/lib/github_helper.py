# -*- coding: utf-8 -*-

import base64, datetime, hashlib, hmac, json, logging, os, pprint
import requests
from django.http import HttpResponse
from iip_processing_app.lib import processor


log = logging.getLogger(__name__)


class GHValidator( object ):
    """ Contains functions to validate incoming github request.
        Helper for views.gh_inscription_watcher() """

    def __init__( self ):
        self.AUTH_USERNAME = os.environ['IIP_PRC__BASIC_AUTH_USERNAME']
        self.AUTH_PASSWORD = os.environ['IIP_PRC__BASIC_AUTH_PASSWORD']
        self.DEV_URL = os.environ['IIP_PRC__DEV_URL']
        self.PRODUCTION_HOSTNAME = os.environ['IIP_PRC__PRODUCTION_HOSTNAME']
        self.SECRET = os.environ['IIP_PRC__REPO_SECRET_KEY']

    def validate_submission( self, submitted_basic_auth_info, submitted_signature, submitted_payload ):
        """ Manages validation.
            Called by views.gh_inscription_watcher() """
        validity = False
        received_username_password_dct = self.parse_http_basic_auth( submitted_basic_auth_info )
        if self.validate_credentials( received_username_password_dct ):
            calculated_signature = self.determine_signature( self.SECRET, submitted_payload )
            if calculated_signature == submitted_signature:
                validity = True
        log.debug( 'validity, `{}`'.format(validity) )
        return validity

    # def parse_http_basic_auth( self, basic_auth_header_text ):
    #     """ Returns parsed username and password.
    #         Called by views.gh_inscription_watcher() """
    #     log.debug( 'starting parse_http_basic_auth()' )
    #     userpass_dct = { 'username': None, 'password': None }
    #     auth = basic_auth_header_text.split()
    #     if len(auth) == 2:
    #         if auth[0].lower() == 'basic':
    #             ( received_username, received_password ) = base64.b64decode( auth[1] ).split( ':' )
    #             userpass_dct = { 'received_username': received_username, 'received_password': received_password }
    #     return userpass_dct

    def parse_http_basic_auth( self, basic_auth_header_text ):
        """ Returns parsed username and password.
            Called by views.gh_inscription_watcher() """
        log.debug( 'starting parse_http_basic_auth()' )
        assert type(basic_auth_header_text) == str, type(basic_auth_header_text)
        userpass_dct = { 'username': None, 'password': None }
        auth = basic_auth_header_text.split()
        assert type(auth) == list, type(auth)
        log.debug( f'auth, ``{auth}``')

        if len(auth) == 2:
            if auth[0].lower() == 'basic':
                userpass_utf8 = base64.b64decode( auth[1] )
                assert type(userpass_utf8) == bytes, type(userpass_utf8)
                userpass = userpass_utf8.decode( 'utf-8' )
                ( received_username, received_password ) = userpass.split( ':' )
                userpass_dct = { 'received_username': received_username, 'received_password': received_password }
        return userpass_dct

    def validate_credentials( self, received_auth_dct ):
        """ Checks credentials.
            Called by views.gh_inscription_watcher() """
        return_val = False
        if received_auth_dct['received_username'] == self.AUTH_USERNAME and received_auth_dct['received_password'] == self.AUTH_PASSWORD:
            return_val = True
        log.debug( 'return_val, ```{}```'.format(return_val) )
        return return_val

    def make_unauthenticated_response( self ):
        """ Returns proper 401 response.
            Called by views.gh_inscription_watcher() """
        log.debug( 'preparing 401 response' )
        resp = HttpResponse( '401 / Not Authenticated' )
        resp.status_code = 401
        resp['WWW-Authenticate'] = 'Basic realm="iip_processor"'
        return resp

    # def determine_signature( self, secret, payload ):
    #     """ Returns signature of payload.
    #         Note, secret must be utf8; payload can be unicode. """
    #     secret_utf8 = secret.encode( 'utf-8' )
    #     hmac_digest_utf8 = hmac.new( secret_utf8, payload, hashlib.sha1 ).hexdigest()
    #     signature = 'sha1={}'.format( hmac_digest_utf8.decode('utf-8') )
    #     log.debug( 'calculated signature, ```{}```'.format(signature) )
    #     return signature

    def determine_signature( self, secret, payload ):
        """ Returns signature of payload.
            Note, secret must be utf8; payload can be unicode. """
        assert type(secret) == str, type(secret)
        assert type(payload) == str, type(payload)
        secret_utf8 = secret.encode( 'utf-8' )
        payload_utf8 = payload.encode( 'utf-8' )
        hmac_digest = hmac.new( secret_utf8, payload_utf8, hashlib.sha1 ).hexdigest()
        assert type(hmac_digest) == str, type(hmac_digest)
        signature = 'sha1={}'.format( hmac_digest )
        log.debug( 'calculated signature, ```{}```'.format(signature) )
        return signature

    ## end class GHValidator()


class GHHelper( object ):
    """ Contains functions to process incoming github request.
        Helper for views.gh_inscription_watcher() """

    def __init__( self ):
        """ Grabs env-vars.
            Note: auth-username and auth-password no longer used for validation here, but still needed for dev pass-through. """
        self.AUTH_USERNAME = os.environ['IIP_PRC__BASIC_AUTH_USERNAME']
        self.AUTH_PASSWORD = os.environ['IIP_PRC__BASIC_AUTH_PASSWORD']
        self.DEV_URL = os.environ['IIP_PRC__DEV_URL']
        self.PRODUCTION_HOSTNAME = os.environ['IIP_PRC__PRODUCTION_HOSTNAME']

    def handle_inscription_update( self, request_body, host, submitted_signature ):
        """ Enqueues first of a series of processing jobs.
            Called by views.gh_inscription_watcher() """
        log.debug( 'request_body, ```{}```'.format(request_body) )
        data_dct = json.loads( request_body )
        to_process_dct = self.prep_files_to_process( data_dct['commits'] )
        processor.run_call_git_pull( to_process_dct )
        self.trigger_dev_if_production( request_body, host, submitted_signature )
        return

    def prep_files_to_process( self, commits_lst ):
        """ Prepares the data-dict to be sent to the first rq job.
            Called by handle_inscription_update() """
        files_to_process = { 'files_updated': [], 'files_removed': [], 'timestamp': str(datetime.datetime.now()) }
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
            if dir_segment in entry:  # good inscription
                cleaned.append( entry.replace(dir_segment, '').replace('.xml', '') )
        log.debug( 'cleaned, ```{}```'.format(cleaned) )
        return cleaned

    def trigger_dev_if_production( self, request_body, host, submitted_signature ):
        """ Sends github `data` to dev-server (which github can't hit) if this is the production-server.
            Called by handle_inscription_update() """
        log.debug( 'starting' )
        if host == self.PRODUCTION_HOSTNAME:
            log.debug( 'gonna hit dev' )
            try:
                headers = {'X_HUB_SIGNATURE': submitted_signature}
                r = requests.post( self.DEV_URL, data=request_body, auth=(self.AUTH_USERNAME, self.AUTH_PASSWORD), headers=headers, timeout=10 )
                log.debug( 'status_code, `{}`'.format(r.status_code) )
            except Exception as e:
                log.error( 'exception, ```{}```'.format( repr(e)) )
        log.debug( 'leaving' )
        return

    ## end class GHHelper()
