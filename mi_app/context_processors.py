# mi_app/context_processors.py
import json
from .models import Categoria, ConfiguracionSitio, Pagina, ConfiguracionRuleta, ConfiguracionChatbot, Banner, Producto
from django.urls import reverse
from django.utils import timezone

def common_context(request):
    """
    Provee contexto común a todas las plantillas, incluyendo las configuraciones
    globales del sitio, la ruleta y el chatbot.
    """
    # Obtenemos todas las configuraciones singleton de una vez.
    try:
        configuracion_sitio = ConfiguracionSitio.get_solo()
    except ConfiguracionSitio.DoesNotExist:
        configuracion_sitio = None
        
    try:
        config_ruleta = ConfiguracionRuleta.get_solo()
    except ConfiguracionRuleta.DoesNotExist:
        config_ruleta = None
        
    try:
        chatbot_config = ConfiguracionChatbot.get_solo()
    except ConfiguracionChatbot.DoesNotExist:
        chatbot_config = None

    # Creamos el diccionario de contexto base.
    context = {
        'categorias_menu': Categoria.objects.filter(parent__isnull=True).prefetch_related('children'),
        'cart_count': sum(item.get('quantity', 0) for item in request.session.get('cart', {}).values()),
        'configuracion_sitio': configuracion_sitio,
        'paginas_informativas': Pagina.objects.filter(publicada=True),
        'configuracion_ruleta': config_ruleta,
        'chatbot_config': chatbot_config, # <-- Aquí está la nueva configuración
    }

    # === PROMOS: Selección rápida de 1 producto nueva colección y 1 oferta ===
    try:
        nuevo = (Producto.objects
                 .filter(es_nueva_coleccion=True, imagen_principal__isnull=False)
                 .order_by('?')
                 .first())
    except Exception:
        nuevo = None
    try:
        oferta = (Producto.objects
                  .filter(es_oferta=True, imagen_principal__isnull=False)
                  .order_by('?')
                  .first())
    except Exception:
        oferta = None

    promo_payload = {
        'new_collection': None,
        'offer': None,
    }
    if nuevo:
        try:
            variant_urls_nuevo = [getattr(v.imagen, 'url', None) for v in nuevo.variantes.all()][:2]
            variant_urls_nuevo = [u for u in variant_urls_nuevo if u]
        except Exception:
            variant_urls_nuevo = []
        promo_payload['new_collection'] = {
            'id': nuevo.id,
            'name': nuevo.nombre,
            'image': getattr(nuevo.imagen_principal, 'url', None),
            'variant_images': variant_urls_nuevo,
            'price': str(nuevo.precio),
        }
    if oferta:
        try:
            variant_urls_oferta = [getattr(v.imagen, 'url', None) for v in oferta.variantes.all()][:2]
            variant_urls_oferta = [u for u in variant_urls_oferta if u]
        except Exception:
            variant_urls_oferta = []
        promo_payload['offer'] = {
            'id': oferta.id,
            'name': oferta.nombre,
            'image': getattr(oferta.imagen_principal, 'url', None),
            'variant_images': variant_urls_oferta,
            'price': str(oferta.precio),
            'offer_price': str(oferta.precio_oferta) if oferta.precio_oferta else None,
            'discount_percent': oferta.descuento_porcentaje,
        }
    # Fallback: cualquier producto con imagen si ambos faltan
    if not promo_payload['new_collection'] and not promo_payload['offer']:
        try:
            cualquiera = (Producto.objects
                           .filter(imagen_principal__isnull=False)
                           .order_by('?')
                           .first())
        except Exception:
            cualquiera = None
        if cualquiera:
            try:
                variant_urls_any = [getattr(v.imagen, 'url', None) for v in cualquiera.variantes.all()][:2]
                variant_urls_any = [u for u in variant_urls_any if u]
            except Exception:
                variant_urls_any = []
            promo_payload['any_product'] = {
                'id': cualquiera.id,
                'name': cualquiera.nombre,
                'image': getattr(cualquiera.imagen_principal, 'url', None),
                'variant_images': variant_urls_any,
                'price': str(cualquiera.precio),
            }
    else:
        promo_payload['any_product'] = None
    context['promo_products_json'] = json.dumps(promo_payload)

    # Preparamos los datos JSON específicos para la ruleta si existe.
    if config_ruleta:
        premios_ruleta = list(config_ruleta.premios.filter(activo=True)[:8])
        premios_json = json.dumps([{'id': p.id, 'nombre': p.nombre} for p in premios_ruleta])
        
        config_json_data = {
            'titulo': config_ruleta.titulo,
            'activa': config_ruleta.activa,
            'sonido_giro_url': config_ruleta.sonido_giro.url if config_ruleta.sonido_giro else None,
            'sonido_premio_url': config_ruleta.sonido_premio.url if config_ruleta.sonido_premio else None,
        }
        config_json = json.dumps(config_json_data)

        context.update({
            'roulette_prizes_json': premios_json,
            'roulette_config_json': config_json,
        })
    else:
        # Si no hay ruleta, proveemos valores por defecto.
        context.update({
            'roulette_prizes_json': '[]',
            'roulette_config_json': '{}',
        })

    return context


def banners_context(request):
    """Devuelve banners activos con URL según modo_destino (simplificado)."""
    banners_out = []
    now = timezone.now()
    for b in Banner.objects.filter(activo=True).order_by('id'):
        if getattr(b, 'fecha_inicio', None) and b.fecha_inicio and b.fecha_inicio > now:
            continue
        if getattr(b, 'fecha_fin', None) and b.fecha_fin and b.fecha_fin < now:
            continue
        destino = None
        modo = getattr(b, 'modo_destino', 'nueva')
        if modo == 'nueva':
            destino = f"{reverse('catalogo_publico')}?categoria=nueva_coleccion&banner_id={b.pk}#product-list-section"
        elif modo == 'ofertas':
            destino = f"{reverse('catalogo_publico')}?solo_ofertas=1&banner_id={b.pk}#product-list-section"
        elif modo == 'producto':
            # Soporte: si hay múltiples seleccionados usamos ?productos=1,2,3
            ids_multi = []
            try:
                ids_multi = list(b.productos_destacados.values_list('pk', flat=True)) if hasattr(b, 'productos_destacados') else []
            except Exception:
                ids_multi = []
            if ids_multi:
                if len(ids_multi) == 1:
                    # Uno solo -> detalle
                    destino = reverse('producto_detalle', args=[ids_multi[0]])
                else:
                    cadena = ','.join(str(i) for i in ids_multi)
                    destino = f"{reverse('catalogo_publico')}?productos={cadena}&banner_id={b.pk}#product-list-section"
        elif modo == 'enlace' and getattr(b, 'enlace', None):
            destino = b.enlace
        # Debug simple después de resolver destino
        try:
            print(f"BANNER_CTX: banner={b.pk} modo={modo} destino={destino}")
        except Exception:
            pass
        if destino:
            banners_out.append({
                'id': b.pk,
                'titulo': getattr(b, 'titulo', ''),
                'subtitulo': getattr(b, 'subtitulo', ''),
                'imagen_url': b.imagen.url if getattr(b, 'imagen', None) else None,
                'destino_url': destino,
                'texto_boton': getattr(b, 'texto_boton', 'Ver ahora'),
                'fecha_fin': getattr(b, 'fecha_fin', None),
                'modo': modo,
            })
    return {'banners_activos': banners_out}
