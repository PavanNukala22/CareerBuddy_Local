import logging
from pathlib import Path
from decouple import config
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-biz-english-lms-key-2024')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="127.0.0.1,localhost"
).split(",")

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Core utilities
    'core',
    # Main LMS apps
    'activities',
    'users',
    # Workshop modules
    'GD_app',
    'jam_app',
    'career_app',
    # Django Channels
    'channels',
    # Employer Portal
    'employer_portal',
    'jobs_app',
    'accounts_app',
    'riya_bot',
    'skillup_assessment',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise: gzip/brotli compression + far-future cache headers for static
    # files (biggest win for the large Skill Up pages). Must sit directly after
    # SecurityMiddleware. Active when DEBUG=False; dev still uses runserver.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Adds static/js/content-protection.js to every HTML page (copy / paste /
    # print / select-all / text-selection blocking). See core/middleware.py.
    'core.middleware.ContentProtectionMiddleware',
]

# ── Content protection ─────────────────────────────────────────────────────
# Pages under these path prefixes are left unprotected.
#   /admin/        — Django admin, staff-only back office.
#   /pro/invoice/  — GST tax invoice; customers must be able to print / save
#                    it as PDF (it has its own "Download / Print" button).
CONTENT_PROTECTION_ENABLED = config('CONTENT_PROTECTION_ENABLED', default=True, cast=bool)
CONTENT_PROTECTION_EXEMPT_PATHS = (
    '/admin/',
    '/pro/invoice/',
)

# ── Activities: performance-based progress ─────────────────────────────────
# Progress = the user's score (correct answers / total), averaged over every
# exercise in the activity; see activities/progress.py.
#   'latest' — the most recent attempt counts (shows CURRENT level; can drop).
#   'best'   — the highest attempt counts (never drops on a weaker retry).
ACTIVITY_PROGRESS_SCORING = config('ACTIVITY_PROGRESS_SCORING', default='latest')

ROOT_URLCONF = 'business_english_lms.urls'

ASGI_APPLICATION = 'business_english_lms.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

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
                'career_app.context_processors.subscription_notice',
            ],
        },
    },
]

WSGI_APPLICATION = 'business_english_lms.wsgi.application'


def get_database_config():
    """MySQL is the only supported database.

    SQLite is not an option in any environment: payment activation relies on
    transactional rollback and row-level behaviour that must match production
    exactly, and a local file database silently diverging from MySQL is how a
    deployment ends up running on the wrong data. Asking for SQLite fails loudly
    rather than being quietly ignored.
    """
    db_engine = config('DB_ENGINE', default='mysql').lower()
    if db_engine == 'sqlite' or config('USE_SQLITE', default=False, cast=bool):
        raise ImproperlyConfigured(
            'SQLite is not supported — this project runs on MySQL only. '
            'Remove USE_SQLITE / DB_ENGINE=sqlite from your environment.'
        )

    return {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME', default='business_english_lms'),
        'USER': config('DB_USER', default='root'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        # Without this, Django opens a brand-new MySQL connection (full TCP
        # handshake + auth) on every single request and closes it at the end —
        # including chatbot requests, which touch the DB for the user's
        # employer/resume/interview lookups. Persisting the connection for 60s
        # lets it be reused across requests on the same worker instead.
        # CONN_HEALTH_CHECKS pings the connection before reuse so a connection
        # MySQL has quietly dropped doesn't surface as a request-killing error.
        'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=60, cast=int),
        'CONN_HEALTH_CHECKS': True,
    }


DATABASES = {
    'default': get_database_config(),
}

# ── Cache ───────────────────────────────────────────────────────────────────
# Email-OTP codes and the send / order-creation rate-limiters live in the cache.
# In a multi-process deployment the cache MUST be shared, or each worker keeps
# its own OTP codes and counters — a code set on one worker is unverifiable on
# another, and a per-IP limit of N becomes N×(workers). Set CACHE_URL to a
# shared backend (e.g. redis://127.0.0.1:6379/1) for any multi-process run. The
# in-memory default matches the current single-process setup (Daphne with the
# InMemoryChannelLayer, which is itself single-process).
CACHE_URL = config('CACHE_URL', default='')
# The 'tts' alias holds Buddy's cached speech audio (riya_bot.agents.utils),
# entries of ~100-300 KB each with a 7-day TTL. It is kept out of 'default'
# on purpose: the in-memory default caps at 300 entries and culls a third
# when full, so letting audio share it would evict live OTP codes and
# login-lockout counters. A separate alias means the audio only ever
# competes with other audio.
if CACHE_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': CACHE_URL,
        },
        'tts': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': CACHE_URL,
            'KEY_PREFIX': 'tts',
        },
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'career-buddy-default',
        },
        # Deliberately NOT LocMemCache: that cache lives inside ONE process,
        # so every worker held its own copy, a restart threw all of it away,
        # and `manage.py warm_tts_cache` warmed a cache that died with the
        # command. Buddy therefore re-synthesised the same fixed replies over
        # and over, paying ~1s (and a Sarvam call) each time. A file-backed
        # cache is shared by every worker and survives restarts, which is what
        # turns a repeat reply into a ~15ms hit.
        'tts': {
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': str(BASE_DIR / '.tts_cache'),
            'OPTIONS': {'MAX_ENTRIES': 2000},
        },
    }

# Let users sign in with either their username or their email. The default
# ModelBackend stays as a fallback so nothing that relied on it breaks.
AUTHENTICATION_BACKENDS = [
    'users.backends.EmailOrUsernameModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
    # Enforces the uppercase / lowercase / number / special-character rules the
    # registration pages show as a live checklist. See users/password_validators.py.
    {'NAME': 'users.password_validators.PasswordComplexityValidator'},
    # Caps password length at 8. With MinimumLengthValidator above this makes
    # passwords exactly 8 characters — a deliberate product decision; see the
    # note on MAX_PASSWORD_LENGTH in users/password_validators.py.
    {'NAME': 'users.password_validators.MaximumLengthValidator'},
]

# ── Security: Frame Options & Popups ───────────────────────────────────────────
# Allow same-origin iframes so Razorpay checkout modal can load inside the page.
# The default (DENY) blocks Razorpay's injected iframe and shows about:blank.
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Allow cross-origin popups (like payment gateways) to communicate with the page.
# Without this, Django's default 'same-origin' policy blocks the payment window.
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'

# SR-06 fix: Django's cookie/HTTPS security flags default to False/off and were
# never set anywhere in this file, so a production deploy (DEBUG=False) would
# still send session and CSRF cookies over plain HTTP with no HSTS. Scoped to
# `not DEBUG` so local/dev (DEBUG=True) is unaffected.
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
    BASE_DIR / 'activities' / 'static',
    BASE_DIR / 'GD_app' / 'static',
    BASE_DIR / 'jam_app' / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise storage: compress static files (gzip + brotli) at `collectstatic`.
# Deliberately NOT the *Manifest* variant: this app references some static
# files that don't exist on disk (e.g. img/favicon.ico, model/*.glb via
# {% static %}). Manifest storage does a strict existence check on every
# {% static %} and raises, 500-ing the whole site; the plain compressed storage
# serves what exists (compressed) and lets missing files 404 harmlessly.
# ── Interview recordings → MinIO (S3-compatible) ───────────────────────────
# Only ResumeInterviewSession.interview_video uses the 'interview_videos'
# alias; résumés, selfies and logos stay on the local MEDIA_ROOT disk. With
# MINIO_ENDPOINT_URL unset the alias falls back to plain filesystem storage so
# local dev needs no MinIO. MINIO_PUBLIC_URL is deliberately separate: it is
# used only for browser-facing links (e.g. behind an Nginx proxy) while the
# internal endpoint remains the private loopback MinIO API address for boto3.
# The bucket must stay private: the file is always streamed through the
# access-checked view in core/media_views.py, never linked to directly.
MINIO_ENDPOINT_URL = config('MINIO_ENDPOINT_URL', default='').strip()
MINIO_PUBLIC_URL = config('MINIO_PUBLIC_URL', default='').strip().rstrip('/')
if MINIO_ENDPOINT_URL:
    storage_options = {
        'access_key': config('MINIO_ACCESS_KEY', default=''),
        'secret_key': config('MINIO_SECRET_KEY', default=''),
        'bucket_name': config('MINIO_BUCKET', default='careerbuddy-media'),
        'endpoint_url': MINIO_ENDPOINT_URL,
        'addressing_style': 'path',
        'file_overwrite': False,
        'default_acl': None,
        'querystring_auth': False,
    }
    if MINIO_PUBLIC_URL:
        public_host = MINIO_PUBLIC_URL.split('://', 1)[-1]
        storage_options['custom_domain'] = public_host
        if MINIO_PUBLIC_URL.startswith('http://') or MINIO_PUBLIC_URL.startswith('https://'):
            # django-storages concatenates this verbatim: it wants 'https:',
            # not 'https'. Without the colon the URL came out as
            # 'https//host/...', which a browser resolves as a RELATIVE path —
            # hence requests like /employer/applications/34/https//careerbuddy4u.com/...
            # and a 404 for every recording.
            storage_options['url_protocol'] = MINIO_PUBLIC_URL.split('://', 1)[0] + ':'
    _interview_video_storage = {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': storage_options,
    }
else:
    _interview_video_storage = {'BACKEND': 'django.core.files.storage.FileSystemStorage'}

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
    'interview_videos': _interview_video_storage,
}
# Cache static for a day; no content-hashing here, so keep it modest to avoid
# serving stale assets after a deploy. (ETag revalidation still yields 304s.)
# In DEBUG this must be 0: a day-long cache kept serving each developer's OLD
# riya_assistant.css / BOTscript.js after a pull, so the chatbot rendered with
# stale (or no) styling until the browser cache expired.
WHITENOISE_MAX_AGE = 0 if DEBUG else 86400

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Sarvam AI API key (set in .env file)
SARVAM_API_KEY = config('SARVAM_API_KEY', default='')
SARVAM_MODEL = config('SARVAM_MODEL', default='sarvam-105b')

# Razorpay payment keys (TEST mode — set in .env file)
RAZORPAY_KEY_ID = config('RAZORPAY_KEY_ID', default='')
RAZORPAY_KEY_SECRET = config('RAZORPAY_KEY_SECRET', default='')
# PAY-02 fix: webhook signing secret (Razorpay Dashboard → Webhooks). Without
# this the server-side webhook (BUG-03) always rejected with HTTP 500 because
# settings never loaded it. Set RAZORPAY_WEBHOOK_SECRET in .env for go-live.
RAZORPAY_WEBHOOK_SECRET = config('RAZORPAY_WEBHOOK_SECRET', default='')


# LanguageTool (optional, free public API used for offline grammar checks)
LANGUAGETOOL_API_URL = config('LANGUAGETOOL_API_URL', default='https://api.languagetool.org/v2/check')

LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = '/'

# ── Email Configuration (SMTP — ZeptoMail) ──────────────────────────────────
# Provider-agnostic: every value comes from the environment, so switching
# providers (or between ZeptoMail's port 587/STARTTLS and 465/SSL) is a .env
# change only. See .env.example and docs/ZeptoMail_SMTP_Setup.pdf.
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.zeptomail.in')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
# ZeptoMail's port 465 is implicit-SSL, not STARTTLS — use EMAIL_USE_SSL=True
# with EMAIL_USE_TLS=False and EMAIL_PORT=465 for that instead of 587/TLS.
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
if EMAIL_USE_TLS and EMAIL_USE_SSL:
    raise ImproperlyConfigured(
        'EMAIL_USE_TLS and EMAIL_USE_SSL cannot both be True — pick TLS for '
        'port 587 or SSL for port 465, not both.'
    )
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
# PAY-P05: payment receipts are sent inline on both activation paths. Without a
# timeout the socket falls back to the system default, which can be minutes — on
# the callback path that stalls the customer's confirmation after their money has
# been taken, and on the webhook path it can push the handler past Razorpay's
# timeout, so the event is retried and the receipt is lost to the idempotency
# short-circuit.
EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', default=10, cast=int)
# The sender address shown to recipients. This must NOT fall back to
# EMAIL_HOST_USER: for ZeptoMail (and most transactional SMTP providers) the
# SMTP username is the literal string "emailapikey", not a mailbox, so that
# fallback used to turn every From: header into the invalid address
# "emailapikey" the moment Gmail's SMTP was swapped for ZeptoMail's.
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@careerbuddy4u.com')

if not DEBUG and not EMAIL_HOST_PASSWORD:
    logging.getLogger(__name__).warning(
        'EMAIL_HOST_PASSWORD is not set in production — welcome emails, '
        'payment receipts and application confirmations will fail to send '
        'until ZeptoMail credentials are added to .env.'
    )


# ── Logging ───────────────────────────────────────────────────────────────
# The payment code raises warnings that mean money is at stake — REFUND
# REQUIRED, amount and ownership mismatches, ignored downgrades, receipt
# delivery failures. Without a configured handler those went to stderr and were
# lost with the terminal, which is how a dead SMTP password stayed invisible for
# hours. Payment and mail events are kept in their own rotating file.
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {'format': '{asctime} {levelname:<8} {name} {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'detailed'},
        'payments_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_DIR / 'payments.log'),
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 10,
            'encoding': 'utf-8',
            'formatter': 'detailed',
        },
        'errors_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_DIR / 'errors.log'),
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'encoding': 'utf-8',
            'formatter': 'detailed',
            'level': 'WARNING',
        },
    },
    'loggers': {
        # Payments, subscriptions and receipt delivery all log from here.
        'career_app.views': {
            'handlers': ['console', 'payments_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'users.views': {
            'handlers': ['console', 'payments_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'errors_file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
    'root': {'handlers': ['console', 'errors_file'], 'level': 'WARNING'},
}

# ── GST tax invoice (seller details) ───────────────────────────────────────
# Printed on the GST invoice issued for every paid subscription. These are the
# supplier's legal particulars and must be filled with real values before
# invoices are shown to business customers claiming input tax credit. GST at
# GST_RATE is charged on the base price and, absent a buyer GSTIN/state, is
# treated as an intra-state supply and split evenly into CGST and SGST.
GST_RATE = config('GST_RATE', default=0.18, cast=float)
COMPANY_LEGAL_NAME = config('COMPANY_LEGAL_NAME', default='Career Buddy')
COMPANY_GSTIN = config('COMPANY_GSTIN', default='')
COMPANY_ADDRESS = config('COMPANY_ADDRESS', default='')
COMPANY_STATE = config('COMPANY_STATE', default='')
COMPANY_STATE_CODE = config('COMPANY_STATE_CODE', default='')
COMPANY_EMAIL = config('COMPANY_EMAIL', default=DEFAULT_FROM_EMAIL)
# SAC 999293 — "Commercial training and coaching services".
COMPANY_SAC_CODE = config('COMPANY_SAC_CODE', default='999293')

# ── CSRF & Proxy Settings ──────────────────────────────────────────────────
CSRF_TRUSTED_ORIGINS = [
    'https://careerbuddy4u.com',
    'https://www.careerbuddy4u.com',
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
