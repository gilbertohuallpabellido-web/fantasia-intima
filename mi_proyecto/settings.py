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
DEBUG = True

# --- Configuración de Hosts y Seguridad Definitiva ---
ALLOWED_HOSTS = []
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS = [f'https://{RENDER_EXTERNAL_HOSTNAME}']

if not IS_PRODUCTION:
    ALLOWED_HOSTS.append('*')


# Application definition
# Lista básica de apps (sin jazzmin). Más abajo intentamos activarlo
# condicionalmente solo si está instalado y si estamos en producción o
# si se fuerza mediante la variable de entorno USE_JAZZMIN=1.
INSTALLED_APPS = [
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

# Permitir activar Jazzmin solo en entornos que lo soporten.
# Comportamiento:
# - En producción (IS_PRODUCTION==True) intentamos usar jazzmin si está instalado.
# - En local puedes forzarlo temporalmente exportando USE_JAZZMIN=1.
USE_JAZZMIN = os.environ.get('USE_JAZZMIN', '0') == '1'
if IS_PRODUCTION or USE_JAZZMIN:
    try:
        import importlib
        if importlib.util.find_spec('jazzmin'):
            # Insertar al inicio para que tenga prioridad sobre el admin por defecto
            INSTALLED_APPS.insert(0, 'jazzmin')
        else:
            # jazzmin no está instalado en este entorno; seguimos sin él
            pass
    except Exception:
        # En caso de cualquier problema con importlib no rompemos el arranque
        pass

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

# --- Archivos estáticos ---
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# === Configuración de Almacenamiento Definitiva y Segura ===
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')
# === INICIO DE LA MEJORA: Permiso especial para el DJ ===
# Le decimos a Cloudinary que los archivos de audio y video no son imágenes.
CLOUDINARY_STORAGE = {
    'MEDIA_TAG': 'media', # Mantiene la carpeta media en Cloudinary
    'INVALID_VIDEO_ERROR_CODE': 400,
    'EXCLUDE_DIR': ('_temp',),
    'RESOURCE_TYPE': {
        'default': 'image',
        'raw': ('mp3', 'wav', 'ogg', 'pdf'),
        'video': ('mp4', 'webm', 'mov'),
    },
    'STATIC_TAG': 'static',
    'STATICFILES_MANIFEST_ROOT': os.path.join(BASE_DIR, 'staticfiles'),
}
# === FIN DE LA MEJORA ===

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'index'
LOGOUT_REDIRECT_URL = 'index'