"""
Django settings for heranow project.

Generated by 'django-admin startproject' using Django 3.0.3.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os
from pathlib import Path
import environ


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
for scheme in ["postgres", "psql", "postgresql", "pgsql"]:
    env.DB_SCHEMES[scheme] = "django.db.backends.postgresql_psycopg2"
# reading .env file
environ.Env.read_env(env_file=str(BASE_DIR / ".env"))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
with open(BASE_DIR / env.str("DJANGO_KEY"), "r") as key_file:
    SECRET_KEY = key_file.read()

with open(BASE_DIR / env.str("GITHUB_APP_KEY_FILE"), "r") as keyfile:
    GITHUB_APP_KEY = keyfile.read()
with open(BASE_DIR / env.str("GITHUB_APP_ID_FILE"), "r") as appid_file:
    GITHUB_APP_ID = appid_file.read()


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DJANGO_DEBUG")

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

INTERNAL_IPS = env.list("DJANGO_INTERNAL_IPS")

DATA_UPLOAD_MAX_MEMORY_SIZE = None
# Application definition
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"

INSTALLED_APPS = [
    "dashboard",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "analytical",
    "django_extensions",
    "django_plotly_dash.apps.DjangoPlotlyDashConfig",
    "dpd_static_support",
    "bootstrap4",
    "django_tables2",
    "django_cleanup.apps.CleanupConfig",
]

MIDDLEWARE = [
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_plotly_dash.middleware.ExternalRedirectionMiddleware",
    "django_plotly_dash.middleware.BaseMiddleware",
]

ROOT_URLCONF = "heranow.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.media",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "heranow.wsgi.application"


# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases
database = env.db_url("DJANGO_DB")
database['CONN_MAX_AGE'] = 60
DATABASES = {"default": database}


# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"
STATICFILES_DIRS = [
    BASE_DIR / "dashboard" / "static",
    # os.path.join(BASE_DIR, "static"),
]
# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "django.contrib.staticfiles.finders.DefaultStorageFinder",
    "django_plotly_dash.finders.DashAssetFinder",
    "django_plotly_dash.finders.DashComponentFinder",
    "django_plotly_dash.finders.DashAppDirectoryFinder",
]
# django_plotly_dash options
X_FRAME_OPTIONS = "SAMEORIGIN"

# Plotly components containing static content that should
# be handled by the Django staticfiles infrastructure

PLOTLY_COMPONENTS = [
    # Common components
    "dash_core_components",
    "dash_html_components",
    "dash_renderer",
    # django-plotly-dash components
    "dpd_components",
    # static support if serving local assets
    "dpd_static_support",
    # Other components, as needed
    "dash_bootstrap_components",
]

NOTEBOOK_ARGUMENTS = [
    # exposes IP and port
    '--ip=0.0.0.0',
    '--port=8882',
    # disables the browser
    '--no-browser',
]
# CELERY Configuration
CELERY_BROKER_URL = env.str("CELERY_REDIS_URL")
CELERY_RESULT_BACKEND = env.str("CELERY_REDIS_URL")
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_WORKER_MAX_TASKS_PER_CHILD = 20
