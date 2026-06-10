"""
Django settings for lumberbank project.
"""

from pathlib import Path
import dj_database_url
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,192.168.15.25', cast=Csv())


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'widget_tweaks',
    'storages',
    # Local apps
    'accounts',
    'projects',
    'jobs',
    'products',
    'core',
    'cutlist',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'lumberbank.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'lumberbank.wsgi.application'


# Database — PostgreSQL

import os as _os
_database_url = _os.environ.get('DATABASE_URL', '')
if _database_url.startswith('postgres'):
    DATABASES = {'default': dj_database_url.parse(_database_url, conn_max_age=600)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='lumberbank_db'),
            'USER': config('DB_USER', default='lumberbank_user'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }


# Custom user model

AUTH_USER_MODEL = 'accounts.User'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'projects:project_list'
LOGOUT_REDIRECT_URL = 'accounts:login'


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalisation

LANGUAGE_CODE = 'en-nz'
TIME_ZONE = 'Pacific/Auckland'
USE_I18N = True
USE_TZ = True


# Static and media files

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Local media defaults (overridden below when USE_SPACES=True)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Storage backends
# In production set USE_SPACES=True and supply SPACES_* env vars.
# Locally the filesystem is used; MEDIA_URL/MEDIA_ROOT above apply.
#
# DO Spaces env vars needed in production:
#   USE_SPACES=True
#   SPACES_KEY=<access-key-id>
#   SPACES_SECRET=<secret-access-key>
#   SPACES_BUCKET=<bucket-name>
#   SPACES_REGION=syd1          (or whichever region your bucket is in)

_USE_SPACES = config('USE_SPACES', default=False, cast=bool)

if _USE_SPACES:
    _spaces_region = config('SPACES_REGION', default='syd1')
    _spaces_bucket = config('SPACES_BUCKET', default='')
    AWS_ACCESS_KEY_ID       = config('SPACES_KEY',    default='')
    AWS_SECRET_ACCESS_KEY   = config('SPACES_SECRET', default='')
    AWS_STORAGE_BUCKET_NAME = _spaces_bucket
    AWS_S3_REGION_NAME      = _spaces_region
    AWS_S3_ENDPOINT_URL     = f'https://{_spaces_region}.digitaloceanspaces.com'
    AWS_DEFAULT_ACL         = 'public-read'
    AWS_S3_FILE_OVERWRITE   = False
    AWS_QUERYSTRING_AUTH    = False
    MEDIA_URL = f'https://{_spaces_bucket}.{_spaces_region}.digitaloceanspaces.com/media/'
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
            'OPTIONS': {'location': 'media'},
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }
else:
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }


# Default primary key

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Email (drawing upload notifications)

# Email — Office 365 SMTP
# In production set these in your .env:
#   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
#   EMAIL_HOST_USER=noreply@lumberbank.co.nz        (must be a valid O365 mailbox)
#   EMAIL_HOST_PASSWORD=<app-password or SMTP auth password>
# Note: Basic SMTP auth must be enabled for the mailbox in M365 Admin → Users → Active users
#       → <user> → Mail → Manage email apps → Authenticated SMTP.
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend',
)
EMAIL_HOST          = config('EMAIL_HOST',          default='smtp.office365.com')
EMAIL_PORT          = config('EMAIL_PORT',          default=587, cast=int)
EMAIL_USE_TLS       = config('EMAIL_USE_TLS',       default=True, cast=bool)
EMAIL_HOST_USER     = config('EMAIL_HOST_USER',     default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL  = config('DEFAULT_FROM_EMAIL',  default='noreply@lumberbank.co.nz')

DETAILING_TEAM_EMAIL = config('DETAILING_TEAM_EMAIL', default='quotes@lumberbank.co.nz')
