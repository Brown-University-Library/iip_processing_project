# -*- coding: utf-8 -*-

import json, logging, os, pprint
from django.conf import settings
from django.contrib.auth import authenticate
from django.http import HttpResponse
from iip_processing_app.models import Status


log = logging.getLogger(__name__)


class UserGrabber(object):
    """ Grabs user object from shib or local-dev.
        Helper for views.view_processing() """

    def __init__( self ):
        self.LEGIT_VIEWER_USER = os.environ['IIP_PRC__LEGIT_QUEUE_VIEWER_USER']
        self.LEGIT_VIEWER_PASSWORD = os.environ['IIP_PRC__LEGIT_QUEUE_VIEWER_PASSWORD']

    def get_user( self, meta_dct ):
        """ Returns user object.
            Called by views.view_processing() """
        shib_checker = ShibChecker()
        if shib_checker.validate_user( meta_dct ):
            log.debug( 'validated via shib' )
            user = self.grab_good_user()
        elif meta_dct['SERVER_NAME'] is '127.0.0.1' and settings.DEBUG is True:
            log.debug( 'validated via localdev' )
            user = self.grab_good_user()
        else:
            log.debug( 'not validated' )
            user = None
        return user

    def grab_good_user( self ):
        """ Grabs generic authenticated user.
            Called by get_user() """
        user = authenticate( username=self.LEGIT_VIEWER_USER, password=self.LEGIT_VIEWER_PASSWORD )
        log.debug( 'user authenticated' )
        return user

    ## end class UserGrabber()


class ShibChecker( object ):
    """ Checks shib for valid eppn or group.
        Helper for views.view_processing() """

    def __init__( self ):
        self.LEGIT_VIEWER_GROUPER_GROUPS = json.loads( os.environ['IIP_PRC__LEGIT_QUEUE_VIEWER_GROUPS_JSON'] )
        self.LEGIT_VIEWER_EPPNS = json.loads( os.environ['IIP_PRC__LEGIT_QUEUE_VIEWER_EPPNS_JSON'] )

    def validate_user( self, meta_dct ):
        """ Checks shib info.
            Called by UserGrabber.get_user() """
        return_val = False
        shib_dct = self.grab_shib_info( meta_dct )
        if shib_dct:
            if self.check_group( shib_dct['member_of'] ):
                return_val = True
            elif self.check_eppn( shib_dct['eppn'] ):
                return_val = True
        log.debug( 'return_val, `{}`'.format(return_val) )
        return return_val

    def grab_shib_info( self, meta_dct ):
        """ Grabs shib values from http-header.
            Called by: validate_user() """
        shib_dct = None
        if 'Shibboleth-eppn' in meta_dct:
            shib_dct = self.grab_shib_from_meta( meta_dct )
        log.debug( 'shib_dct, ```{}```'.format(pprint.pformat(shib_dct)) )
        return shib_dct

    def check_group( self, user_memberships ):
        """ Checks user's grouper groups.
            Called by validate_user() """
        return_val = False
        for group in self.LEGIT_VIEWER_GROUPER_GROUPS:
            if group in user_memberships:
                return_val = True
                break
        log.debug( 'check_group() return_val, `{}`'.format(return_val) )
        return return_val

    def check_eppn( self, eppn ):
        """ Checks user's eppn.
            Called by validate_user() """
        return_val = False
        if eppn in self.LEGIT_VIEWER_EPPNS:
            return_val = True
        log.debug( 'check_eppn() return_val, `{}`'.format(return_val) )
        return return_val

    def grab_shib_from_meta( self, meta_dct ):
        """ Extracts shib values from http-header.
            Called by grab_shib_info() """
        shib_dct = {
            # 'brown_status': meta_dct.get( 'Shibboleth-brownStatus', '' ),  # eg. 'active'
            # 'brown_type': meta_dct.get( 'Shibboleth-brownType', '' ),  # eg. 'Staff'
            # 'department': meta_dct.get( 'Shibboleth-department', '' ),
            # 'edu_person_primary_affiliation': meta_dct.get( 'Shibboleth-eduPersonPrimaryAffiliation', '' ),  # eg. 'staff'
            # 'email': meta_dct.get( 'Shibboleth-mail', '' ).lower(),
            'eppn': meta_dct.get( 'Shibboleth-eppn', '' ),
            # 'id_net': meta_dct.get( 'Shibboleth-brownNetId', '' ),
            # 'id_short': meta_dct.get( 'Shibboleth-brownShortId', '' ),
            'member_of': sorted( meta_dct.get('Shibboleth-isMemberOf', '').split(';') ),  # only dct element that's not a unicode string
            # 'name_first': meta_dct.get( 'Shibboleth-givenName', '' ),
            # 'name_last': meta_dct.get( 'Shibboleth-sn', '' ),
            # 'patron_barcode': meta_dct.get( 'Shibboleth-brownBarCode', '' ),
            # 'phone': meta_dct.get( 'Shibboleth-phone', 'unavailable' ),  # valid?
            # 'title': meta_dct.get( 'Shibboleth-title', '' ),
        }
        return shib_dct

    ## end class ShibChecker()


class ProcessStatusRecorder( object ):
    """ Contains functions for recording processed-status.
        Helper for views.view_processing() """

    def __init__( self ):
        """ Settings. """
        pass

    def check_for_data( self, request_body ):
        """ Returns any multiple-enqueue data and any single-update data.
            Called by views.update_processing_status() """
        data_dct = self.grab_data_dct( request_body )
        to_process_dct = self.grab_to_process_dct( data_dct )
        single_update_dct = self.grab_single_update_dct( data_dct )
        return ( to_process_dct, single_update_dct )

    def grab_data_dct( self, request_body ):
        """ Grabs dct info from request.body.
            Called by check_for_data() """
        try:
            data_dct = json.loads( request_body )
        except:
            data_dct = {}
        log.debug( 'data_dct, ```{}```'.format(pprint.pformat(data_dct)) )
        return data_dct

    def grab_to_process_dct( self, data_dct ):
        """ Grabs possible enqueue-these data.
            Called by check_for_data() """
        try:
            to_process_dct = data_dct['to_process_dct']
        except:
            to_process_dct = {}
        log.debug( 'to_process_dct, ```{}```'.format(pprint.pformat(to_process_dct)) )
        return to_process_dct

    def grab_single_update_dct( self, data_dct ):
        """ Grabs possible single-item data.
            Called by check_for_data() """
        try:
            single_update_dct = {
                'inscription_id': data_dct['inscription_id'],
                'status_summary': data_dct['status_summary'],
                'status_detail': data_dct['status_detail'],
            }
        except:
            single_update_dct = {}
        log.debug( 'single_update_dct, ```{}```'.format(pprint.pformat(single_update_dct)) )
        return single_update_dct

    def handle_enqueues( self, to_process_dct ):
        """ Adds enqueu info to processing-status db.
            Called by views.update_processing_status() """
        for inscription_id in to_process_dct.get( 'files_removed', [] ):
            self.update_processing_status( inscription_id=inscription_id, new_status_summary='queued for deletion', new_status_detail='' )
        for inscription_id in to_process_dct.get( 'files_updated', [] ):
            self.update_processing_status( inscription_id=inscription_id, new_status_summary='queued for update', new_status_detail='' )
        resp = HttpResponse( '200 / OK' )
        return resp

    def update_processing_status( self, inscription_id, new_status_summary, new_status_detail ):
        """ Updates tracker that entry is queued for deletion.
            Called by handle_enqueues(), and by handle_single_update() """
        try:
            process_status = Status.objects.get( inscription_id=inscription_id )
        except Exception:
            log.debug( 'creating new Status instance' )
            process_status = Status( inscription_id=inscription_id )
        process_status.status_summary = new_status_summary
        process_status.status_detail = new_status_detail
        process_status.save()
        return

    def handle_single_update( self, single_update_dct ):
        """ Updates single entry processed status.
            Called by views.update_processing_status() """
        ( inscription_id, new_status_summary, new_status_detail ) = (
            single_update_dct['inscription_id'], single_update_dct['status_summary'], single_update_dct['status_detail'] )
        self.update_processing_status(
            inscription_id=inscription_id, new_status_summary=new_status_summary, new_status_detail=new_status_detail )
        resp = HttpResponse( '200 / OK' )
        return resp

    ## end class ProcessStatusRecorder()
