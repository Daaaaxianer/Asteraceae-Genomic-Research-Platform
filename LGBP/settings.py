import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

from LGBP.private_config import load_private_config
_private_settings = load_private_config(BASE_DIR)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = _private_settings['SECRET_KEY']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',

    # Local apps
    'tools',
    'browse',
    'api',
]

MIDDLEWARE = [
    'api.download_access.DownloadOwnerMiddleware',
    'api.security.APISecurityMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'api.middleware.DownloadConcurrencyLimitMiddleware',
    'api.compute_limits.ComputeSubmissionMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'LGBP.urls'

CSRF_COOKIE_SECURE = True  # 如果使用HTTPS
CSRF_COOKIE_HTTPONLY = True  # 可选，增强安全性


CSRF_TRUSTED_ORIGINS = [
    # 'https://cgrpoee.top',
    # 'https://fabaceae2.cgrpoee.top',
    # 'https://fabaceae.cgrpoee.top',
    # 'http://localhost:8000',  # 如果在本地测试
    'http://127.0.0.1:8000'
]


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')]
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'LGBP.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }
# # settings.py
DATABASES = _private_settings['DATABASES']
del _private_settings

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'learn_database',
#         'USER': 'learn_database',
#         'PASSWORD': '',
#         'HOST': '47.92.161.27',
#         'PORT': '3306',
#         'CONN_MAX_AGE': 1200,  # 保持连接600秒
#         # 'OPTIONS': {
#         #     'charset': 'utf8mb4',
#         #     'use_unicode': True,  # 确认数据库使用的字符编码是否与 Django 设置中的 DATABASES 配置兼容
#         # },
#         'OPTIONS': {
#             'init_command': "SET SESSION wait_timeout = 28800",
#             'charset': 'utf8mb4',
#             'sql_mode': 'STRICT_TRANS_TABLES',
#         },
#     }
# }



# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
    # os.path.join(BASE_DIR, 'Jojoa/templates/static'),
    # os.path.join(BASE_DIR, '/browse/static'),
)

# settings.py
MEDIA_URL = '/file_keep/'  # 必须与 URL 中的 /file_keep/ 匹配
MEDIA_ROOT = os.path.join(BASE_DIR, 'file_keep')  # 文件实际存储的绝对路径

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600  #上传文件大小，改成25M
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600	#上传数据大小，也改成了25M



# import logging
#
# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'handlers': {
#         'file': {
#             'level': 'DEBUG',
#             'class': 'logging.FileHandler',
#             'filename': '/www/wwwlogs/LGRPv2.log',  # 修改为日志文件路径
#         },
#     },
#     'loggers': {
#         'django': {
#             'handlers': ['file'],
#             'level': 'DEBUG',
#             'propagate': True,
#         },
#     },
# }

# -----------------------------------------------------------------------------
# AGRP public API protection
# -----------------------------------------------------------------------------
# This cache is used by API rate limiting and download concurrency limiting.
# It is intentionally lightweight and does not require extra services.
# If the API later receives heavy traffic or runs with many worker processes,
# replace LocMemCache with Redis or Memcached for shared counters.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'agrp-api-rate-limit',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 10000,
        },
    }
}

# Public users use the default limits. Authorized collaborators can be granted
# higher quota by adding their IP address to AGRP_API_TRUSTED_IPS or by issuing
# a dedicated API key and storing only its SHA-256 hash in AGRP_API_KEY_HASHES.
#
# Examples:
# AGRP_API_TRUSTED_IPS = {
#     '203.0.113.10',       # one fixed IP
#     '203.0.113.0/24',     # one CIDR network
# }
#
# AGRP_API_KEY_HASHES = {
#     'paste_sha256_hash_here': {
#         'name': 'Example Lab',
#         'tier': 'partner',
#         'enabled': True,
#     },
# }
AGRP_API_TRUSTED_IPS = set()

AGRP_API_KEY_HASHES = {}

AGRP_API_RATE_LIMITS = {
    'public': {
        'download': (5, 60),
        'files': (60, 60),
        'query': (120, 60),
        'ping': (60, 60),
    },
    'partner': {
        'download': (60, 60),
        'files': (600, 60),
        'query': (1000, 60),
        'ping': (120, 60),
    },
    'trusted': {
        'download': (120, 60),
        'files': (1200, 60),
        'query': (2000, 60),
        'ping': (300, 60),
    },
}

AGRP_API_DOWNLOAD_CONCURRENCY_LIMITS = {
    'public': 2,
    'partner': 10,
    'trusted': 20,
}

AGRP_API_QUERY_MAX_LIMITS = {
    'public': 100,
    'partner': 1000,
    'trusted': 2000,
}

REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'api.throttles.AGRPIPRateThrottle',
    ],
}

# API security only; framework/database versions and non-API routes are unchanged.
# Nginx appends its peer to X-Forwarded-For. Requests must arrive through
# that local proxy and a verified Cloudflare hop, over public HTTPS.
AGRP_API_REQUIRE_EDGE = True
AGRP_API_REQUIRE_HTTPS = True
AGRP_API_ALLOWED_HOSTS = ('asteraceae.cgrpoee.top', 'asteraceae.cgrpoee.cn')
AGRP_API_TRUSTED_PROXY_CIDRS = ('127.0.0.1/32', '::1/128')
AGRP_API_MAX_QUERY_BYTES = 8192
AGRP_API_MAX_OFFSET = 100000
AGRP_API_JSON_MAX_BYTES = 16 * 1024 * 1024
AGRP_API_TE_MAX_BYTES = 16 * 1024 * 1024
AGRP_API_TE_MAX_FILES = 64
AGRP_API_GLOBAL_QUERY_CONCURRENCY = 8
AGRP_API_GLOBAL_DOWNLOAD_CONCURRENCY = 8
AGRP_API_STATE_DIR = BASE_DIR / '.api_security_state'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'api_audit': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(BASE_DIR / '.api_security_logs' / 'api_audit.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'encoding': 'utf-8',
            'formatter': 'api_timestamp',
        },
    },
    'formatters': {'api_timestamp': {'format': '%(asctime)s %(levelname)s %(message)s'}},
    'loggers': {'agrp.api': {'handlers': ['api_audit'], 'level': 'INFO', 'propagate': False}},
}


# One-click exports and temporary, task-scoped result links.
AGRP_API_EXPORT_MAX_BYTES = 16 * 1024 * 1024
AGRP_RESULT_LINK_MAX_AGE = 7 * 86400
AGRP_API_INLINE_CONCURRENCY = 8
