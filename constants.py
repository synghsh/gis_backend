import os

# Environment Variables
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
DJANGO_DEBUG = os.getenv('DEBUG', 'True')
QUERY_LOGGING = os.getenv('QUERY_LOGGING', 'True')
DEBUG_WATERMARK = os.getenv('DEBUG_WATERMARK', 'False')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*')

# Cache Configuration
CACHE_STORE_TIME = 3600  # 1 Hour

# Logging Configuration
LOGGING_LEVEL = os.getenv('LOGGING_LEVEL', 'DEBUG')
LOG_FILESIZE = os.getenv('LOG_FILESIZE', '50')
LOG_BACKUPCOUNT = int(os.getenv('LOG_BACKUPCOUNT', '5'))

LOG_FILE_HEALTH = "health.log"
LOG_FILE_AUTH = "auth.log"
LOG_FILE_ADMIN = "admin.log"
LOG_FILE_COMMON = "common.log"
LOG_FILE_SURVEY = "survey.log"

# Database Configuration
DB_ENGINE = os.getenv('DB_ENGINE', 'dj_db_conn_pool.backends.postgresql')
DB_NAME = os.getenv('DB_NAME', 'gis_survey_db')
DB_SCHEMA = os.getenv('DB_SCHEMA', 'public')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_REPLICA_HOST = os.getenv('DB_REPLICA_HOST', '127.0.0.1')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_POOL = os.getenv('DB_POOL', '10')
DB_OVER = os.getenv('DB_OVER', '5')
CONN_MAX_AGE = os.getenv('CONN_MAX_AGE', '600')

# AWS Configuration
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_S3_REGION = os.getenv('AWS_S3_REGION', 'ap-south-1')
AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET')
AWS_S3_OBJECT_NAME = os.getenv('AWS_S3_OBJECT_NAME', 'gis/development/')
AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL')

# Database Cursor Alias
DB_ALIAS_MASTER = "default"
DB_ALIAS_REPLICA = "replica"

# General Constants
C_TYPE_APP_JSON = "application/json"
UTF8 = "UTF-8"
TZ_INTERVAL = "5 hour 30 Minutes"
TZINFO = '05:30:00'
DB_STRF_TIME = "%Y-%m-%d %H:%M:%S.%f"
NOT_AVAILABLE = "N/A"

# Regex Expressions
PHONE_REGEX = r"^[6789]{1}\d{9}$"
EMAIL_REGEX = r"^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$"
NAME_REGEX = r"^[a-zA-Z\s'\-]+$"
PIN_REGEX = r"^[0-9]{6,6}$"
PASS_REGEX = r'^(?=^.{8,}$)((?=.*\d)|(?=.*\W+))(?![.\n])(?=.*[A-Z])(?=.*[a-z]).*$'


# JWT Settings
JWT_EXCLUSION_LIST = [
    '/gis/administration/admin/login/',
    '/gis/administration/health/',
]

# Response envelopes keys
DATA = 'Data'
ERROR = 'Errors'
TOKEN = 'Token'
EXCEPTION = 'Exception'
CODE = 'Code'
MESSAGE = 'Message'
STATUS_MESSAGE = 'Status Message'
STATUS_CODE = 'Status Code'

# Roles & Access Levels
SUPER_ADMIN = 1
SURVEYOR = 2
CONTRACTOR = 3
VERIFIER = 4

ENABLE_PRIVILEGE_CHECK = False
PRIVILEGE_CACHE_TIMEOUT = 600
RBAC_API_PREFIX = "/gis/administration/"

PRIVILEGE_WHITELISTED_PATHS = [
    'gis/administration/admin/login',
    'gis/administration/health'
]

# Active Statuses
ACTIVE = 1
INACTIVE = 2

# Password Salting matching ASRLM reference
PASS_PRE_SALT = "@$R!"
PASS_POST_SALT = "l^^M"

