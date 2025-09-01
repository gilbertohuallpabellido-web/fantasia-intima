"""
Django settings for mi_proyecto project.
"""

from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(os.path.join(BASE_DIR, ".env"))

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-tu-clave-secreta-para-desarrollo')

# --- Lógica de Entorno a Prueba de Fallos ---
IS_PRODUCTION = 'RENDER' in os.environ
DEBUG = not IS_PRODUCTION

# --- Configuración de Hosts para Producción y Desarrollo ---
ALLOWED_HOSTS = []
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS = [f'https://{RENDER_EXTERNAL_HOSTNAME}']

if not IS_PRODUCTION:
    ALLOWED_HOSTS.append('*')


# Application definition
INSTALLED_APPS = [
    # 'jazzmin', # <-- ELIMINADO
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'mi_app',
    'mptt',
    'solo',
    'widget_tweaks',
    'smart_selects',
    'cloudinary_storage', 
    'cloudinary',       
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

ROOT_URLCONF = 'mi_proyecto.urls'

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
                'mi_app.context_processors.common_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'mi_proyecto.wsgi.application'

# --- Base de Datos Inteligente ---
if IS_PRODUCTION:
    DATABASES = { 'default': dj_database_url.config(conn_max_age=600, ssl_require=True) }
else:
    DATABASES = { 'default': { 'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3' } }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Lima'
USE_I18N = True
USE_TZ = True

# --- INICIO DE LA MEJORA: Configuración de Archivos 100% Cloud ---
# Configuración de Archivos Estáticos (CSS, JS)
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Configuración de Archivos Media (Imágenes subidas) - SIEMPRE a Cloudinary
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'dmyzbifxz',
    'API_KEY': '791437747798959',
    'API_SECRET': '7CGRPD9IMWehmZZS2P-bGMXcAWM',
}

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
# Las variables MEDIA_URL y MEDIA_ROOT ya no son necesarias.
# --- FIN DE LA MEJORA ---

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'index'
LOGOUT_REDIRECT_URL = 'index'


# === INICIO DE LA MEJORA: Se elimina toda la configuración de Jazzmin ===
# JAZZMIN_SETTINGS = { ... }
# JAZZMIN_UI_TWEAKS = { ... }
# === FIN DE LA MEJORA ===

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'calderonpalaciosa123@gmail.com'
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_USE_TLS = False