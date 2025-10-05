# mi_app/urls.py

from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from .views.dashboard_views import get_subcategories_json, catalogo_publico
from .views.order_views import (
    add_to_cart, cart_count_view, ver_carrito, eliminar_del_carrito,
    checkout_view, checkout_carrito, procesar_pago,
    crear_pedido_whatsapp, resumen_pedido_whatsapp,
    actualizar_cantidad_carrito, error_stock_view, compra_exitosa
)
from .views.catalog_views import pagina_informativa_view, search_suggest
from .views.healthy_views import health_check

urlpatterns = [
    # Rutas para el catálogo público y el carrito
    path('', catalogo_publico, name='index'),
    path('catalogo/', catalogo_publico, name='catalogo_publico'),
    
    path('producto/<int:pk>/', views.producto_detalle, name='producto_detalle'),
    
    # Rutas para el carrito
    path('add_to_cart/', views.add_to_cart, name='add_to_cart'),
    path('cart/count/', views.cart_count_view, name='cart_count'),
    path('ver-carrito/', views.ver_carrito, name='ver_carrito'),
    path('cart/item/<str:item_id>/remove/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    path('cart/item/update/', views.actualizar_cantidad_carrito, name='actualizar_cantidad_carrito'),

    # Rutas para el proceso de pago
    path('checkout/', views.checkout_carrito, name='checkout_carrito'),
    path('checkout/pagar/', procesar_pago, name='procesar_pago'),
    
    path('compra-exitosa/<uuid:pedido_id>/', compra_exitosa, name='compra_exitosa'),
    
    path('error-stock/', error_stock_view, name='error_stock'),

    # Ruta para el asistente de IA
    path('get-ai-response/', views.get_ai_response, name='get_ai_response'),
    path('ai/status/', views.ai_status, name='ai_status'),

    # --- INICIO DE LA MEJORA: URL para la Ruleta de la Suerte ---
    path('roulette/spin/', views.spin_roulette, name='spin_roulette'),
    # --- FIN DE LA MEJORA ---

    # Rutas para pedidos por WhatsApp
    path('pedido/whatsapp/crear/', crear_pedido_whatsapp, name='crear_pedido_whatsapp'),
    path('pedido/<uuid:pedido_id>/', resumen_pedido_whatsapp, name='resumen_pedido_whatsapp'),

    # Rutas de autenticación y registro
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    path('registro/', views.registro_view, name='registro'),
    path('activar/<str:uidb64>/<str:token>/', views.activate, name='activate'),
    
    # === INICIO DE LA MEJORA: Rutas para el panel del cliente ===
    path('mi-cuenta/', views.mi_cuenta, name='mi_cuenta'),
    path('mi-cuenta/eliminar/', views.eliminar_cuenta_view, name='eliminar_cuenta'),
    # === FIN DE LA MEJORA ===
    
    # Ruta para páginas informativas
    path('paginas/<slug:slug>/', pagina_informativa_view, name='pagina_informativa'),

    # API: sugerencias de búsqueda
    path('api/search/suggest/', search_suggest, name='search_suggest'),

    # --- API para subcategorías dinámicas en el admin ---
    path('api/admin/get-subcategories/', get_subcategories_json, name='admin_get_subcategories'),

    # Otras rutas
    path('chaining/', include('smart_selects.urls')),

    # Healthcheck simple para monitoreo / uptime
    path('health/', health_check, name='health_check'),
]
