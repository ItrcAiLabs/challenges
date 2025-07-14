from .common import *  # noqa: ignore=F405

import warnings

# Database
# https://docs.djangoproject.com/en/1.10.2/ref/settings/#databases

DEBUG = True

ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.environ.get("POSTGRES_NAME", "evalai"),  # noqa: ignore=F405
        "USER": os.environ.get(  # noqa: ignore=F405
            "POSTGRES_USER", "postgres"
        ),  # noqa: ignore=F405
        "PASSWORD": os.environ.get(  # noqa: ignore=F405
            "POSTGRES_PASSWORD", "postgres"
        ),  # noqa: ignore=F405
        "HOST": os.environ.get(  # noqa: ignore=F405
            "POSTGRES_HOST", "localhost"
        ),  # noqa: ignore=F405
        "PORT": os.environ.get("POSTGRES_PORT", 5432),  # noqa: ignore=F405
    }
}

# E-Mail Settings
#EMAIL_HOST = "localhost"
#EMAIL_PORT = 1025
#EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

#EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
#EMAIL_HOST = 'smtp.gmail.com'
#EMAIL_PORT = 587
#EMAIL_USE_TLS = True
#EMAIL_HOST_USER = 'elahehehteshami0@gmail.com'
#EMAIL_HOST_PASSWORD = 'dzmylmlowbbahbfp'
#DEFAULT_FROM_EMAIL = 'webmaster@yourdomain.com'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_SSL = True
#EMAIL_USE_TLS = False
EMAIL_HOST = 'smtps.itrc.ac.ir'
EMAIL_HOST_USER = 'ailabs@itrc.ac.ir'
EMAIL_HOST_PASSWORD = 'ailabs@itrc'
EMAIL_PORT = 465
DEFAULT_FROM_EMAIL = 'ailabs@itrc.ac.ir'

ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"

# DJANGO-SPAGHETTI-AND-MEATBALLS SETTINGS
INSTALLED_APPS += [  # noqa: ignore=F405
    "django_spaghetti",
    "autofixture",
    "debug_toolbar",
    "django_extensions",
    "silk",
]

SPAGHETTI_SAUCE = {
    "apps": [
        "auth",
        "accounts",
        "analytics",
        "base",
        "challenges",
        "hosts",
        "jobs",
        "participants",
        "web",
    ],
    "show_fields": True,
}

CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"},
    "throttling": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}

MEDIA_URL = "/media/"

MIDDLEWARE += [  # noqa: ignore=F405
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "silk.middleware.SilkyMiddleware",
]

SILKY_PYTHON_PROFILER = True

# Prevents Datetime warning by showing errors
warnings.filterwarnings(
    "error",
    r"DateTimeField .* received a naive datetime",
    RuntimeWarning,
    r"django\.db\.models\.fields",
)
