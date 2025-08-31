# mi_app/context_processors.py
import json
from .models import Categoria, ConfiguracionSitio, Pagina, ConfiguracionRuleta, ConfiguracionChatbot

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
