# mi_proyecto/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    # Aquí se incluyen todas las rutas de tu aplicación 'mi_app'
    path('', include('mi_app.urls')),

    # --- LÍNEA MODIFICADA para el login ---
    # Le decimos a la vista de login que use el template 'mi_app/login.html'
    path(
        'accounts/login/', 
        auth_views.LoginView.as_view(template_name='mi_app/login.html'), 
        name='login'
    ),
    
    # --- Vista de logout ---
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)