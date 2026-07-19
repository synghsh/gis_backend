"""
Django settings for gis_admin project.
"""
import mimetypes
import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory definition
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variable files before importing constants (as constants loads them at import time)
_django_env = os.getenv('DJANGO_ENV', 'development')
load_dotenv(BASE_DIR / f".env.{_django_env}")

from constants import (
    DJANGO_DEBUG, SECRET_KEY, ALLOWED_HOSTS, DB_ENGINE, DB_HOST, DB_REPLICA_HOST, 
    DB_PORT, DB_NAME, DB_SCHEMA, DB_USER, DB_PASSWORD, DB_POOL, DB_OVER, CONN_MAX_AGE,
    LOGGING_LEVEL, LOG_FILESIZE, LOG_BACKUPCOUNT, LOG_FILE_HEALTH, LOG_FILE_AUTH, 
    LOG_FILE_ADMIN, LOG_FILE_COMMON, LOG_FILE_SURVEY, QUERY_LOGGING,
    R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_ENDPOINT_URL, R2_PUBLIC_URL
)

ENVIRONMENT = os.getenv('DJANGO_ENV', 'development')

SECRET_KEY = str(SECRET_KEY)
DEBUG = bool(DJANGO_DEBUG == 'True' or DJANGO_DEBUG == True)

ALLOWED_HOSTS = [x.strip() for x in ALLOWED_HOSTS.split(',')] if ALLOWED_HOSTS else ['*']

CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_ALL_ORIGINS = True

if DEBUG:
    mimetypes.add_type("application/javascript", ".js", True)

# Application definitions
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'rest_framework',
    'corsheaders',
    
    # Custom apps
    'JWTAuth',
    'common',
    'administration',
    'survey_management',
    'master_management',
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',  
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',  
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Custom ASRLM-style Middleware Pipeline
    'commonUtility.middleware.DataParseMiddleware',             # Request parser (GET/POST/JSON -> request.data)
    'JWTAuth.JWTMiddleware.AuthMiddleware',                     # JWT authentication checking
    'commonUtility.middleware.TransactionMiddleware',           # Request-level DB atomic transactions
    'commonUtility.middleware.ErrorHandlingMiddleware',         # Intercept exceptions and assign error codes
    'commonUtility.middleware.FinalResponseMiddleware',         # Final JSON response envelope wrapper
]

ROOT_URLCONF = 'gis_admin.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'gis_admin.wsgi.application'

# Database configuration with connection pooling (using SQLite fallback if postgres parameters missing)
if not DB_NAME or DB_NAME == 'placeholder':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': str(DB_ENGINE),
            'NAME': str(DB_NAME),
            'HOST': str(DB_HOST),
            'PORT': int(DB_PORT) if DB_PORT else 5432,
            'USER': str(DB_USER),
            'PASSWORD': str(DB_PASSWORD),
            'OPTIONS': {
                'options': f'-c search_path={DB_SCHEMA}'
            },
            'POOL_OPTIONS': {
                'POOL_SIZE': int(DB_POOL) if DB_POOL else 10,
                'MAX_OVERFLOW': int(DB_OVER) if DB_OVER else 5,
                'RECYCLE': 24 * 60 * 60
            },
            'CONN_MAX_AGE': int(CONN_MAX_AGE) if CONN_MAX_AGE else 600,
        },
        'replica': {
            'ENGINE': str(DB_ENGINE),
            'NAME': str(DB_NAME),
            'HOST': str(DB_REPLICA_HOST or DB_HOST),
            'PORT': int(DB_PORT) if DB_PORT else 5432,
            'USER': str(DB_USER),
            'PASSWORD': str(DB_PASSWORD),
            'OPTIONS': {
                'options': f'-c search_path={DB_SCHEMA}'
            },
            'POOL_OPTIONS': {
                'POOL_SIZE': int(DB_POOL) if DB_POOL else 10,
                'MAX_OVERFLOW': int(DB_OVER) if DB_OVER else 5,
                'RECYCLE': 24 * 60 * 60
            },
            'CONN_MAX_AGE': int(CONN_MAX_AGE) if CONN_MAX_AGE else 600,
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Cloudflare R2 / S3-compatible Storage Configuration with fallback
if R2_ACCESS_KEY_ID and R2_ACCESS_KEY_ID != 'placeholder_r2_access_key':
    AWS_ACCESS_KEY_ID = R2_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY = R2_SECRET_ACCESS_KEY
    AWS_STORAGE_BUCKET_NAME = R2_BUCKET_NAME
    AWS_S3_ENDPOINT_URL = R2_ENDPOINT_URL
    AWS_S3_CUSTOM_DOMAIN = R2_PUBLIC_URL.replace("https://", "").replace("http://", "") if R2_PUBLIC_URL else None
    AWS_S3_REGION_NAME = 'auto'
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH = False
    AWS_DEFAULT_ACL = None

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/" if AWS_S3_CUSTOM_DOMAIN else f"{R2_ENDPOINT_URL}/{R2_BUCKET_NAME}/"
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    MEDIA_URL = 'media/'
    MEDIA_ROOT = BASE_DIR / 'media'


# Logging Configuration
LOG_DIR = BASE_DIR / 'logs'
os.makedirs(LOG_DIR, exist_ok=True)

# File size in bytes (from MB settings)
MAX_LOG_BYTES = int(LOG_FILESIZE or 50) * 1024 * 1024

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'file': {
            'format': '%(asctime)s %(levelname)-8s | Process %(process)d | Thread: %(thread)d | %(name)-12s | %(module)s.%(funcName)s:ln %(lineno)d |--  %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'console': {
            'format': '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
        }
    },
    'handlers': {
        'file_health': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / LOG_FILE_HEALTH,
            'maxBytes': MAX_LOG_BYTES,
            'backupCount': LOG_BACKUPCOUNT,
            'formatter': 'file',
            'delay': False
        },
        'file_auth': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / LOG_FILE_AUTH,
            'maxBytes': MAX_LOG_BYTES,
            'backupCount': LOG_BACKUPCOUNT,
            'formatter': 'file',
            'delay': False
        },
        'file_admin': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / LOG_FILE_ADMIN,
            'maxBytes': MAX_LOG_BYTES,
            'backupCount': LOG_BACKUPCOUNT,
            'formatter': 'file',
            'delay': False
        },
        'file_common': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / LOG_FILE_COMMON,
            'maxBytes': MAX_LOG_BYTES,
            'backupCount': LOG_BACKUPCOUNT,
            'formatter': 'file',
            'delay': False
        },
        'file_survey': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / LOG_FILE_SURVEY,
            'maxBytes': MAX_LOG_BYTES,
            'backupCount': LOG_BACKUPCOUNT,
            'formatter': 'file',
            'delay': False
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'console'
        }
    },
    'loggers': {
        'django.request': {
            'level': 'ERROR',
            'handlers': ['file_common', 'file_auth', 'file_admin', 'file_survey'],
            'propagate': False,
        },
        'django': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': True
        },
        'health': {
            'level': str(LOGGING_LEVEL),
            'handlers': ['file_health'],
            'propagate': True,
        },
        'administration': {
            'level': str(LOGGING_LEVEL),
            'handlers': ['file_admin'],
            'propagate': True,
        },
        'JWTAuth': {
            'level': str(LOGGING_LEVEL),
            'handlers': ['file_auth'],
            'propagate': True,
        },
        'common': {
            'level': str(LOGGING_LEVEL),
            'handlers': ['file_common'],
            'propagate': True,
        },
        'survey_management': {
            'level': str(LOGGING_LEVEL),
            'handlers': ['file_survey'],
            'propagate': True,
        },
        'master_management': {
            'level': str(LOGGING_LEVEL),
            'handlers': ['file_admin'],
            'propagate': True,
        },
    }
}

ENABLE_QUERY_LOGGING = bool(QUERY_LOGGING == 'True' or QUERY_LOGGING == True)
RATE_LIMIT_SKIP_IPS = ['127.0.0.1']
