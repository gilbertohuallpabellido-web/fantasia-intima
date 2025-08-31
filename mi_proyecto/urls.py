# mi_proyecto/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Esta línea pasa el control a las URLs de tu aplicación.
    path('', include('mi_app.urls')),

    path('chaining/', include('smart_selects.urls')),
]

# --- CONFIGURACIÓN ESTÁNDAR Y RECOMENDADA ---
if settings.DEBUG:
    # Para servir archivos subidos por el usuario (media)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Para servir archivos estáticos (CSS, JS) en desarrollo
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
