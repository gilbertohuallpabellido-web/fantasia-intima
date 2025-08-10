# mi_app/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Rutas para el catálogo público y el carrito
    path('', views.catalogo_publico, name='catalogo_publico'),
    path('producto/<int:pk>/', views.producto_detalle, name='producto_detalle'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('ver-carrito/', views.ver_carrito, name='ver_carrito'),
    path('eliminar-del-carrito/<str:item_id>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    path('api/cart-count/', views.cart_count_view, name='cart_count'),

    # Rutas para el proceso de pago
    path('checkout/<int:pk>/<int:variante_pk>/', views.checkout_view, name='checkout_view'),
    path('checkout-carrito/', views.checkout_carrito, name='checkout_carrito'),
    path('procesar-pago/', views.procesar_pago, name='procesar_pago'),
    path('compra-exitosa/', views.compra_exitosa, name='compra_exitosa'),
    path('error-stock/', views.error_stock_view, name='error_stock'),

    # Ruta para el asistente de IA
    path('get-ai-response/', views.get_ai_response, name='get_ai_response'),

    # Rutas para pedidos por WhatsApp
    path('crear-pedido-whatsapp/', views.crear_pedido_whatsapp, name='crear_pedido_whatsapp'),
    path('resumen-pedido/<uuid:pedido_id>/', views.resumen_pedido_whatsapp, name='resumen_pedido_whatsapp'),

    # --- CAMBIO IMPORTANTE ---
    # Esta ruta es necesaria para que el enlace de 'Mis Pedidos' funcione.
    path('detalle-pedido/<uuid:pedido_id>/', views.resumen_pedido_whatsapp, name='detalle_pedido'),

    # Rutas de autenticación y registro
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro_view, name='registro'),
    
    # --- RUTA PARA EL PANEL DEL CLIENTE ---
    path('mi-cuenta/', views.mi_cuenta, name='mi_cuenta'),
    
    # Rutas del dashboard de administrador
    path('dashboard/', views.dashboard, name='dashboard'),
    path('subir-producto/', views.subir_producto, name='subir_producto'),
    path('modificar-producto/<int:pk>/', views.subir_producto, name='modificar_producto'),
    path('eliminar-producto/<int:pk>/', views.eliminar_producto, name='eliminar_producto'),
]