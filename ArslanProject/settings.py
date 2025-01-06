"""
Django settings for ArslanProject project.

Generated by 'django-admin startproject' using Django 4.2.2.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

import logging
import os
from pathlib import Path
from dotenv import load_dotenv


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

dotenv_path = os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = str(os.getenv('SECRET_KEY')) #'django-insecure-5a3gd-zj_#1h$bstcn)(o3a7--(j!95a(g(kbz-e=khb-%_qwi'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['0.0.0.0', '127.0.0.1', '192.168.150.43', 'arslan', '192.168.8.21']


# Application definition

INSTALLED_APPS = [
    'daphne',
    'ArslanTakipApp',
    'StokApp',
    'adminlte3',
    'adminlte3_theme',
    'tabulator',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'django.contrib.humanize',
    'guardian',
    'django_celery_beat',
    'django_celery_results',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ArslanProject.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'ArslanProject.wsgi.application'
ASGI_APPLICATION = "ArslanProject.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("localhost", 6379)],
        },
    },
}

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'arslanBy',
        'USER': 'arslan',
        'PASSWORD': 'gqTYe5HdX0VQ',
        'HOST': '192.168.150.230', 
        'PORT': '5432',
    },
    'dies': {
        'ENGINE': 'mssql',
        'NAME': 'ARSLAN_2025',
        'USER': 'arsbyz',
        'PASSWORD': '123',
        'HOST': '192.168.180.200', 
        'PORT': '1433',
        "OPTIONS": {"driver": "ODBC Driver 17 for SQL Server", 
        },
    },
    'dms': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'DMS',
        'USER': 'arslan',
        'PASSWORD': 'gqTYe5HdX0VQ',
        'HOST': '192.168.150.230', 
        'PORT': '5432',
    }
}

DATABASE_ROUTERS = [
    'ArslanProject.router.KalipMsRouter',
]


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'tr-TR'

TIME_ZONE = 'Turkey'

DATETIME_FORMAT = 'd-m-Y H:M:S' #'%d-%m-%Y %H:%M:%S' 
USE_L10N = False
USE_TZ = False

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = 'static/'
STATICFILES_DIRS = (
    # This defines a prefix so the url paths will become `/static/node_modules/...`
    ('node_modules', os.path.join(BASE_DIR, 'node_modules/')),
)

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = 'media/'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = "/login_success"
LOGOUT_REDIRECT_URL = "/" 

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
)

# email configs
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_BACKEND = "mailer.backend.DbBackend"
EMAIL_HOST = 'webmail.arslanaluminyum.com'
EMAIL_HOST_USER = 'yazilim@arslanaluminyum.com' #str(os.getenv('EMAIL_USER'))
EMAIL_HOST_PASSWORD = 'rHE7Je' #str(os.getenv('EMAIL_PASSWORD'))
EMAIL_USE_TLS = True
EMAIL_TLS_VERSION = 'TLSv1.2'
EMAIL_PORT = 587
EMAIL_TIMEOUT = None
DEFAULT_FROM_EMAIL = 'yazilim@arslanaluminyum.com'


# Celery configurations
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Istanbul'

# Django Celery Results configuration
CELERY_RESULT_BACKEND = 'django-db'

# Celery Beat Configuration
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'check-email-every-minute': {
        'task': 'ArslanTakipApp.tasks.start_email_listener',
        'schedule': crontab(minute='*/10'),
    },
    'check-rapor': {
        'task': 'ArslanTakipApp.tasks.start_rapor_listener',
        'schedule': crontab(minute=0, hour='2,5,8,11,14,17,20,23')
    },
    'check-die': {
        'task': 'ArslanTakipApp.tasks.start_die_listener',
        'schedule': crontab(minute='*/30'),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://localhost:6379/1",
    }
}

logger = logging.getLogger('django.email')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': 'error.log',
        },
        'file2': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
        'ArslanTakipApp': {  # Replace 'yourapp' with the name of your Django app
            'handlers': ['file2'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}