"""
Django settings for core project.
"""

import base64
import hashlib
import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
APP_VERSION = '1.6.2'


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() in ('true', '1', 't')

_em_teste = 'test' in sys.argv
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '').strip()
if not SECRET_KEY:
    if not DEBUG and not _em_teste:
        raise ImproperlyConfigured('DJANGO_SECRET_KEY é obrigatório quando DEBUG=False.')
    SECRET_KEY = 'django-insecure-desenvolvimento-local-apenas'

_hosts_configurados = [host.strip() for host in os.getenv('DJANGO_ALLOWED_HOSTS', '').split(',') if host.strip()]
if not _hosts_configurados:
    if not DEBUG and not _em_teste:
        raise ImproperlyConfigured('DJANGO_ALLOWED_HOSTS é obrigatório quando DEBUG=False.')
    _hosts_configurados = ['localhost', '127.0.0.1', '[::1]']
ALLOWED_HOSTS = _hosts_configurados

# Domínios confiáveis para CSRF (necessário para requisições com Origin no Django 4+)
_trusted_origins = [
    h.strip() for h in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if h.strip()
]
if DEBUG or _em_teste:
    _trusted_origins.extend([
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'http://localhost:8000',
        'http://127.0.0.1:8000',
    ])
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(_trusted_origins))

# Segurança em produção — ativas quando DEBUG=False
if not DEBUG:
    # Necessário quando atrás de proxy reverso (Caddy, Nginx, etc.)
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = not _em_teste
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv('DJANGO_SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'estoque',
    'notifications',
    'omie',
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

ROOT_URLCONF = 'core.urls'

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
                'estoque.context_processors.estoque_baixo',
                'estoque.context_processors.app_info',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.getenv('DJANGO_DB_NAME', str(BASE_DIR / 'data' / 'db.sqlite3')),
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internacionalização
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Whitenoise — compressão e cache de estáticos
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

FRONTEND_DIST_DIR = BASE_DIR / 'frontend' / 'dist'
STATICFILES_DIRS = [FRONTEND_DIST_DIR] if FRONTEND_DIST_DIR.exists() else []

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# ── Notificações ─────────────────────────────────────────────────────────────
NOTIFICATION_WEBHOOK_URL = os.getenv('NOTIFICATION_WEBHOOK_URL', '')
NOTIFICATION_TOKEN = os.getenv('NOTIFICATION_TOKEN', '')

# ── Integração Omie ──────────────────────────────────────────────────────────
OMIE_APP_KEY = os.getenv('OMIE_APP_KEY', '')
OMIE_APP_SECRET = os.getenv('OMIE_APP_SECRET', '')
OMIE_ENCRYPTION_KEY = os.getenv('OMIE_ENCRYPTION_KEY', '').strip()
if not OMIE_ENCRYPTION_KEY:
    if not DEBUG and not _em_teste:
        raise ImproperlyConfigured('OMIE_ENCRYPTION_KEY é obrigatória quando DEBUG=False.')
    OMIE_ENCRYPTION_KEY = base64.urlsafe_b64encode(hashlib.sha256(SECRET_KEY.encode()).digest()).decode()
