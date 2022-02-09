# -*- coding: utf-8 -*-

from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic import RedirectView
from iip_processing_app import views

admin.autodiscover()


urlpatterns = [

    url( r'^admin/options/', views.admin_options, name='admin_options_url' ),
    url( r'^admin/', include(admin.site.urls) ),

    url( r'^info/$', views.info, name='info_url' ),

    url( r'^gh_inscription_watcher/$', views.gh_inscription_watcher, name='gh_inscription_watcher_url' ),

    url( r'^process_all/$', views.process_all, name='process_all_url' ),

    url( r'^delete_solr_orphans/process_deletions/$', views.process_solr_deletions, name='process_deletions_url' ),
    url( r'^delete_solr_orphans/$', views.delete_solr_orphans, name='delete_orphans_url' ),

    url( r'^update_processing_status/$', views.update_processing_status, name='update_processing_status_url' ),

    url( r'^view_processing/$', views.view_processing, name='view_processing_url' ),

    ## support urls...
    url( r'^version/$', views.version, name='version_url' ),
    url( r'^error_check/$', views.error_check, name='error_check_url' ),

    url( r'^$', RedirectView.as_view(pattern_name='info_url') ),

    ]
