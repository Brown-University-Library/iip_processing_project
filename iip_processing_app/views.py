# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime, json, logging, os, pprint
from django.conf import settings
from django.contrib.auth import login as django_login
from django.contrib.auth import logout
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
# from iip_processing_app.lib.admin_helper import ProcessStatusRecorder
from iip_processing_app.lib.github_helper import GHHelper, GHValidator
from iip_processing_app.lib.orphan_helper import OrphanDeleter
from iip_processing_app.lib.process_viewer_helper import UserGrabber, ProcessStatusRecorder
from iip_processing_app.models import Status


log = logging.getLogger(__name__)
github_validator = GHValidator()
github_helper = GHHelper()
orphan_deleter = OrphanDeleter()
process_status_recorder = ProcessStatusRecorder()
user_grabber = UserGrabber()


def info( request ):
    """ Returns simplest response. """
    now = datetime.datetime.now()
    log.debug( 'now, ```{}```'.format(now) )
    return HttpResponse( '<p>hi</p> <p>( %s )</p>' % now )


@csrf_exempt
def gh_inscription_watcher( request ):
    """ Handles github inscriptions web-hook notification. """
    log.debug( 'request.__dict__, ```{}```'.format(pprint.pformat(request.__dict__)) )
    resp = HttpResponseForbidden( '403 / Forbidden' )  # will be returned if incorrect basic-auth credentials are submitted, or if signature check fails.
    if 'HTTP_AUTHORIZATION' in request.META:
        ( submitted_basic_auth_info, submitted_signature, submitted_payload ) = ( request.META['HTTP_AUTHORIZATION'].decode('utf-8'), request.META['HTTP_X_HUB_SIGNATURE'].decode('utf-8'), request.body.decode('utf-8') )
        if github_validator.validate_submission( submitted_basic_auth_info, submitted_signature, submitted_payload ):
            github_helper.handle_inscription_update( request.body, request.META.get('HTTP_HOST', None), submitted_signature )
            resp = HttpResponse( '200 / OK' )
    else:
        resp = github_validator.make_unauthenticated_response()
    log.debug( 'response status code, `{}`'.format(resp.status_code) )
    return resp


@csrf_exempt
def update_processing_status( request ):
    """ Updates status table, either with a bunch of items to be listed as 'enqueued' -- or with a single item status update.
        Called by workers. """
    log.debug( 'request.__dict__, ```{}```'.format(pprint.pformat(request.__dict__)) )
    resp = HttpResponseForbidden( '403 / Forbidden' )
    if unicode( request.META.get('HTTP_HOST', '') ) in settings.ALLOWED_HOSTS:
        ( to_process_dct, single_update_dct ) = process_status_recorder.check_for_data( request.body )
        if to_process_dct:
            resp = process_status_recorder.handle_enqueues( to_process_dct )
        elif single_update_dct:
            resp = process_status_recorder.handle_single_update( single_update_dct )
    return resp


### admin-access views ###


def delete_solr_orphans( request ):
    """ Manages initial request to delete orphaned records from solr. """
    request.session['ids_to_delete'] = json.dumps( [] )
    resp = HttpResponseForbidden( '403 / Forbidden' )
    ( eppn, dev_user, host ) = ( request.META.get('Shibboleth-eppn', ''), request.GET.get('dev_auth_hack', ''), request.get_host() )
    if orphan_deleter.validate_delete_request( eppn, dev_user, host ):
        data = orphan_deleter.prep_data()
        request.session['ids_to_delete'] = json.dumps( data )
        context = orphan_deleter.prep_context( data )
        resp = render( request, u'iip_processing_templates/show_proposed_deletions.html', context )
    log.debug( 'resp.__dict__, ```{}```'.format(pprint.pformat(resp.__dict__)) )
    return resp


def process_solr_deletions( request ):
    """ Triggers actual deletion-processing.
        Called by clicking the go-ahead-and-delete button in views.delete_solr_orphans()
        The POST requirement, combined with built-in csrf protection, is enough to ensure hits are valid. """
    resp = HttpResponseForbidden( '403 / Forbidden' )
    if request.method == 'POST':
        orphan_deleter.run_deletes( json.loads(request.session.get('ids_to_delete')) )
        resp = HttpResponse( 'deletions completed' )
    request.session['ids_to_delete'] = json.dumps( [] )
    log.debug( 'resp.__dict__, ```{}```'.format(pprint.pformat(resp.__dict__)) )
    return resp


def view_processing( request ):
    """ If shib headers ok, logs user in & redirects to admin view. """
    log.debug( 'starting view_processing()' )
    user = user_grabber.get_user( request.META )
    if user:
        log.debug( 'logging in user' )
        django_login(request, user )
    url = reverse('admin:iip_processing_app_status_changelist' )
    log.debug( 'redirect url to admin, ```{}```'.format(url) )
    return HttpResponseRedirect( url )  ## TODO: add shib logout (via redirecting to shib-logout url, then redirecting to the above admin url)


def process_all( request ):
    """ Manages full-reindexing. """
    request.session['process_all_ids'] = json.dumps( [] )
    resp = HttpResponseForbidden( '403 / Forbidden' )
    ( eppn, dev_user, host ) = ( request.META.get('Shibboleth-eppn', ''), request.GET.get('dev_auth_hack', ''), request.get_host() )
    if all_processor.validate_request( eppn, dev_user, host ):
        data_lst = all_processor.prep_data()
        request.session['process_all_ids'] = json.dumps( data_lst )
        context = all_processor.prep_context()
        resp = render( request, u'iip_processing_templates/process_all_response.html', context )
    log.debug( 'resp.__dict__, ```{}```'.format(pprint.pformat(resp.__dict__)) )
    return resp
    return HttpResponse( 'process_all coming' )

## EOF
