# mi_app/context_processors.py
import json
from .models import Categoria, ConfiguracionSitio, Pagina, ConfiguracionRuleta, ConfiguracionChatbot, Banner
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
    """Devuelve una lista de banners activos ya resueltos a una URL destino.

    Prioridad de destino por cada banner:
      1) Primer producto en `productos_destacados` con stock (usa la vista `producto_detalle`)
      2) Si no hay producto disponible, usa `banner.enlace` si está presente
      3) Si no hay destino válido, se omite el banner
    """
    banners_out = []
    # No usamos fechas en el modelo actual; solo consideramos `activo=True`
    now = timezone.now()
    for b in Banner.objects.filter(activo=True).order_by('id'):
        # respetar rango de fechas si están definidos
        if getattr(b, 'fecha_inicio', None) and b.fecha_inicio and b.fecha_inicio > now:
            continue
        if getattr(b, 'fecha_fin', None) and b.fecha_fin and b.fecha_fin < now:
            continue
        destino = None
        # Prioridad: producto con stock
        try:
            productos = list(b.productos_destacados.all())
        except Exception:
            productos = []

        # Si hay varios productos destacados válidos, construimos una URL al catálogo
        valid_product_ids = [str(p.pk) for p in productos if getattr(p, 'total_stock', 0) > 0]
        if len(valid_product_ids) == 1:
            destino = reverse('producto_detalle', args=[int(valid_product_ids[0])])
        elif len(valid_product_ids) > 1:
            # redirige al catálogo con filtro por lista de productos
            destino = f"{reverse('catalogo_publico')}?productos={','.join(valid_product_ids)}"

        # Siguiente prioridad: enlace directo
        if not destino and getattr(b, 'enlace', None):
            destino = b.enlace

        if destino:
            banners_out.append({
                'titulo': getattr(b, 'titulo', ''),
                'subtitulo': getattr(b, 'subtitulo', ''),
                'imagen_url': b.imagen.url if getattr(b, 'imagen', None) else None,
                'destino_url': destino,
                'texto_boton': getattr(b, 'texto_boton', 'Ver ahora'),
                'fecha_fin': getattr(b, 'fecha_fin', None),
            })

    return {'banners_activos': banners_out}
