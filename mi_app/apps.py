from django.apps import AppConfig


class MiAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mi_app'

    def ready(self):
        # Registrar señal: al iniciar sesión, fusionar carrito de sesión -> carrito persistente
        from django.contrib.auth.signals import user_logged_in
        from django.dispatch import receiver
        from django.utils import timezone
        from datetime import timedelta
        from decimal import Decimal
        from .models import Carrito, CarritoItem, ColorVariante, ReservaStock

        @receiver(user_logged_in)
        def merge_session_cart(sender, user, request, **kwargs):
            try:
                session_cart = request.session.get('cart', {}) or {}
                if not session_cart:
                    return
                carrito, _ = Carrito.objects.get_or_create(user=user)
                for variant_id, item in session_cart.items():
                    try:
                        variante = ColorVariante.objects.get(pk=variant_id)
                    except ColorVariante.DoesNotExist:
                        continue
                    price_val = Decimal(str(item.get('price'))) if item.get('price') is not None else Decimal('0')
                    original_val = Decimal(str(item.get('original_price'))) if item.get('original_price') else None
                    image_val = item.get('image_url') or ''
                    ci, _ = CarritoItem.objects.get_or_create(
                        carrito=carrito,
                        variante=variante,
                        defaults={'quantity': 0, 'price': price_val, 'original_price': original_val, 'image_url': image_val}
                    )
                    ci.quantity = (ci.quantity or 0) + int(item.get('quantity', 0))
                    ci.price = price_val
                    ci.original_price = original_val
                    ci.image_url = image_val
                    ci.save()

                    # Migrar/crear reserva a usuario y extender 24h
                    expires_at = timezone.now() + timedelta(hours=24)
                    reserva, _ = ReservaStock.objects.get_or_create(
                        variante=variante,
                        user=user,
                        defaults={'quantity': 0, 'expires_at': expires_at, 'session_key': request.session.session_key}
                    )
                    reserva.quantity = ci.quantity
                    reserva.expires_at = expires_at
                    reserva.session_key = request.session.session_key
                    reserva.save()
                # Espejar carrito persistente a la sesión
                mirror = {}
                for ci in carrito.items.select_related('variante', 'variante__producto').all():
                    p = ci.variante.producto
                    mirror[str(ci.variante.pk)] = {
                        'id': str(ci.variante.pk),
                        'product_id': p.pk,
                        'name': p.nombre,
                        'price': str(ci.price),
                        'original_price': str(ci.original_price) if ci.original_price else None,
                        'color': ci.variante.codigo or ci.variante.color,
                        'image_url': ci.image_url,
                        'quantity': ci.quantity,
                        'added_at': timezone.now().isoformat(),
                    }
                request.session['cart'] = mirror
                request.session.modified = True
            except Exception:
                # No bloquear login en caso de error de fusión
                pass
