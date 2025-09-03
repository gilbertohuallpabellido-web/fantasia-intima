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
                    'error': 'Has alcanzado el límite de intentos (3).' 
                }, status=403)
        except TiradaRuleta.DoesNotExist:
            last_spin = None

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
        if last_spin:
            last_spin.attempts = min(last_spin.attempts + 1, 3)
            last_spin.ultima_tirada = now
            last_spin.save(update_fields=['attempts','ultima_tirada'])
        else:
            last_spin = TiradaRuleta.objects.create(usuario=user, ultima_tirada=now, attempts=1)

    response_data = {
        'success': True,
        'prize_id': premio_ganado.id,  # ID para recalcular índice en frontend si cambia el orden
        'prize': {
            'id': premio_ganado.id,
            'name': premio_ganado.nombre,
            'coupon_code': cupon.codigo,
        },
        # Índice según el orden usado aquí (order_by('id')[:8])
    'winning_index': winning_index,
    'remaining': (0 if user.is_superuser else max(0, 3 - (last_spin.attempts)))
    }
    
    return JsonResponse(response_data)