"""
Django settings for the Fire Conference backend.
"""

from pathlib import Path

from decouple import Csv, config
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('DJANGO_SECRET_KEY', default='django-insecure-change-this-in-production')
DEBUG = config('DJANGO_DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Railway (como Heroku) termina o TLS no proxy e encaminha pro app por HTTP
# simples com esse header — sem isso, request.is_secure() dá False mesmo em
# HTTPS, e o CSRF do Django rejeita todo POST (ex: login do admin) porque o
# esquema que ele calcula (http) não bate com o Origin que o navegador manda
# (https).
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Origens explicitamente confiáveis pra CSRF — precisa do próprio domínio do
# backend (é ele que serve o formulário de login do /admin/).
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',

    # Local apps
    'apps.core',
    'apps.lotes',
    'apps.users',
    'apps.inscricoes',
]

AUTH_USER_MODEL = 'users.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
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

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# DATABASE_URL takes priority when set (Railway injects it once Postgres is attached);
# falls back to local SQLite otherwise — same pattern as AreaMais and Mio-Festa-2026.
DATABASE_URL = config('DATABASE_URL', default='')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

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

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:5173,http://127.0.0.1:5173',
    cast=Csv(),
)

# Pix copia-e-cola (ADR-0001) — placeholders para dev/teste local.
# PRECISA ser configurado com a chave Pix real da igreja antes de qualquer deploy.
_PIX_KEY_PLACEHOLDER = 'chave-pix-nao-configurada@example.com'
PIX_KEY = config('PIX_KEY', default=_PIX_KEY_PLACEHOLDER)
PIX_MERCHANT_NAME = config('PIX_MERCHANT_NAME', default='FIRE CONFERENCE')
PIX_MERCHANT_CITY = config('PIX_MERCHANT_CITY', default='SAO PAULO')

if not DEBUG and PIX_KEY == _PIX_KEY_PLACEHOLDER:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured('PIX_KEY não configurada — defina a chave Pix real antes de deployar.')

# Supabase Storage (comprovantes) — usa a service_role key (bypassa RLS), nunca
# exposta ao frontend. Buscar em Project Settings > API no painel do Supabase.
SUPABASE_URL = config('SUPABASE_URL', default='')
SUPABASE_SERVICE_ROLE_KEY = config('SUPABASE_SERVICE_ROLE_KEY', default='')
SUPABASE_COMPROVANTES_BUCKET = 'comprovantes'

if not DEBUG and not (SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY):
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured('SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY não configurados.')

# E-mail (ingresso) — sem RESEND_API_KEY, cai no backend Django padrão (console em dev).
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='ingressos@fireconference.local')
RESEND_API_KEY = config('RESEND_API_KEY', default='')

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
}
