from .common import *  # noqa: ignore=F405

import logging.config
import os
from django.utils.log import DEFAULT_LOGGING

import raven

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Database
# https://docs.djangoproject.com/en/1.10.2/ref/settings/#databases

CORS_ORIGIN_ALLOW_ALL = False

CORS_ORIGIN_WHITELIST = (
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8888",

)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "evalai",  # noqa: ignore=F405
        "USER": "postgres"
        ,  # noqa: ignore=F405
        "PASSWORD": "postgres"
        ,  # noqa: ignore=F405
        "HOST": "localhost"
        ,  # noqa: ignore=F405
        "PORT": 5432,  # noqa: ignore=F405
    }
}

# settings.py
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static'), ]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'



INSTALLED_APPS += ("storages", "raven.contrib.django.raven_compat")  # noq

#EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
#EMAIL_USE_SSL = True
#EMAIL_USE_TLS = False
#EMAIL_HOST = 'smtps.itrc.ac.ir'
#EMAIL_HOST_USER = 'ailabs@itrc.ac.ir'
#EMAIL_HOST_PASSWORD = 'ailabs@itrc'
#EMAIL_PORT = 465
#DEFAULT_FROM_EMAIL = 'challenges@parsiazma'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'elahehehteshami0@gmail.com'
EMAIL_HOST_PASSWORD = 'dzmylmlowbbahbfp'
DEFAULT_FROM_EMAIL = 'elahehehteshami0@gmail.com'

# Hide API Docs on production environment
REST_FRAMEWORK_DOCS = {"HIDE_DOCS": True}

# Port number for the python-memcached cache backend.
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"},
    "throttling": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}  # noqa: ignore=F405

# https://docs.djangoproject.com/en/1.10/ref/settings/#secure-proxy-ssl-header
SECURE_SSL_REDIRECT = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
LOGLEVEL = os.environ.get('LOGLEVEL', 'info').upper()
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}
