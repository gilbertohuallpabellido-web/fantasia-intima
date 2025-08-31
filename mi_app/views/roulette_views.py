# mi_app/views/roulette_views.py
import random
from datetime import timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from ..models import ConfiguracionRuleta, Cupon, TiradaRuleta

@require_POST
@login_required
def spin_roulette(request):
    user = request.user
    now = timezone.now()

    if not user.is_superuser:
        try:
            last_spin = TiradaRuleta.objects.get(usuario=user)
            if not last_spin.puede_jugar():
                return JsonResponse({
                    'success': False,
                    'error': '¡Ya has probado tu suerte hoy! Vuelve a intentarlo mañana.'
                }, status=403)
        except TiradaRuleta.DoesNotExist:
            pass

    try:
        config_ruleta = ConfiguracionRuleta.get_solo()
        # Se obtienen hasta 8 premios para que coincida con el diseño visual
        premios_activos = list(config_ruleta.premios.filter(activo=True).order_by('id')[:8])
        if not config_ruleta.activa or not premios_activos:
            return JsonResponse({'success': False, 'error': 'La ruleta no está disponible en este momento.'}, status=500)
    except ConfiguracionRuleta.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'La ruleta no está configurada.'}, status=500)

    # --- INICIO DE LA MEJORA: Se elige el premio y se determina su posición ---
    premio_ganado = random.choice(premios_activos)
    winning_index = premios_activos.index(premio_ganado)
    # --- FIN DE LA MEJORA ---

    cupon = Cupon.objects.create(
        usuario=user,
        premio=premio_ganado
    )

    if not user.is_superuser:
        TiradaRuleta.objects.update_or_create(
            usuario=user,
            defaults={'ultima_tirada': now}
        )

    response_data = {
        'success': True,
        'prize': {
            'name': premio_ganado.nombre,
            'coupon_code': cupon.codigo,
        },
        # Se envía el índice del premio ganador al frontend
        'winning_index': winning_index
    }
    
    return JsonResponse(response_data)