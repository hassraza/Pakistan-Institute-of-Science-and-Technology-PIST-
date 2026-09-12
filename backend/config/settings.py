"""Django settings for the PIST admission ecosystem project."""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/

DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

if DEBUG:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'pist-dev-secret-key-only-for-local-development')
else:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise RuntimeError('SECRET_KEY must be configured in production.')

DEFAULT_ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '[::1]',
    'testserver',
    'hasaza555.pythonanywhere.com',
]
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('ALLOWED_HOSTS', ','.join(DEFAULT_ALLOWED_HOSTS)).split(',')
    if host.strip()
]

DEFAULT_CSRF_TRUSTED_ORIGINS = ['https://hasaza555.pythonanywhere.com']
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        'CSRF_TRUSTED_ORIGINS', ','.join(DEFAULT_CSRF_TRUSTED_ORIGINS)
    ).split(',')
    if origin.strip()
]

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
    if origin.strip()
]


# Application definition

INSTALLED_APPS = [
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'django_filters',
    'main',
    'admissions',
    'university_admin',
    'students',
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'admissions.context_processors.site_context',
                'students.context_processors.student_portal_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

LOGIN_URL = '/university-admin/login/'
LOGIN_REDIRECT_URL = '/university-admin/'
LOGOUT_REDIRECT_URL = '/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

if DEBUG:
    PIST_EXTERNAL_API_KEY = os.environ.get('PIST_EXTERNAL_API_KEY', 'pist-dev-integration-key')
else:
    PIST_EXTERNAL_API_KEY = os.environ.get('PIST_EXTERNAL_API_KEY')
    if not PIST_EXTERNAL_API_KEY:
        raise RuntimeError('PIST_EXTERNAL_API_KEY must be configured for production integrations.')

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'PIST University Admission Integration API',
    'DESCRIPTION': (
        'Centralized Admission Platform (PakUniPortal) API integration layer for '
        'Pakistan Institute of Science and Technology (PIST). Allows external platforms '
        'to create student accounts, submit applications, check status, retrieve notifications, and access roll slips.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SECURITY': [{'ApiKeyAuth': []}],
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'ApiKeyAuth': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'X-API-KEY',
                'description': 'Secret API key for PakUniPortal integration authentication.',
            }
        }
    },
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    },
}


# Email
# https://docs.djangoproject.com/en/6.1/topics/email/#topic-email-configuration

if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
    if not os.environ.get('EMAIL_HOST'): 
        raise RuntimeError('Email configuration is required in production. Set EMAIL_HOST and related settings.')

STUDENT_MIN_AGE = 15
STUDENT_MAX_AGE = 100
STUDENT_MIN_NAME_LENGTH = 3
STUDENT_ID_PREFIX = 'PIST-STU'
STUDENT_PHOTO_MAX_SIZE_MB = 2
ACADEMIC_DOCUMENT_MAX_SIZE_MB = 5
PIST_ADMISSION_YEAR = int(os.environ.get('PIST_ADMISSION_YEAR', '2026'))
LOGIN_ATTEMPT_LIMIT = 5
LOGIN_ATTEMPT_WINDOW_MINUTES = 10
SESSION_COOKIE_HTTPONLY = True

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') if os.environ.get('USE_HTTPS_PROXY', 'False').lower() == 'true' else None
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True' if not DEBUG else 'False').lower() == 'true'
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'True' if not DEBUG else 'False').lower() == 'true'
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True' if not DEBUG else 'False').lower() == 'true'
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000' if not DEBUG else '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'True' if not DEBUG else 'False').lower() == 'true'
SECURE_HSTS_PRELOAD = os.environ.get('SECURE_HSTS_PRELOAD', 'True' if not DEBUG else 'False').lower() == 'true'


#CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_ALL_ORIGINS = False