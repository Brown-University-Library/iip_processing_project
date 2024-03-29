# -*- coding: utf-8 -*-

"""
Django settings for iip_processing_project for travis-ci.org

Environmental variables are set in run_travis_tests.py
"""

# import json, logging, os


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '123'

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG = json.loads( os.environ['IIP_PRC__DEBUG_JSON'] )  # will be True or False

# ADMINS = json.loads( os.environ['IIP_PRC__ADMINS_JSON'] )

# ALLOWED_HOSTS = json.loads( os.environ['IIP_PRC__ALLOWED_HOSTS'] )  # list


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'iip_processing_app',
]

# MIDDLEWARE = [
#     'django.middleware.security.SecurityMiddleware',
#     'django.contrib.sessions.middleware.SessionMiddleware',
#     'django.middleware.common.CommonMiddleware',
#     'django.middleware.csrf.CsrfViewMiddleware',
#     'django.contrib.auth.middleware.AuthenticationMiddleware',
#     'django.contrib.messages.middleware.MessageMiddleware',
#     'django.middleware.clickjacking.XFrameOptionsMiddleware',
# ]

ROOT_URLCONF = 'config.urls'

# TEMPLATES = json.loads( os.environ['IIP_PRC__TEMPLATES_JSON'] )  # list of dict(s)

# WSGI_APPLICATION = 'config.passenger_wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

# DATABASES = json.loads( os.environ['IIP_PRC__DATABASES_JSON'] )
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'travis_tests.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

# AUTH_PASSWORD_VALIDATORS = [
#     {
#         'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
#     },
# ]


# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

# LANGUAGE_CODE = 'en-us'

# TIME_ZONE = 'America/New_York'  # was 'UTC'

# USE_I18N = True

# USE_L10N = True

# USE_TZ = True  # was False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

# STATIC_URL = os.environ['IIP_PRC__STATIC_URL']
# STATIC_ROOT = os.environ['IIP_PRC__STATIC_ROOT']  # needed for collectstatic command


# Email
# EMAIL_HOST = os.environ['IIP_PRC__EMAIL_HOST']
# EMAIL_PORT = int( os.environ['IIP_PRC__EMAIL_PORT'] )


# sessions

# <https://docs.djangoproject.com/en/1.10/ref/settings/#std:setting-SESSION_SAVE_EVERY_REQUEST>
# Thinking: not that many concurrent users, and no pages where session info isn't required, so overhead is reasonable.
# SESSION_SAVE_EVERY_REQUEST = True
# SESSION_EXPIRE_AT_BROWSER_CLOSE = True


# logging

## disable module loggers
# existing_logger_names = logging.getLogger().manager.loggerDict.keys()
# print( f'- EXISTING_LOGGER_NAMES, ``{existing_logger_names}``' )
# logging.getLogger('requests').setLevel( logging.WARNING )

# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': True,
#     'formatters': {
#         'standard': {
#             'format': "[%(asctime)s] %(levelname)s [%(module)s-%(funcName)s()::%(lineno)d] %(message)s",
#             'datefmt': "%d/%b/%Y %H:%M:%S"
#         },
#     },
#     'handlers': {
#         'logfile': {
#             'level':'DEBUG',
#             'class':'logging.FileHandler',  # note: configure server to use system's log-rotate to avoid permissions issues
#             'filename': os.environ.get(u'IIP_PRC__LOG_PATH'),
#             'formatter': 'standard',
#         },
#         'console':{
#             'level':'DEBUG',
#             'class':'logging.StreamHandler',
#             'formatter': 'standard'
#         },
#     },
#     'loggers': {
#         'iip_processing_app': {
#             'handlers': ['logfile'],
#             'level': os.environ.get(u'IIP_PRC__LOG_LEVEL'),
#             'propagate': False
#         },
#     }
# }
