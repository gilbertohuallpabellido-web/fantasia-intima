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

# Clave secreta leída desde las variables de entorno de Render.
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-tu-clave-secreta-para-desarrollo')

# DEBUG se desactiva automáticamente en producción por seguridad.
DEBUG = 'RENDER' not in os.environ

# --- Configuración de Hosts para Producción y Desarrollo ---
ALLOWED_HOSTS = []
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS = [f'https://{RENDER_EXTERNAL_HOSTNAME}']

if DEBUG:
    ALLOWED_HOSTS.append('*')


# Application definition
INSTALLED_APPS = [
    # === INICIO DE LA MEJORA: Jazzmin solo se activa en producción ===
    # 'jazzmin', # Se moverá abajo para ser condicional
    # === FIN DE LA MEJORA ===
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Tus aplicaciones
    'mi_app',
    
    # Aplicaciones de terceros
    'mptt',
    'solo',
    'widget_tweaks',
    'smart_selects',
    
    'cloudinary_storage', 
    'cloudinary',       
]

# === INICIO DE LA MEJORA: Jazzmin solo se activa en producción ===
if 'RENDER' in os.environ:
    # Insertamos jazzmin al principio de la lista, como recomienda la documentación.
    INSTALLED_APPS.insert(0, 'jazzmin')
# === FIN DE LA MEJORA ===

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
if 'RENDER' in os.environ:
    DATABASES = {
        'default': dj_database_url.config(
            conn_max_age=600,
            ssl_require=True
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Lima'
USE_I18N = True
USE_TZ = True

# --- Configuración de Archivos Estáticos y Medios Adaptativa ---
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

if 'RENDER' in os.environ:
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')
else:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'index'
LOGOUT_REDIRECT_URL = 'index'


# === INICIO DE LA MEJORA: Configuración de Jazzmin solo para producción ===
if 'RENDER' in os.environ:
    JAZZMIN_SETTINGS = {
        "site_title": "Fantasía Íntima Admin",
        "site_header": "Fantasía Íntima",
        "site_brand": "Panel de Control",
        "site_logo": "productos/logo.png",
        "login_logo": "productos/logo.png",
        "welcome_sign": "Bienvenida al Panel de Fantasía Íntima",
        "copyright": "Fantasía Íntima",
        "search_model": ["mi_app.Producto", "mi_app.Categoria"],
        "topmenu_links": [
            {"name": "Inicio",  "url": "admin:index"},
            {"name": "Ver Tienda", "url": "/", "new_window": True},
            {"model": "auth.User"},
        ],
        "order_with_respect_to": [
            "mi_app.Producto", "mi_app.Categoria", "mi_app.ColorVariante",
            "mi_app.PedidoWhatsApp",
            "mi_app.Banner", "mi_app.Pagina",
            "mi_app.ConfiguracionSitio", "mi_app.ConfiguracionRuleta", "mi_app.ConfiguracionChatbot",
            "auth.User", "auth.Group",
        ],
        "icons": {
            "auth": "fas fa-users-cog",
            "auth.user": "fas fa-user",
            "auth.Group": "fas fa-users",
            "mi_app.Producto": "fas fa-tshirt",
            "mi_app.Categoria": "fas fa-tags",
            "mi_app.ColorVariante": "fas fa-palette",
            "mi_app.PedidoWhatsApp": "fab fa-whatsapp-square",
            "mi_app.Banner": "fas fa-images",
            "mi_app.Pagina": "fas fa-file-alt",
            "mi_app.ConfiguracionSitio": "fas fa-cogs",
            "mi_app.ConfiguracionRuleta": "fas fa-dharmachakra",
            "mi_app.ConfiguracionChatbot": "fas fa-robot",
        },
        "default_icon_parents": "fas fa-chevron-circle-right",
        "default_icon_children": "fas fa-circle",
        "show_ui_builder": True,
    }

    JAZZMIN_UI_TWEAKS = {
        "navbar_small_text": False,
        "footer_small_text": False,
        "body_small_text": False,
        "brand_small_text": False,
        "brand_colour": "navbar-pink",
        "accent": "accent-pink",
        "navbar": "navbar-pink navbar-dark",
        "no_navbar_border": False,
        "navbar_fixed": True,
        "layout_boxed": False,
        "footer_fixed": False,
        "sidebar_fixed": True,
        "sidebar": "sidebar-dark-pink",
        "sidebar_nav_small_text": False,
        "sidebar_disable_expand": False,
        "sidebar_nav_child_indent": True,
        "sidebar_nav_compact_style": False,
        "sidebar_nav_legacy_style": False,
        "sidebar_nav_flat_style": True,
        "theme": "litera",
        "dark_mode_theme": None,
        "button_classes": {
            "primary": "btn-outline-primary",
            "secondary": "btn-outline-secondary",
            "info": "btn-info",
            "warning": "btn-warning",
            "danger": "btn-danger",
            "success": "btn-success"
        },
        "actions_sticky_top": True,
    }
# === FIN DE LA MEJORA ===

# --- CONFIGURACIÓN PARA EL ENVÍO DE CORREOS ELECTRÓNICOS (Tu configuración, intacta) ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'calderonpalaciosa123@gmail.com'
# --- MEJORA DE SEGURIDAD: Leer contraseña desde el entorno ---
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_USE_TLS = False