# -*- coding: utf-8 -*-

""" Contains tests for git-pulls and rq processing. """

import logging, os, time
import redis, requests, rq
from django.test import TestCase
from iip_processing_app.lib import processor
from iip_processing_app.lib.processor import Prepper
from iip_processing_app.lib.processor import Puller


log = logging.getLogger(__name__)
TestCase.maxDiff = None
prepper = Prepper()
puller = Puller()


class PrepperOtherTest(TestCase):
    """ Checks processor.py functions that depend on git-pulls or rq jobs. """

    def setUp(self):
        self.queue_name = os.environ['IIP_PRC__QUEUE_NAME']

    def test_good_transform_xml(self):
        """ Checks transform with good source-xml and good-stylesheet.
            TODO: think about how to call the xsl_transformer url and move this test back to tests_unit.py
            Note: if this test fails from localdev, check that the IP calling the stylesheet-transormer service is in the dev-server settings. """
        url = 'https://apps.library.brown.edu/iip/inscriptions/epidoc-files/abur0001.xml'
        r = requests.get( url )
        xml_utf8 = r.content
        source_xml = xml_utf8.decode( 'utf-8' )
        unicode_doc = prepper.make_initial_solr_doc( source_xml )
        self.assertEqual(
            True,
            # u'Κύριε' in unicode_doc,  # now appears w/vertical characters
            u'νούντων' in unicode_doc,
        )

    def test_transform_bad_stylesheet_path(self):
        """ Checks transform response with bad stylesheet.
            TODO: think about how to call the xsl_transformer url and move this test back to tests_unit.py """
        prepper.STYLESHEET_PATH = '/does/not/exist'
        url = 'https://apps.library.brown.edu/iip/inscriptions/epidoc-files/abur0001.xml'
        r = requests.get( url )
        xml_utf8 = r.content
        source_xml = xml_utf8.decode( 'utf-8' )
        try:
            unicode_doc = prepper.make_initial_solr_doc( source_xml )
        except Exception as e:
            self.assertTrue( 'No such file or directory' in repr(e) )

    def test_call_git_pull(self):
        """ Checks for successful pull. """
        self.assertEqual(
            0,  # 0 means no problems; 1 means a problem
            puller.call_git_pull()
        )

    def test_run_call_git_pull(self):
        """ Triggers processing for processor.run_call_git_pull(); checks for no failed jobs.
            Note, if running locally, may have to run `$ python ./iip_processing_app/lib/queue_utils/clear_job_queue.py` first. """
        ## confirm no processing jobs running
        q = rq.Queue( self.queue_name, connection=redis.Redis() )
        self.assertEqual( 0, len(q.jobs) )
        ##
        ## confirm no processing failed jobs
        failed_queue = rq.queue.get_failed_queue( connection=redis.Redis() )
        failed_count = 0
        for job in failed_queue.jobs:
            if job.origin == self.queue_name:
                failed_count += 1
        self.assertEqual( 0, failed_count )
        ##
        ## call processor.run_call_git_pull( to_process_dct )
        # to_process_dct = {
        #     'files_removed': ['abur0001', 'ahma0001'],
        #     'files_updated': [],
        #     'timestamp': '2017-01-24 09:52:38.911009' }
        to_process_dct = {
            'files_removed': [],
            'files_updated': ['abur0001', 'ahma0001'],
            'timestamp': '2017-01-24 09:52:38.911009' }
        processor.run_call_git_pull( to_process_dct )
        ##
        ## confirm no processing failed jobs
        time.sleep( 2 )
        failed_queue = rq.queue.get_failed_queue( connection=redis.Redis() )
        failed_count = 0
        for job in failed_queue.jobs:
            if job.origin == self.queue_name:
                failed_count += 1
        self.assertEqual( 0, failed_count )
