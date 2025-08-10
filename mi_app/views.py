# mi_app/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings # Importar settings para referenciar el modelo de usuario
from .models import Producto, ColorVariante, PedidoWhatsApp, DetallePedidoWhatsApp
from .forms import ProductoForm, LoginForm, ColorVarianteFormSet, CustomUserCreationForm
from django.db import transaction
import os
import json
import requests
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

# --- Vistas del catálogo público ---
def catalogo_publico(request):
    """
    Muestra la página principal del catálogo de productos.
    Recupera todos los productos y el conteo del carrito desde la sesión.
    """
    productos = Producto.objects.all()
    if 'cart' not in request.session:
        request.session['cart'] = {}
    cart_count = sum(item['quantity'] for item in request.session['cart'].values())
    return render(request, 'mi_app/catalogo_publico.html', {'productos': productos, 'cart_count': cart_count})

def producto_detalle(request, pk):
    """
    Muestra los detalles de un producto específico.
    """
    producto = get_object_or_404(Producto, pk=pk)
    if 'cart' not in request.session:
        request.session['cart'] = {}
    cart_count = sum(item['quantity'] for item in request.session['cart'].values())
    return render(request, 'mi_app/producto_detalle.html', {'producto': producto, 'cart_count': cart_count})

def add_to_cart(request):
    """
    Agrega un producto con una variante y cantidad al carrito de la sesión.
    Devuelve una respuesta JSON para ser utilizada en llamadas AJAX.
    """
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        variant_id = request.POST.get('variant_id')
        quantity = int(request.POST.get('quantity', 1))

        product = get_object_or_404(Producto, pk=product_id)
        variant = get_object_or_404(ColorVariante, pk=variant_id)
        
        cart = request.session.get('cart', {})
        if str(variant_id) in cart:
            cart[str(variant_id)]['quantity'] += quantity
        else:
            cart[str(variant_id)] = {
                'id': str(variant_id),
                'product_id': product.pk,
                'name': product.nombre,
                'price': str(product.precio),
                'color': variant.get_color_display(), # Guardamos el nombre en español
                'image_url': variant.imagen.url,
                'quantity': quantity,
            }
        request.session['cart'] = cart
        cart_count = sum(item['quantity'] for item in request.session['cart'].values())
        return JsonResponse({'success': True, 'cart_count': cart_count})
    return JsonResponse({'success': False}, status=400)

def cart_count_view(request):
    """
    Devuelve la cantidad de productos en el carrito de la sesión en formato JSON.
    Esta vista es utilizada por la llamada AJAX en la plantilla.
    """
    cart = request.session.get('cart', {})
    cart_count = sum(item['quantity'] for item in cart.values())
    return JsonResponse({"cart_count": cart_count})

def ver_carrito(request):
    """
    Muestra la página del carrito, con los productos y el precio total.
    """
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0
    for item_id, item_data in cart.items():
        item_data['id'] = item_id
        # --- CÓDIGO ACTUALIZADO PARA CALCULAR EL SUBTOTAL ---
        subtotal = float(item_data['price']) * item_data['quantity']
        item_data['subtotal'] = subtotal
        total_price += subtotal
        # ----------------------------------------------------
        cart_items.append(item_data)
    
    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'cart_count': sum(item['quantity'] for item in request.session['cart'].values())
    }
    return render(request, 'mi_app/ver_carrito.html', context)

def eliminar_del_carrito(request, item_id):
    """
    Elimina un ítem específico del carrito de la sesión.
    """
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        if str(item_id) in cart:
            del cart[str(item_id)]
            request.session['cart'] = cart
    return redirect('ver_carrito')


# --- Vistas para el proceso de pago ---
def checkout_view(request, pk, variante_pk):
    """
    Inicia el proceso de pago para un solo producto.
    """
    producto = get_object_or_404(Producto, pk=pk)
    try:
        variante = ColorVariante.objects.get(pk=variante_pk, producto=producto)
        if variante.stock <= 0:
            return redirect('error_stock')
    except ColorVariante.DoesNotExist:
        return redirect('error_stock')

    contexto = {
        'producto': producto,
        'variante': variante,
        'ciudades': ['Lima', 'Provincia']
    }
    return render(request, 'mi_app/checkout.html', contexto)

def checkout_carrito(request):
    """
    Inicia el proceso de pago para todos los productos en el carrito.
    """
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0
    
    for item_id, item_data in cart.items():
        total_price += float(item_data['price']) * item_data['quantity']
        cart_items.append(item_data)

    if not cart_items:
        return redirect('catalogo_publico')

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'ciudades': ['Lima', 'Provincia']
    }
    return render(request, 'mi_app/checkout_carrito.html', context)

@transaction.atomic
def procesar_pago(request):
    """
    Procesa el pago, valida el stock y vacía el carrito.
    Utiliza una transacción atómica para asegurar la integridad de los datos.
    """
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        
        for item_id, item_data in cart.items():
            variante = get_object_or_404(ColorVariante, pk=item_id)
            if variante.stock >= item_data['quantity']:
                variante.stock -= item_data['quantity']
                variante.save()
            else:
                return redirect('error_stock')
        
        request.session['cart'] = {}
        return redirect('compra_exitosa')
    return redirect('catalogo_publico')

def compra_exitosa(request):
    """
    Muestra una página de confirmación de compra exitosa.
    """
    return render(request, 'mi_app/compra_confirmacion.html')

def error_stock_view(request):
    """
    Muestra una página de error cuando no hay suficiente stock.
    """
    return render(request, 'mi_app/error_stock.html')


# --- VISTAS PARA PEDIDOS POR WHATSAPP (ACTUALIZADO) ---

@require_POST
def crear_pedido_whatsapp(request):
    """
    ### CAMBIO IMPORTANTE
    Esta vista ahora asocia el pedido al usuario si está autenticado.
    Esto permite que los pedidos aparezcan en la sección "Mis Pedidos" del cliente.
    """
    cart = request.session.get('cart', {})
    if not cart:
        return JsonResponse({'error': 'El carrito está vacío'}, status=400)

    # Generar código de pedido único
    now = timezone.now()
    codigo_pedido = f"FI-{now.strftime('%d%m%y-%H%M%S')}"
    
    total_pedido = 0
    
    # Asignar el usuario si está autenticado
    user_to_assign = request.user if request.user.is_authenticated else None

    # Crear el objeto Pedido con el usuario
    pedido = PedidoWhatsApp.objects.create(
        codigo_pedido=codigo_pedido, 
        total=0,
        user=user_to_assign # <--- CAMBIO AQUÍ: Asociamos el usuario al pedido
    )

    for variant_id, item_data in cart.items():
        total_item = item_data['quantity'] * float(item_data['price'])
        total_pedido += total_item
        
        DetallePedidoWhatsApp.objects.create(
            pedido=pedido,
            producto_nombre=item_data['name'],
            variante_color=item_data['color'],
            cantidad=item_data['quantity'],
            precio_unitario=item_data['price'],
            imagen_url=item_data['image_url']
        )

    pedido.total = total_pedido
    pedido.save()

    # Generar la URL para el resumen del pedido
    order_url = request.build_absolute_uri(f'/resumen-pedido/{pedido.id}/')
    
    return JsonResponse({
        'success': True,
        'order_url': order_url.replace('http://', 'https://'),
        'order_code': codigo_pedido
    })

def resumen_pedido_whatsapp(request, pedido_id):
    pedido = get_object_or_404(PedidoWhatsApp, id=pedido_id)
    return render(request, 'mi_app/resumen_pedido.html', {'pedido': pedido})


# --- Vista del asistente virtual con IA (Gemini API) ---
def get_ai_response(request):
    """
    Se comunica con la API de Gemini para generar una respuesta basada
    en el mensaje del usuario y el contexto de la página.
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        user_message = data.get('message')
        page_context = data.get('context')
        
        prompt = f"""Eres un asistente virtual para una tienda de lencería en línea. Tu objetivo es responder preguntas sobre los productos, métodos de pago y envío, basándote únicamente en la siguiente información. Si la pregunta no se puede responder con la información proporcionada, debes indicar que no tienes esa información y sugerirle que contacte a la tienda por WhatsApp.

        ---
        INFORMACIÓN DE LA TIENDA:
        - Productos disponibles: {json.dumps(page_context['products'], indent=2)}
        - Métodos de pago aceptados: {', '.join(page_context['paymentMethods'])}.
        - Tiempos de envío: Lima ({page_context['deliveryInfo']['lima']}), Provincia ({page_context['deliveryInfo']['provincia']}).
        - Información de contacto: WhatsApp ({page_context['contactInfo']['whatsapp']}).

        PREGUNTA DEL USUARIO:
        {user_message}
        ---

        Respuesta:"""

        try:
            # Reemplaza con tu lógica de manejo de API key.
            api_key = os.environ.get("GEMINI_API_KEY", "")
            if not api_key:
                return JsonResponse({"error": "API Key no configurada."}, status=500)
            
            headers = {"Content-Type": "application/json"}
            payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key}"

            response = requests.post(api_url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            
            result = response.json()
            ai_text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', "Lo siento, no pude obtener una respuesta.")
            
            return JsonResponse({"response": ai_text})

        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": f"Error de conexión con la API: {str(e)}"}, status=500)
        except Exception as e:
            return JsonResponse({"error": f"Error inesperado: {str(e)}"}, status=500)

    return JsonResponse({"error": "Método no permitido."}, status=405)


# --- Vistas para el manejo de usuarios (login, logout, etc.) ---
def login_view(request):
    """
    Muestra la página de inicio de sesión y maneja el proceso de autenticación.
    """
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'¡Hola {user.first_name}! Has iniciado sesión correctamente.')
                return redirect('dashboard')
            else:
                messages.error(request, 'Usuario o contraseña incorrectos.')
    else:
        form = LoginForm()
    return render(request, 'mi_app/login.html', {'form': form})

def logout_view(request):
    """
    Esta vista maneja el proceso de cierre de sesión.
    
    1. Cierra la sesión del usuario.
    2. Redirige a la página principal del catálogo.
    """
    if request.user.is_authenticated:
        messages.info(request, f'¡Adiós {request.user.first_name}! Has cerrado tu sesión.')
    logout(request)
    return redirect('catalogo_publico')

def registro_view(request):
    """
    Vista para manejar el registro de nuevos usuarios.
    """
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # --- ESTA ES LA LÓGICA CORRECTA ---
            # 1. Inicia sesión automáticamente con el nuevo usuario
            login(request, user)
            # 2. Muestra un mensaje de bienvenida
            messages.success(request, f'¡Bienvenida, {user.first_name}! Tu cuenta ha sido creada con éxito.')
            # 3. Redirige directamente al dashboard del cliente
            return redirect('mi_cuenta') # <--- Redirigimos a la cuenta del cliente
        else:
            messages.error(request, 'Error al crear la cuenta. Por favor, revisa los campos.')
    else:
        form = CustomUserCreationForm()
    
    context = {
        'form': form
    }
    return render(request, 'mi_app/registro.html', context)


@login_required
def dashboard(request):
    """
    Muestra el panel de control del administrador.
    Solo es accesible para usuarios que han iniciado sesión.
    """
    productos = Producto.objects.all()
    return render(request, 'mi_app/dashboard.html', {'productos': productos})

@login_required
def subir_producto(request, pk=None):
    """
    Permite subir un nuevo producto o modificar uno existente.
    """
    if pk:
        producto = get_object_or_404(Producto, pk=pk)
        titulo = "Modificar Producto"
    else:
        producto = None
        titulo = "Añadir Nuevo Producto"
    
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        formset = ColorVarianteFormSet(request.POST, request.FILES, instance=producto)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                producto = form.save()
                formset.instance = producto
                formset.save()
            return redirect('dashboard')
    else:
        form = ProductoForm(instance=producto)
        formset = ColorVarianteFormSet(instance=producto)

    contexto = {
        'titulo': titulo,
        'producto': producto,
        'form': form,
        'formset': formset,
    }
    return render(request, 'mi_app/subir_producto.html', contexto)

@login_required
def eliminar_producto(request, pk):
    """
    Maneja la eliminación de un producto.
    """
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.delete()
        messages.success(request, f'El producto "{producto.nombre}" ha sido eliminado correctamente.')
        return redirect('dashboard')
    return render(request, 'mi_app/eliminar_confirmacion.html', {'producto': producto})


@login_required
def mi_cuenta(request):
    """
    ### CAMBIO IMPORTANTE
    Esta vista ahora obtiene y pasa al contexto los pedidos del usuario
    logueado. Así, se pueden mostrar en la plantilla.
    """
    # Si un admin intenta acceder, lo redirigimos a su dashboard
    if request.user.is_staff:
        return redirect('dashboard')
    
    # Obtener todos los pedidos del usuario actual, ordenados por fecha descendente
    pedidos_del_usuario = PedidoWhatsApp.objects.filter(user=request.user).order_by('-fecha_creacion')
    
    # El diccionario de contexto se pasa a la plantilla
    context = {
        'pedidos': pedidos_del_usuario,
    }
    return render(request, 'mi_app/mi_cuenta.html', context)