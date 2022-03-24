# -*- coding: utf-8 -*-

from django.contrib import admin
from iip_processing_app.models import Status


class StatusAdmin( admin.ModelAdmin ):
    date_hierarchy = 'modified_datetime'
    ordering = [ 'inscription_id' ]
    list_display = [
        'inscription_id', 'status_summary', 'status_detail', 'modified_datetime' ]
    list_filter = [ 'status_summary' ]
    search_fields = [
        'inscription_id', 'status_summary', 'status_detail' ]
    readonly_fields = [
        'inscription_id', 'status_summary', 'status_detail', 'modified_datetime' ]


admin.site.register( Status, StatusAdmin )
