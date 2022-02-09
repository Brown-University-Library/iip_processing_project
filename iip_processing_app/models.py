# -*- coding: utf-8 -*-

import json, logging
from django.core import serializers
from django.db import models


log = logging.getLogger(__name__)


class Status( models.Model ):
    """ Contains processing status. """
    inscription_id = models.CharField( blank=True, max_length=20 )
    modified_datetime = models.DateTimeField( auto_now=True )
    status_summary = models.CharField( blank=True, max_length=20 )
    status_detail = models.TextField( blank=True )

    def __str__(self):
        return self.inscription_id

    def jsonify(self):
        """ Returns object data in json-compatible dict. """
        jsn = serializers.serialize( 'json', [self] )  # json string is single-item list
        lst = json.loads( jsn )
        object_dct = lst[0]
        # return Status
        return object_dct

    class Meta:
        verbose_name_plural = 'Processing Statuses'
