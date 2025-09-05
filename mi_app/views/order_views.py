# mi_app/views/order_views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from datetime import timedelta
from django.contrib import messages
from urllib.parse import quote

# Se añaden todos los modelos necesarios
from ..models import Producto, ColorVariante, PedidoWhatsApp, DetallePedidoWhatsApp, ConfiguracionSitio, Direccion, ReservaStock, Carrito, CarritoItem

def _clean_expired_cart_items(request):
    cart = request.session.get('cart', {})
    if not cart:
        return [], cart

    now = timezone.now()
    expiration_time = timedelta(hours=24)
    expired_items_names = []
    
    for item_id in list(cart.keys()):
        item_data = cart[item_id]
        added_at_str = item_data.get('added_at')
        
        if added_at_str:
            added_at = timezone.datetime.fromisoformat(added_at_str)
            if now - added_at > expiration_time:
                expired_items_names.append(item_data['name'])
                # liberar reserva si existiera
                try:
                    variante = ColorVariante.objects.get(pk=item_id)
                    ReservaStock.objects.filter(variante=variante, session_key=request.session.session_key).delete()
                except ColorVariante.DoesNotExist:
                    pass
                del cart[item_id]

    if expired_items_names:
        request.session['cart'] = cart
        request.session.modified = True

    return expired_items_names, cart


def _get_or_create_carrito(user):
    carrito, _ = Carrito.objects.get_or_create(user=user)
    return carrito


def add_to_cart(request):
    if request.method == 'POST':
        if request.content_type == 'application/json':
            payload = json.loads(request.body.decode('utf-8') or '{}')
            product_id = payload.get('product_id')
            variant_id = payload.get('variant_id')
            quantity = int(payload.get('quantity', 1))
        else:
            product_id = request.POST.get('product_id')
            variant_id = request.POST.get('variant_id')
            quantity = int(request.POST.get('quantity', 1))

        if not product_id or not variant_id:
            return JsonResponse({'success': False, 'error': 'Faltan datos del producto. Inténtalo de nuevo.'}, status=400)

        product = get_object_or_404(Producto, pk=product_id)
        variant = get_object_or_404(ColorVariante, pk=variant_id, producto=product)

        if quantity <= 0:
            return JsonResponse({'success': False, 'error': 'Cantidad inválida'}, status=400)

        # asegurar session_key
        if not request.session.session_key:
            request.session.create()
        cart = request.session.get('cart', {})

        effective_price = product.precio_oferta if product.precio_oferta is not None else product.precio
        original_price = product.precio if product.precio_oferta is not None else None

        current_qty = cart.get(str(variant_id), {}).get('quantity', 0)
        new_qty = current_qty + quantity
        
        # calcular stock disponible considerando reservas de otras sesiones
        active_reservations = ReservaStock.objects.filter(
            variante=variant,
            expires_at__gt=timezone.now()
        ).exclude(session_key=request.session.session_key)
        reserved_qty_others = sum(r.quantity for r in active_reservations)
        available_effective = max(variant.stock - reserved_qty_others, 0)
        if new_qty > available_effective:
            if current_qty > 0:
                error_message = (
                    f"No puedes añadir más. Ya tienes {current_qty} en tu carrito y solo quedan {available_effective} disponibles."
                )
            else:
                error_message = (
                    f"La cantidad solicitada ({quantity}) supera el stock disponible ({available_effective})."
                )
            return JsonResponse({
                'success': False,
                'error': error_message,
                'available': available_effective
            }, status=400)

        image_url = variant.imagen.url if variant.imagen else ''

        cart_item_data = {
            'id': str(variant_id),
            'product_id': product.pk,
            'name': product.nombre,
            'price': str(effective_price),
            'original_price': str(original_price) if original_price else None,
            'color': variant.codigo or variant.color,
            'image_url': image_url,
            'quantity': new_qty,
            'added_at': timezone.now().isoformat()
        }
        cart[str(variant_id)] = cart_item_data

        # Persistir carrito si está autenticado
        if request.user.is_authenticated:
            carrito = _get_or_create_carrito(request.user)
            item, created = CarritoItem.objects.get_or_create(
                carrito=carrito,
                variante=variant,
                defaults={
                    'quantity': 0,
                    'price': effective_price,
                    'original_price': original_price,
                    'image_url': image_url,
                }
            )
            item.quantity = new_qty
            item.price = effective_price
            item.original_price = original_price
            item.image_url = image_url
            item.save()

    # crear/actualizar reserva por 24h
        expires_at = timezone.now() + timedelta(hours=24)
        reserva, _ = ReservaStock.objects.get_or_create(
            variante=variant,
            session_key=request.session.session_key,
            defaults={'quantity': 0, 'expires_at': expires_at}
        )
        reserva.quantity = new_qty
        reserva.expires_at = expires_at
        if request.user.is_authenticated:
            reserva.user = request.user
        reserva.save()

        request.session['cart'] = cart
        # calcular cart_count: si autenticado, usar carrito persistente
        if request.user.is_authenticated:
            carrito = Carrito.objects.filter(user=request.user).first()
            cart_count = carrito.total_items if carrito else 0
        else:
            cart_count = sum(item['quantity'] for item in cart.values())
        # devolver stock efectivo restante
        active_reservations_all = ReservaStock.objects.filter(variante=variant, expires_at__gt=timezone.now())
        reserved_total = sum(r.quantity for r in active_reservations_all)
        current_available = max(variant.stock - reserved_total, 0)
        return JsonResponse({'success': True, 'cart_count': cart_count, 'current_available': current_available})
    return JsonResponse({'success': False, 'error': 'Solicitud no válida.'}, status=400)

def cart_count_view(request):
    if request.user.is_authenticated:
        carrito = Carrito.objects.filter(user=request.user).first()
        count = carrito.total_items if carrito else 0
        return JsonResponse({"cart_count": count})
    else:
        cart = request.session.get('cart', {})
        cart_count = sum(item['quantity'] for item in cart.values())
        return JsonResponse({"cart_count": cart_count})

def ver_carrito(request):
    # Si está autenticado, sincronizar desde Carrito persistente a la sesión para reusar la plantilla
    if request.user.is_authenticated:
        carrito = Carrito.objects.filter(user=request.user).first()
        cart = {}
        if carrito:
            for ci in carrito.items.select_related('variante', 'variante__producto').all():
                product = ci.variante.producto
                cart[str(ci.variante.pk)] = {
                    'id': str(ci.variante.pk),
                    'product_id': product.pk,
                    'name': product.nombre,
                    'price': str(ci.price),
                    'original_price': str(ci.original_price) if ci.original_price else None,
                    'color': ci.variante.codigo or ci.variante.color,
                    'image_url': ci.image_url,
                    'quantity': ci.quantity,
                    'added_at': timezone.now().isoformat()
                }
        request.session['cart'] = cart
        expired_items = []
    else:
        expired_items, cart = _clean_expired_cart_items(request)
    if expired_items:
        messages.warning(request, f"Algunos productos han sido eliminados de tu carrito porque su reserva de 24 horas ha caducado: {', '.join(expired_items)}.")

    cart_items = []
    total_price = Decimal('0')
    for item_id, item_data in cart.items():
        item_data['id'] = item_id
        price = Decimal(str(item_data['price']))
        subtotal = price * item_data['quantity']
        item_data['subtotal'] = float(subtotal)
        total_price += subtotal
        cart_items.append(item_data)
    
    context = {
        'cart_items': cart_items,
        'total_price': float(total_price),
        'cart_count': sum(item['quantity'] for item in cart.values())
    }
    return render(request, 'mi_app/ver_carrito.html', context)

@login_required(login_url='/login/')
def checkout_carrito(request):
    expired_items, cart = _clean_expired_cart_items(request)
    if expired_items:
        messages.warning(request, f"Algunos productos han sido eliminados de tu carrito por caducidad antes de proceder al pago: {', '.join(expired_items)}.")
        return redirect('ver_carrito')

    if not cart:
        return redirect('ver_carrito')

    cart_items = []
    total_price = Decimal('0')
    
    for item_id, item_data in cart.items():
        total_price += Decimal(str(item_data['price'])) * item_data['quantity']
        cart_items.append(item_data)

    direcciones_usuario = []
    initial_data = {}

    if request.user.is_authenticated:
        direcciones_usuario = Direccion.objects.filter(user=request.user).order_by('-predeterminada')
        
        direccion_predeterminada = direcciones_usuario.first()
        if direccion_predeterminada:
            initial_data = {
                'nombre': direccion_predeterminada.destinatario,
                'direccion': direccion_predeterminada.direccion,
                'ciudad': direccion_predeterminada.ciudad,
                'telefono': direccion_predeterminada.telefono,
                'referencia': direccion_predeterminada.referencia,
            }
        else:
            initial_data['nombre'] = request.user.get_full_name()

    site_config = ConfiguracionSitio.get_solo()

    context = {
        'cart_items': cart_items,
        'total_price': float(total_price),
        'site_config': site_config,
        'direcciones_usuario': direcciones_usuario,
        'initial_data': initial_data,
    }
    return render(request, 'mi_app/checkout_carrito.html', context)

@transaction.atomic
def procesar_pago(request):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        if not cart:
            return redirect('ver_carrito')
        # Pre-chequeo de stock
        for item_id, item_data in cart.items():
            variante = get_object_or_404(ColorVariante, pk=item_id)
            if variante.stock < item_data['quantity']:
                messages.error(request, f"Lo sentimos, el stock del producto '{variante.producto.nombre}' ha cambiado. Por favor, revisa tu carrito.")
                return redirect('ver_carrito')
        
        now = timezone.now()
        codigo_pedido = f"FI-{now.strftime('%d%m%y-%H%M%S')}"
        total_pedido = sum(Decimal(str(item['price'])) * item['quantity'] for item in cart.values())
        
        pedido = PedidoWhatsApp.objects.create(
            codigo_pedido=codigo_pedido,
            total=total_pedido,
            user=request.user if request.user.is_authenticated else None,
            nombre_cliente=request.POST.get('nombre'),
            dni_cliente=request.POST.get('dni'),
            email_cliente=request.POST.get('email'),
            celular_cliente=request.POST.get('celular'),
            ciudad_envio=request.POST.get('ciudad'),
            direccion_envio=request.POST.get('direccion'),
        )
        # Descontar stock, limpiar reservas y crear detalle por cada item
        for item_id, item_data in cart.items():
            variante = get_object_or_404(ColorVariante, pk=item_id)
            # doble verificación contra reservas de otros antes de descontar
            active_reservations = ReservaStock.objects.filter(
                variante=variante,
                expires_at__gt=timezone.now()
            ).exclude(session_key=request.session.session_key)
            reserved_qty_others = sum(r.quantity for r in active_reservations)
            available_effective = max(variante.stock - reserved_qty_others, 0)
            if item_data['quantity'] > available_effective:
                messages.error(request, f"El stock de '{variante.producto.nombre}' cambió durante el pago. Solo quedan {available_effective}.")
                return redirect('ver_carrito')

            variante.stock -= item_data['quantity']
            variante.save()

            # eliminar reservas del usuario (todas las sesiones) y de la sesión actual
            if request.user.is_authenticated:
                ReservaStock.objects.filter(variante=variante, user=request.user).delete()
            if request.session.session_key:
                ReservaStock.objects.filter(variante=variante, session_key=request.session.session_key).delete()

            DetallePedidoWhatsApp.objects.create(
                pedido=pedido,
                producto_nombre=item_data['name'],
                variante_color=item_data['color'],
                cantidad=item_data['quantity'],
                precio_unitario=Decimal(str(item_data['price'])),
                imagen_url=item_data['image_url']
            )

        # Limpiar carrito persistente si está autenticado
        if request.user.is_authenticated:
            CarritoItem.objects.filter(carrito__user=request.user).delete()
        request.session['cart'] = {}
        return redirect('compra_exitosa', pedido_id=pedido.id)

    return redirect('catalogo_publico')


def compra_exitosa(request, pedido_id):
    pedido = get_object_or_404(PedidoWhatsApp, id=pedido_id)
    # --- CORRECCIÓN: Se define la variable 'site_config' antes de usarla ---
    site_config = ConfiguracionSitio.get_solo()

    resumen_url = request.build_absolute_uri(reverse('resumen_pedido_whatsapp', args=[pedido.id]))
    
    mensaje_whatsapp = (
        f"¡Hola Fantasía Íntima! ✨\n\n"
        f"Acabo de realizar el pago para mi pedido *#{pedido.codigo_pedido}* 🛍️.\n\n"
        f"Te adjunto la captura del pago 📸.\n\n"
        f"Puedes ver el resumen de mi pedido aquí: 👇\n{resumen_url}"
    )
    whatsapp_link_con_mensaje = f"{site_config.whatsapp_link}?text={quote(mensaje_whatsapp)}"

    context = {
        'pedido': pedido,
        'site_config': site_config,
        'whatsapp_link_con_mensaje': whatsapp_link_con_mensaje,
    }
    return render(request, 'mi_app/compra_confirmacion.html', context)

def error_stock_view(request):
    return render(request, 'mi_app/error_stock.html')

@require_POST
def crear_pedido_whatsapp(request):
    cart = request.session.get('cart', {})
    if not cart:
        return JsonResponse({'error': 'El carrito está vacío'}, status=400)

    now = timezone.now()
    codigo_pedido = f"FI-{now.strftime('%d%m%y-%H%M%S')}"
    
    total_pedido = Decimal('0')
    user_to_assign = request.user if request.user.is_authenticated else None

    pedido = PedidoWhatsApp.objects.create(
        codigo_pedido=codigo_pedido, 
        total=Decimal('0'),
        user=user_to_assign
    )

    for variant_id, item_data in cart.items():
        price = Decimal(str(item_data['price']))
        total_item = price * item_data['quantity']
        total_pedido += total_item
        
        DetallePedidoWhatsApp.objects.create(
            pedido=pedido,
            producto_nombre=item_data['name'],
            variante_color=item_data['color'],
            cantidad=item_data['quantity'],
            precio_unitario=price,
            imagen_url=item_data['image_url']
        )

    pedido.total = total_pedido
    pedido.save()

    relative_url = reverse('resumen_pedido_whatsapp', args=[pedido.id])
    order_url = f"{request.scheme}://{request.get_host()}{relative_url}"
    
    return JsonResponse({
        'success': True,
        'order_url': order_url,
        'order_code': codigo_pedido
    })

def resumen_pedido_whatsapp(request, pedido_id):
    pedido = get_object_or_404(PedidoWhatsApp, id=pedido_id)
    return render(request, 'mi_app/resumen_pedido.html', {'pedido': pedido})

@require_POST
def actualizar_cantidad_carrito(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            variant_id = str(data.get('variant_id'))
            new_quantity = int(data.get('quantity'))
            
            cart = request.session.get('cart', {})
            variant = get_object_or_404(ColorVariante, pk=variant_id)

            # asegurar session_key
            if not request.session.session_key:
                request.session.create()

            # considerar reservas de otros
            active_reservations = ReservaStock.objects.filter(
                variante=variant,
                expires_at__gt=timezone.now()
            ).exclude(session_key=request.session.session_key)
            reserved_qty_others = sum(r.quantity for r in active_reservations)
            available_effective = max(variant.stock - reserved_qty_others, 0)

            if new_quantity > available_effective:
                return JsonResponse({
                    'success': False, 
                    'error': f'Solo quedan {available_effective} unidades disponibles.',
                    'current_stock': available_effective
                }, status=400)

            if variant_id in cart:
                cart[variant_id]['quantity'] = new_quantity
                request.session['cart'] = cart

                # Si autenticado, reflejar en CarritoItem
                if request.user.is_authenticated:
                    carrito = _get_or_create_carrito(request.user)
                    item, _ = CarritoItem.objects.get_or_create(
                        carrito=carrito,
                        variante=variant,
                        defaults={
                            'price': Decimal(str(cart[variant_id]['price'])),
                            'original_price': Decimal(str(cart[variant_id]['original_price'])) if cart[variant_id]['original_price'] else None,
                            'image_url': cart[variant_id]['image_url'],
                        }
                    )
                    item.quantity = new_quantity
                    item.save()

                # actualizar/crear reserva y extender vencimiento
                expires_at = timezone.now() + timedelta(hours=24)
                reserva, _ = ReservaStock.objects.get_or_create(
                    variante=variant,
                    session_key=request.session.session_key,
                    defaults={'quantity': 0, 'expires_at': expires_at}
                )
                reserva.quantity = new_quantity
                reserva.expires_at = expires_at
                if request.user.is_authenticated:
                    reserva.user = request.user
                reserva.save()
                
                item = cart[variant_id]
                item_subtotal = float(item['price']) * item['quantity']
                cart_total = sum(float(i['price']) * i['quantity'] for i in cart.values())
                cart_item_count = sum(i['quantity'] for i in cart.values())

                # calcular disponibilidad actual (stock - todas las reservas)
                active_reservations_all = ReservaStock.objects.filter(variante=variant, expires_at__gt=timezone.now())
                reserved_total = sum(r.quantity for r in active_reservations_all)
                current_available = max(variant.stock - reserved_total, 0)

                return JsonResponse({
                    'success': True,
                    'item_quantity': new_quantity,
                    'item_subtotal': item_subtotal,
                    'cart_total': cart_total,
                    'cart_item_count': cart_item_count,
                    'current_available': current_available
                })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

def eliminar_del_carrito(request, item_id):
    cart = request.session.get('cart', {})
    item_id_str = str(item_id)

    if item_id_str in cart:
        del cart[item_id_str]
        request.session['cart'] = cart

        # eliminar reserva asociada de esta sesión
        try:
            variante = ColorVariante.objects.get(pk=item_id_str)
            # Si autenticado, borrar item del Carrito persistente
            if request.user.is_authenticated:
                try:
                    carrito = Carrito.objects.get(user=request.user)
                    CarritoItem.objects.filter(carrito=carrito, variante=variante).delete()
                except Carrito.DoesNotExist:
                    pass
            if request.session.session_key:
                ReservaStock.objects.filter(variante=variante, session_key=request.session.session_key).delete()
        except ColorVariante.DoesNotExist:
            pass

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        cart_total = sum(float(i['price']) * i['quantity'] for i in cart.values())
        cart_item_count = sum(i['quantity'] for i in cart.values())
        return JsonResponse({
            'success': True,
            'cart_total': cart_total,
            'cart_item_count': cart_item_count
        })
    
    return redirect('ver_carrito')

def checkout_view(request, pk, variante_pk):
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