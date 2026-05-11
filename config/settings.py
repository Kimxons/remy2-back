from pathlib import Path
import os
from decimal import Decimal
import environ
from django.core.exceptions import ImproperlyConfigured
from celery.schedules import crontab
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()

# -----------------------------
# Load .env safely
# -----------------------------
if not os.getenv('DIGITALOCEAN_APP_ID'):
    env_file = os.path.join(BASE_DIR, '.env')
    if os.path.exists(env_file):
        environ.Env.read_env(env_file)

# -----------------------------
# Core settings
# -----------------------------
SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)

ENVIRONMENT = env('ENVIRONMENT', default='production').lower()
IS_PRODUCTION = ENVIRONMENT == 'production'

if IS_PRODUCTION and DEBUG:
    raise ImproperlyConfigured('DEBUG must be False in production.')

if IS_PRODUCTION and len(set(SECRET_KEY)) < 5:
    raise ImproperlyConfigured('SECRET_KEY is too weak for production.')

if IS_PRODUCTION and (len(SECRET_KEY) < 50 or SECRET_KEY.startswith('django-insecure-')):
    raise ImproperlyConfigured('SECRET_KEY must be long, random, and production-safe.')

FRONTEND_URL = env(
    'FRONTEND_URL',
    default='https://remyink.co.ke' if IS_PRODUCTION else 'http://localhost:3000'
)
BACKEND_BASE_URL = env(
    'BACKEND_BASE_URL',
    default='https://api.remyink.co.ke' if IS_PRODUCTION else 'http://127.0.0.1:8000'
)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

if IS_PRODUCTION and not ALLOWED_HOSTS:
    raise ImproperlyConfigured('ALLOWED_HOSTS must be set in production.')


def _env_first(*keys: str, default=None):
    for key in keys:
        value = env(key, default=None)
        if value not in (None, ''):
            return value
    return default

# -----------------------------
# Paystack
# -----------------------------
PAYSTACK_CALLBACK_URL = env(
    'PAYSTACK_CALLBACK_URL',
    default='https://remyink-9gqjd.ondigitalocean.app/payment/verify'
)
PAYSTACK_SECRET_KEY = _env_first(
    'PAYSTACK_SECRET_KEY_LIVE' if IS_PRODUCTION else 'PAYSTACK_SECRET_KEY_TEST',
    'PAYSTACK_SECRET_KEY',
    'PAYSTACK_SECRET_KEY_LIVE',
    'PAYSTACK_SECRET_KEY_TEST',
    default='',
)
PAYSTACK_PUBLIC_KEY = _env_first(
    'PAYSTACK_PUBLIC_KEY_LIVE' if IS_PRODUCTION else 'PAYSTACK_PUBLIC_KEY_TEST',
    'PAYSTACK_PUBLIC_KEY',
    'PAYSTACK_PUBLIC_KEY_LIVE',
    'PAYSTACK_PUBLIC_KEY_TEST',
    default='',
)
PAYSTACK_WEBHOOK_SECRET = env('PAYSTACK_WEBHOOK_SECRET')

PAYSTACK_INITIALIZE_URL = 'https://api.paystack.co/transaction/initialize'
PAYSTACK_VERIFY_URL = 'https://api.paystack.co/transaction/verify/'

SESSION_COOKIE_DOMAIN = env(
    'SESSION_COOKIE_DOMAIN',
    default='.remyink.co.ke' if IS_PRODUCTION else None,
)
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=IS_PRODUCTION)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=IS_PRODUCTION)
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=IS_PRODUCTION)
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=31536000 if IS_PRODUCTION else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=IS_PRODUCTION)
SECURE_HSTS_PRELOAD = env.bool('SECURE_HSTS_PRELOAD', default=IS_PRODUCTION)

CLIENT_FEE_PERCENTAGE = 0.20
FREELANCER_PAYOUT_PERCENTAGE = 0.80
DEFAULT_CURRENCY = 'USD'
DEFAULT_CURRENCY_SYMBOL = '$'

# -----------------------------
# JWT
# -----------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=7),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": (
        "rest_framework_simplejwt.tokens.AccessToken",
    ),
}

# -----------------------------
# Apps
# -----------------------------
INSTALLED_APPS = [
    'daphne',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'corsheaders',

    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',

    'channels',
    'django_celery_beat',
    'django_filters',

    'user_module.apps.UserModuleConfig',
    'jobs.apps.JobsConfig',
    'orders.apps.OrdersConfig',
    'chat.apps.ChatConfig',
    'pay_freelancer.apps.PayFreelancerConfig',
    'payment_gateway',
    'payments',
    'notifications',
]

if DEBUG:
    INSTALLED_APPS.append('django_extensions')

# -----------------------------
# ASGI / WSGI
# -----------------------------
ASGI_APPLICATION = "config.asgi.application"
WSGI_APPLICATION = "config.wsgi.application"

# -----------------------------
# Channels / Redis
# -----------------------------
USE_REDIS_CHANNEL_LAYER = env.bool('USE_REDIS_CHANNEL_LAYER', default=IS_PRODUCTION)
CHANNEL_REDIS_URL = env(
    "CHANNEL_REDIS_URL",
    default="redis://127.0.0.1:6379/1"
)

if USE_REDIS_CHANNEL_LAYER:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [CHANNEL_REDIS_URL],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }

# -----------------------------
# Auth
# -----------------------------
AUTH_USER_MODEL = 'user_module.User'
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']

# -----------------------------
# Celery
# -----------------------------
CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = env('TIME_ZONE')

CELERY_BEAT_SCHEDULE = {
    'check-and-process-auto-payouts': {
        'task': 'pay_freelancer.tasks.check_and_process_auto_payouts',
        'schedule': crontab(minute='0', hour='0'),
        'options': {'queue': 'remyink_payouts'},
    },
}

# -----------------------------
# Middleware
# -----------------------------
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

# -----------------------------
# Helpers
# -----------------------------
def _csv_env_list(key: str) -> list[str]:
    raw = env(key, default="")
    return [i.strip() for i in str(raw).split(",") if i.strip()]

# -----------------------------
# CORS / CSRF
# -----------------------------
CORS_ALLOWED_ORIGINS = _csv_env_list('CORS_ALLOWED_ORIGINS')
CSRF_TRUSTED_ORIGINS = _csv_env_list('CSRF_TRUSTED_ORIGINS')
CORS_ALLOWED_ORIGIN_REGEXES = _csv_env_list('CORS_ALLOWED_ORIGIN_REGEXES')

CORS_ALLOW_CREDENTIALS = env.bool('CORS_ALLOW_CREDENTIALS', default=True)
CORS_ALLOW_ALL_ORIGINS = env.bool('CORS_ALLOW_ALL_ORIGINS', default=False)

if IS_PRODUCTION and CORS_ALLOW_ALL_ORIGINS:
    raise ImproperlyConfigured("CORS_ALLOW_ALL_ORIGINS cannot be True in production.")

if IS_PRODUCTION and not CORS_ALLOW_ALL_ORIGINS and CORS_ALLOW_CREDENTIALS:
    if not CORS_ALLOWED_ORIGINS and not CORS_ALLOWED_ORIGIN_REGEXES:
        raise ImproperlyConfigured(
            "Set CORS_ALLOWED_ORIGINS or CORS_ALLOWED_ORIGIN_REGEXES in production."
        )

if IS_PRODUCTION and not CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured("CSRF_TRUSTED_ORIGINS must be set in production.")

# -----------------------------
# REST FRAMEWORK
# -----------------------------
ROOT_URLCONF = 'config.urls'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'chat_anon': '6000/hour',
        'chat_user': '20000/hour',
        'orders_anon': '2000/hour',
        'orders_user': '10000/hour',
    },
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend'
    ],
}

# -----------------------------
# Cache
# -----------------------------
CACHES = {
    "default": env.cache('CACHE_URL'),
}

# -----------------------------
# Templates
# -----------------------------
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

# -----------------------------
# API docs
# -----------------------------
SPECTACULAR_SETTINGS = {
    'TITLE': 'RemyInk API',
    'DESCRIPTION': 'API documentation for the RemyInk freelance platform',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# -----------------------------
# Database
# -----------------------------
DATABASES = {
    'default': env.db('DATABASE_URL'),
}

# -----------------------------
# Password validation
# -----------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# -----------------------------
# i18n
# -----------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = env('TIME_ZONE')
USE_I18N = True
USE_TZ = True

# -----------------------------
# Static / Media
# -----------------------------
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATIC_DIR = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = [STATIC_DIR] if os.path.isdir(STATIC_DIR) else []

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# -----------------------------
# Default auto field
# -----------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -----------------------------
# Currency defaults
# -----------------------------
USD_EXCHANGE_RATE = Decimal('1.00')