"""Isolated API regression settings; no production database is used."""
from pathlib import Path
SECRET_KEY = 'isolated-api-regression-tests'
BASE_DIR = Path(__file__).resolve().parent.parent
INSTALLED_APPS = []
DATABASES = {'default': {'ENGINE': 'django.db.backends.dummy'}}
USE_I18N = False
DEBUG = True
ALLOWED_HOSTS = ['testserver', 'asteraceae.cgrpoee.top', 'localhost']
ROOT_URLCONF = 'api.security_test_urls'
MIDDLEWARE = ['api.download_access.DownloadOwnerMiddleware', 'api.security.APISecurityMiddleware', 'api.middleware.DownloadConcurrencyLimitMiddleware', 'api.compute_limits.ComputeSubmissionMiddleware']
REST_FRAMEWORK = {'DEFAULT_AUTHENTICATION_CLASSES': [], 'UNAUTHENTICATED_USER': None,
                  'DEFAULT_THROTTLE_CLASSES': []}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
AGRP_API_TRUSTED_IPS = set()
AGRP_API_KEY_HASHES = {}
LOGGING = {'version': 1, 'handlers': {'null': {'class': 'logging.NullHandler'}},
           'loggers': {'agrp.api': {'handlers': ['null'], 'propagate': False}}}
