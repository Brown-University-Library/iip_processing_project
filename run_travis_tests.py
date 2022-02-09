# -*- coding: utf-8 -*-

# flake8: noqa

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner


if __name__ == '__main__':
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings_travis'
    ## initialize dummy envvars used by class initialization
    for not_used_for_testing_item in [
        'IIP_PRC__BASIC_AUTH_PASSWORD',
        'IIP_PRC__BASIC_AUTH_USERNAME',
        'IIP_PRC__CLONED_INSCRIPTIONS_PATH',
        'IIP_PRC__DEV_URL',
        'IIP_PRC__DISPLAY_STATUSES_BACKUP_DIR',
        'IIP_PRC__LEGIT_QUEUE_VIEWER_PASSWORD',
        'IIP_PRC__LEGIT_QUEUE_VIEWER_USER',
        'IIP_PRC__PROCESS_STATUS_UPDATER_URL',
        'IIP_PRC__PRODUCTION_HOSTNAME',
        'IIP_PRC__REPO_SECRET_KEY',
        'IIP_PRC__SOLR_DOC_STYLESHEET_PATH',
        'IIP_PRC__SOLR_URL',
        'IIP_PRC__STATUSES_GIST_PASSWORD',
        'IIP_PRC__STATUSES_GIST_URL',
        'IIP_PRC__STATUSES_GIST_USERNAME',
        'IIP_PRC__TRANSFORMER_AUTH_KEY',
        'IIP_PRC__TRANSFORMER_URL' ]:
        os.environ[ not_used_for_testing_item ] = 'foo'
    os.environ['IIP_PRC__DISPLAY_STATUSES_BACKUP_TIMEFRAME_IN_DAYS'] = '1'  # converted to int by __init__
    os.environ['IIP_PRC__LEGIT_ADMINS_JSON'] = '"foo"'  # valid json required
    os.environ['IIP_PRC__LEGIT_QUEUE_VIEWER_GROUPS_JSON'] = '"foo"'
    os.environ['IIP_PRC__LEGIT_QUEUE_VIEWER_EPPNS_JSON'] = '"foo"'
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['iip_processing_app.tests.tests_unit'])
    sys.exit(bool(failures))
