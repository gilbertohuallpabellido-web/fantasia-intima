import json
import os
import time
import random
import logging
import requests
import re
from difflib import SequenceMatcher
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.cache import cache
from ..models import Producto, ConfiguracionSitio, ApiKey, ConfiguracionChatbot

logger = logging.getLogger(__name__)

# ================= Config =================
CONTEXT_CACHE_KEY = "ai_store_context_v11"
CONTEXT_TTL_SECONDS = 300
MAX_HISTORY_CHARS = 3000
RATE_LIMIT_WINDOW = 300
RATE_LIMIT_MAX = 50
GENERATION_CONFIG = {
    "temperature": 0.75,
    "topP": 0.95,
    "topK": 40,
    "maxOutputTokens": 1024,
}
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash-latest")
SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# ================= Helpers =================
def _client_ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")

def _rate_limit_exceeded(request):
    ip = _client_ip(request)
    key = f"ai_rl_{ip}"
    current = cache.get(key, 0)
    if current >= RATE_LIMIT_MAX:
        return True
    if current == 0:
        cache.set(key, 1, RATE_LIMIT_WINDOW)
    else:
        cache.incr(key)
    return False

def _get_api_keys():
    cached_keys = cache.get('gemini_api_keys_db')
    if cached_keys is not None:
        random.shuffle(cached_keys)
        return cached_keys
    keys_qs = ApiKey.objects.filter(activa=True).values_list('key', flat=True)
    api_keys = list(keys_qs)
    cache.set('gemini_api_keys_db', api_keys, 60)
    if not api_keys:
        logger.error("No se encontraron claves de API de Gemini activas en la base de datos.")
    random.shuffle(api_keys)
    return api_keys

def _trim_history(chat_history, max_chars=MAX_HISTORY_CHARS):
    try:
        s = json.dumps(chat_history, ensure_ascii=False)
        if len(s) <= max_chars:
            return chat_history
        trimmed, total = [], 0
        for item in reversed(chat_history):
            item_s = json.dumps(item, ensure_ascii=False)
            if total + len(item_s) > max_chars:
                break
            trimmed.insert(0, item)
            total += len(item_s)
        return trimmed
    except Exception:
        return chat_history[-6:]

def _build_prompt_context(user_query=None):
    cache_key = f"{CONTEXT_CACHE_KEY}_{user_query[:20]}" if user_query else CONTEXT_CACHE_KEY
    cached = cache.get(cache_key)
    if cached:
        return cached

    config = ConfiguracionSitio.get_solo()
    base_productos_qs = Producto.objects.select_related("categoria").prefetch_related("variantes")
    productos = None

    if user_query:
        from django.db.models import Q
        productos = base_productos_qs.filter(Q(nombre__icontains=user_query) | Q(categoria__nombre__icontains=user_query))[:6]

    if not user_query or not productos or not productos.exists():
        try:
            productos = base_productos_qs.order_by('-ventas')[:10]
        except Exception:
            productos = base_productos_qs.order_by('?')[:10]

    catalogo = {}
    for p in productos:
        cat_nombre = p.categoria.nombre if p.categoria else "General"
        catalogo.setdefault(cat_nombre, []).append({
            "sku": p.variantes.first().codigo if p.variantes.exists() else f"ID-{p.pk}",
            "nombre": p.nombre,
            "precio": float(p.precio_oferta or p.precio),
        })

    context = {
        "info_tienda": {
            "nombre": config.nombre_tienda,
            "contacto_whatsapp": config.whatsapp_link,
            "redes_sociales": { "facebook": config.facebook_link, "instagram": config.instagram_link, "tiktok": config.tiktok_link },
            "metodos_pago": { "tipos": ["Yape", "Plin"], "numero_yape_plin": config.numero_yape_plin }
        },
        "catalogo_relevante": catalogo,
    }
    cache.set(cache_key, context, CONTEXT_TTL_SECONDS)
    return context

def get_system_instructions(user_name=None):
    config = ConfiguracionChatbot.get_solo()
    return config.instrucciones_sistema.format(user_name=user_name or "Desconocido")

AFFIRMATIVES = {"si", "sí", "dale", "ok", "ya", "dame", "claro", "a ver", "porfis"}
BUY_INTENTS = {
    "me animo", "lo compro", "quiero llevar", "quiero comprar",
    "me lo quedo", "lo llevo", "comprar", "sí quiero llevarme",
    "si quiero llevarme", "sí quiero llevar", "si quiero llevar",
    "si quiero", "sí quiero"
}

def _postprocess_response(user_message, ai_text, history, context):
    msg = user_message.lower().strip()
    last_response = next((h.get("text", "") for h in reversed(history) if h.get("role") == "model"), "")
    tienda = context.get("info_tienda", {})

    if any(phrase in msg for phrase in BUY_INTENTS):
        numero_yape_plin = tienda.get("metodos_pago", {}).get("numero_yape_plin", "nuestro número oficial")
        whatsapp_link = tienda.get("contacto_whatsapp", "")
        
        upsell_message = ""
        catalogo = context.get("catalogo_relevante", {})
        accesorio_encontrado = next((p for cat_products in catalogo.values() for p in cat_products if "media" in p.get("nombre", "").lower()), None)
        
        if accesorio_encontrado:
            upsell_message = (
                f"\n\n✨ Además, para completar tu look, te puedo recomendar nuestras '{accesorio_encontrado['nombre']}' "
                f"(S/{accesorio_encontrado['precio']:.2f}). Combinan perfecto. ¿Te las agrego?"
            )

        sociales = tienda.get("redes_sociales", {})
        social_links_parts = [f"[{net.capitalize()}]({link})" for net, link in sociales.items() if link]
        fidelizacion_message = ""
        if social_links_parts:
            social_links = ", ".join(social_links_parts)
            fidelizacion_message = f"\n\nNo olvides seguirnos en {social_links} para enterarte de todas nuestras novedades y ofertas. ¡Te esperamos!"

        return (
            f"¡Me encanta tu decisión! 🎉 Te separo de inmediato el producto que elegiste.\n\n"
            f"👉 Puedes pagar por **Yape o Plin al número {numero_yape_plin}**. "
            f"Cuando hagas el pago, envíame el comprobante a nuestro **WhatsApp ({whatsapp_link})** para coordinar el envío 📦."
            f"{upsell_message}"
            f"{fidelizacion_message}"
        )

    if msg in AFFIRMATIVES and SequenceMatcher(None, ai_text.lower(), last_response.lower()).ratio() > 0.8:
        logger.warning(f"BUCLE DETECTADO! Respuesta repetida tras un 'sí'. Original: '{ai_text}'")
        if "¿te animas a llevarlo?" in last_response.lower():
             return _postprocess_response("si me animo", "", history, context)
        else:
            return "¡Mil disculpas si me repetí! Te doy más detalles: este conjunto está hecho de un encaje floral súper delicado que se siente increíble en la piel. ¿Qué te parece? ¿Te animas a llevarlo?"
            
    valid_skus = set()
    if 'catalogo_relevante' in context:
        for products in context['catalogo_relevante'].values():
            for product in products:
                valid_skus.add(product.get('sku', '').lower())
    mentioned_skus = set(re.findall(r'SKU:?\s*([A-Z0-9-]+)', ai_text, re.IGNORECASE))
    invented_sku_found = any(sku.lower() not in valid_skus for sku in mentioned_skus if sku)

    if invented_sku_found:
        logger.warning(f"ALUCINACIÓN DETECTADA! El bot inventó un SKU. Respuesta original: '{ai_text}'")
        first_valid_product = next((p for cat in context.get('catalogo_relevante', {}).values() for p in cat), None)
        if first_valid_product:
            return f"¡Uy, creo que mi imaginación voló! Para darte información 100% correcta, te recomiendo nuestro '{first_valid_product['nombre']}' (SKU: {first_valid_product['sku']}). Cuesta S/ {first_valid_product['precio']:.2f}. ¿Te gustaría saber más?"
        else:
            return "Lo siento, me confundí y no encuentro una recomendación precisa ahora. ¿Qué categoría te interesa más?"
            
    return ai_text

def _call_gemini_with_rotation(api_keys, payload):
    base = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"
    headers = {"Content-Type": "application/json"}
    for key in api_keys:
        key_hash = key[-4:]
        if cache.get(f"failed_api_key_{key_hash}"):
            continue
        url = f"{base}?key={key}"
        try:
            r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=25)
            if r.status_code == 200:
                j = r.json()
                text = j.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
                if text:
                    return text
                logger.warning("Respuesta OK pero sin texto con clave ...%s. Respuesta: %s", key_hash, j)
            else:
                logger.warning("Status %s con clave ...%s. Respuesta: %s", r.status_code, key_hash, r.text)
                cache.set(f"failed_api_key_{key_hash}", True, 60)
        except requests.exceptions.RequestException as e:
            logger.warning("Error de red con clave ...%s: %s", key_hash, e)
            cache.set(f"failed_api_key_{key_hash}", True, 60)
        time.sleep(1)
    return None

# ================= View =================
@require_POST
def get_ai_response(request):
    try:
        chatbot_config = ConfiguracionChatbot.get_solo()
        if not chatbot_config.activo:
            return JsonResponse({"response": "Lo siento, mi asistente virtual Fanty no está disponible en este momento."}, status=503)

        if _rate_limit_exceeded(request):
            return JsonResponse({"response": "Muchos mensajes. Inténtalo en unos minutos."}, status=429)

        data = json.loads(request.body or "{}")
        user_message = (data.get("message") or "").strip()
        chat_history = data.get("history", [])
        if not user_message:
            return JsonResponse({"response": "Escribe un mensaje."}, status=400)

        api_keys = _get_api_keys()
        if not api_keys:
            return JsonResponse({"response": "El asistente de IA no está configurado."}, status=503)

        user_name = None
        if request.user.is_authenticated:
            user_name = request.user.first_name or request.user.username

        context = _build_prompt_context(user_message)
        trimmed_history = _trim_history(chat_history)
        
        system_instructions = get_system_instructions(user_name=user_name)
        
        contents = []
        contents.append({"role": "user", "parts": [{"text": f"CONTEXTO DE LA TIENDA:\n{json.dumps(context, ensure_ascii=False)}"}]})
        contents.append({"role": "model", "parts": [{"text": "¡Entendido! Estoy lista para ayudar como Fanty."}]})

        for entry in trimmed_history:
            role = "user" if entry.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": entry.get("text", "")}]})
        
        contents.append({"role": "user", "parts": [{"text": user_message}]})
        
        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system_instructions}]},
            "generationConfig": GENERATION_CONFIG,
            "safetySettings": SAFETY_SETTINGS,
        }

        ai_text = _call_gemini_with_rotation(api_keys, payload)
        if ai_text:
            original_ai_text = ai_text
            processed_ai_text = _postprocess_response(user_message, original_ai_text, trimmed_history, context)
            if original_ai_text != processed_ai_text:
                logger.info(f"Post-procesador corrigió la respuesta. Original: '{original_ai_text}', Corregida: '{processed_ai_text}'")
            return JsonResponse({"response": processed_ai_text})

        logger.error("Todas las claves fallaron o sin respuesta válida.")
        config = ConfiguracionSitio.get_solo()
        fallback_message = f"Estoy con problemitas técnicos 😅. Escríbeme directo a WhatsApp 👉 {config.whatsapp_link} para ayudarte rápido."
        return JsonResponse({"response": fallback_message}, status=503)

    except (ConfiguracionSitio.DoesNotExist, ConfiguracionChatbot.DoesNotExist):
        logger.exception("Configuración de sitio o chatbot no establecida.")
        return JsonResponse({"response": "Configura la tienda y el chatbot antes de usar el asistente."}, status=500)
    except Exception as e:
        logger.exception("Error inesperado en get_ai_response: %s", e)
        try:
            config = ConfiguracionSitio.get_solo()
            fallback_message = f"Ocurrió un error inesperado, ¡pero no te preocupes! Escríbeme directo a WhatsApp 👉 {config.whatsapp_link} para atenderte personalmente."
            return JsonResponse({"response": fallback_message}, status=500)
        except ConfiguracionSitio.DoesNotExist:
            return JsonResponse({"response": "Ocurrió un error inesperado y no se pudo cargar la configuración de contacto."}, status=500)