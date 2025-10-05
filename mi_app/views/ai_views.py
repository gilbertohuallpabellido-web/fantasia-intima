import json
import os
import time
import random
import logging
import requests
import re
from difflib import SequenceMatcher
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.core.cache import cache
from ..models import Producto, ConfiguracionSitio, ApiKey, ConfiguracionChatbot

logger = logging.getLogger(__name__)

# ================= Config =================
CONTEXT_CACHE_KEY = "ai_store_context_v11"
CONTEXT_TTL_SECONDS = 300
MAX_HISTORY_CHARS = 3000
RATE_LIMIT_WINDOW = 300
RATE_LIMIT_MAX = 50
DEFAULT_GENERATION_CONFIG = {
    "temperature": 0.75,
    "topP": 0.95,
    "topK": 40,
    "maxOutputTokens": 1024,
}
GEMINI_FALLBACK_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash-latest")
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

def _get_api_keys(provider: str):
    cache_key = f'api_keys_{provider}'
    cached_keys = cache.get(cache_key)
    if cached_keys is not None:
        random.shuffle(cached_keys)
        return cached_keys
    keys_qs = ApiKey.objects.filter(activa=True, provider=provider).values_list('key', flat=True)
    api_keys = list(keys_qs)
    cache.set(cache_key, api_keys, 60)
    if not api_keys:
        logger.error(f"No se encontraron claves activas para proveedor {provider}.")
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

    metodos_pago = { "tipos": ["Yape", "Plin"], "numero_yape_plin": config.numero_yape_plin }
    # Añadimos nuevos campos si existen
    try:
        if getattr(config, 'numero_yape', ''):
            metodos_pago['numero_yape'] = config.numero_yape
        if getattr(config, 'numero_plin', ''):
            metodos_pago['numero_plin'] = config.numero_plin
    except Exception:
        pass
    context = {
        "info_tienda": {
            "nombre": config.nombre_tienda,
            "contacto_whatsapp": config.whatsapp_link,
            "redes_sociales": { "facebook": config.facebook_link, "instagram": config.instagram_link, "tiktok": config.tiktok_link },
            "metodos_pago": metodos_pago
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
        metodos_pago = tienda.get("metodos_pago", {})
        numero_yape = metodos_pago.get("numero_yape")
        numero_plin = metodos_pago.get("numero_plin")
        numero_legacy = metodos_pago.get("numero_yape_plin", "nuestro número oficial")
        if numero_yape and numero_plin:
            numero_display = f"Yape: {numero_yape} | Plin: {numero_plin}"
        elif numero_yape:
            numero_display = f"Yape: {numero_yape}"
        elif numero_plin:
            numero_display = f"Plin: {numero_plin}"
        else:
            numero_display = numero_legacy
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
            f"👉 Puedes pagar por **{numero_display}**. "
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

def _call_gemini_with_rotation(api_keys, payload, model_name):
    """Llama a Gemini intentando modelo principal y variantes si devuelve 404.

    Modelos alternativos comunes (dependen de disponibilidad regional / versión API):
    - gemini-1.5-flash
    - gemini-1.5-flash-001
    - gemini-pro
    - gemini-1.0-pro
    """
    candidate_models = [model_name]
    # Normalizar: si termina en '-latest', agregar la versión sin sufijo y otras variantes
    if model_name.endswith('-latest'):
        base_name = model_name.rsplit('-latest', 1)[0]
        candidate_models.append(base_name)
        if '1.5-flash' in base_name:
            candidate_models.append('gemini-1.5-flash')
            candidate_models.append('gemini-1.5-flash-001')
        candidate_models.extend(['gemini-pro', 'gemini-1.0-pro'])
    else:
        # Asegurar algunas alternativas genéricas si el nombre no tiene -latest
        candidate_models.extend(['gemini-1.5-flash', 'gemini-pro'])

    tried_models = set()
    headers = {"Content-Type": "application/json"}
    for current_model in candidate_models:
        if current_model in tried_models:
            continue
        tried_models.add(current_model)
        # Intentamos primero el endpoint v1beta y, si obtenemos 404 por modelo no encontrado,
        # reintentamos inmediatamente con el mismo modelo usando el endpoint v1 antes de saltar a otro modelo.
        base_endpoints = [
            ("v1beta", f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent"),
            ("v1", f"https://generativelanguage.googleapis.com/v1/models/{current_model}:generateContent"),
        ]
        for key in api_keys:
            key_hash = key[-4:]
            if cache.get(f"failed_api_key_{key_hash}"):
                continue
            attempted_variant_404 = False
            for endpoint_label, base in base_endpoints:
                url = f"{base}?key={key}"
                try:
                    # Usar siempre 'systemInstruction'. Si la API devuelve 400 por campo desconocido, reintentamos sin él.
                    send_payload = payload
                    r = requests.post(url, headers=headers, data=json.dumps(send_payload), timeout=25)
                    if r.status_code == 200:
                        j = r.json()
                        text = j.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
                        if text:
                            if current_model != model_name:
                                logger.info("Se utilizó modelo alternativo Gemini '%s' (endpoint %s) tras fallar '%s'", current_model, endpoint_label, model_name)
                            else:
                                logger.info("Modelo Gemini '%s' respondió ok via endpoint %s", current_model, endpoint_label)
                            return text
                        logger.warning("Respuesta OK pero sin texto (modelo %s endpoint %s) clave ...%s. Respuesta: %s", current_model, endpoint_label, key_hash, j)
                        break  # No sentido probar el otro endpoint si 200 sin texto
                    elif r.status_code == 404:
                        logger.warning("Modelo Gemini '%s' no disponible (404) en endpoint %s con clave ...%s.", current_model, endpoint_label, key_hash)
                        # Marcamos que este endpoint devolvió 404; si era v1beta seguimos a v1, si era v1 salimos a siguiente modelo
                        attempted_variant_404 = True
                        # Si era el segundo endpoint (v1), abandonamos esta clave e intentamos siguiente modelo
                        if endpoint_label == "v1":
                            break
                        # Si era v1beta, continuará el loop para intentar v1
                        continue
                    elif r.status_code == 400:
                        txt = r.text or ""
                        low = txt.lower()
                        if 'unknown name' in low and 'systeminstruction' in low:
                            logger.warning("Endpoint %s rechaza systemInstruction; aplicando fallback embebiendo instrucciones en contents (modelo %s clave ...%s)", endpoint_label, current_model, key_hash)
                            if 'systemInstruction' in send_payload:
                                try:
                                    sp2 = dict(send_payload)
                                    sys_part = sp2.pop('systemInstruction', None)
                                    # Embebemos el texto de instrucciones al inicio del primer mensaje 'user'
                                    if sys_part and isinstance(sys_part, dict):
                                        sys_text = ''
                                        parts = sys_part.get('parts', [])
                                        if parts and isinstance(parts, list):
                                            sys_text = '\n'.join(p.get('text','') for p in parts if isinstance(p, dict))
                                        contents = sp2.get('contents', [])
                                        if contents and isinstance(contents, list):
                                            # Insertar un nuevo mensaje inicial con las instrucciones para no contaminar el contexto original
                                            instr_block = {"role": "user", "parts": [{"text": f"[INSTRUCCIONES DEL SISTEMA]\n{sys_text.strip()}"}]}
                                            contents.insert(0, instr_block)
                                    r2 = requests.post(url, headers=headers, data=json.dumps(sp2), timeout=25)
                                    if r2.status_code == 200:
                                        j2 = r2.json()
                                        text2 = j2.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
                                        if text2:
                                            logger.info("Modelo %s respondió tras fallback sin systemInstruction en endpoint %s", current_model, endpoint_label)
                                            return text2
                                        logger.warning("Respuesta OK sin texto tras fallback sin systemInstruction (modelo %s endpoint %s) ...%s => %s", current_model, endpoint_label, key_hash, j2)
                                        break
                                    elif r2.status_code == 404:
                                        logger.warning("Tras fallback sin systemInstruction, modelo %s da 404 endpoint %s (clave ...%s)", current_model, endpoint_label, key_hash)
                                        attempted_variant_404 = True
                                        if endpoint_label == 'v1':
                                            break
                                        continue
                                    else:
                                        logger.warning("Retry sin systemInstruction status %s (modelo %s endpoint %s) ...%s => %s", r2.status_code, current_model, endpoint_label, key_hash, r2.text)
                                        if r2.status_code not in (400, 404):
                                            cache.set(f"failed_api_key_{key_hash}", True, 60)
                                        break
                                except Exception as ie:
                                    logger.exception("Error aplicando fallback sin systemInstruction: %s", ie)
                                    break
                        else:
                            logger.warning("Status 400 distinto (modelo %s endpoint %s) ...%s => %s", current_model, endpoint_label, key_hash, txt)
                            cache.set(f"failed_api_key_{key_hash}", True, 60)
                            break
                    else:
                        logger.warning("Status %s (modelo %s endpoint %s) con clave ...%s. Respuesta: %s", r.status_code, current_model, endpoint_label, key_hash, r.text)
                        cache.set(f"failed_api_key_{key_hash}", True, 60)
                        break  # No insistir con segundo endpoint si error distinto a 404
                except requests.exceptions.RequestException as e:
                    logger.warning("Error de red Gemini (modelo %s endpoint %s) con clave ...%s: %s", current_model, endpoint_label, key_hash, e)
                    cache.set(f"failed_api_key_{key_hash}", True, 60)
                    break
                finally:
                    time.sleep(1)
            # Si ambos endpoints devolvieron 404 para este modelo y clave, pasamos al siguiente modelo sin penalizar
            if attempted_variant_404:
                # Probar siguiente modelo (romper loop de claves para este modelo)
                break
    return None


# ================= Status Endpoint =================
@require_GET
def ai_status(request):
    """Devuelve información de estado del subsistema de IA para monitoreo rápido.

    Incluye:
    - proveedor activo según toggles
    - modelo Gemini configurado y último válido persistido
    - modelo OpenAI configurado
    - cantidad de claves activas por proveedor
    """
    try:
        cfg = ConfiguracionChatbot.get_solo()
        # Replicar lógica de selección de proveedor
        if getattr(cfg, 'use_chatgpt', False) and not getattr(cfg, 'use_gemini', False):
            provider = 'chatgpt'
        elif getattr(cfg, 'use_gemini', True) and not getattr(cfg, 'use_chatgpt', False):
            provider = 'gemini'
        elif getattr(cfg, 'use_chatgpt', False) and getattr(cfg, 'use_gemini', False):
            provider = cfg.chat_provider or 'gemini'
        else:
            provider = cfg.chat_provider or 'gemini'

        data = {
            "activo": cfg.activo,
            "provider_seleccionado": provider,
            "gemini": {
                "modelo_configurado": cfg.gemini_model_name,
                "last_valid_model": getattr(cfg, 'last_valid_gemini_model', ''),
                "env_override": os.environ.get("GEMINI_MODEL") or None,
                "claves_activas": ApiKey.objects.filter(provider='gemini', activa=True).count(),
            },
            "chatgpt": {
                "modelo_configurado": cfg.openai_model_name,
                "env_override": os.environ.get("OPENAI_MODEL") or None,
                "claves_activas": ApiKey.objects.filter(provider='chatgpt', activa=True).count(),
            },
        }
        return JsonResponse(data)
    except ConfiguracionChatbot.DoesNotExist:
        return JsonResponse({"error": "Configuración de chatbot inexistente"}, status=500)
    except Exception as e:
        logger.exception("Error en ai_status: %s", e)
        return JsonResponse({"error": "Error interno"}, status=500)

def _call_openai_with_rotation(api_keys, messages, model_name, temperature: float):
    """Llama a la API de OpenAI (Chat Completions) con rotación de claves simples.

    Se evita instalar el paquete oficial para mantener dependencias ligeras; se usa requests.
    """
    url = "https://api.openai.com/v1/chat/completions"
    for key in api_keys:
        key_hash = key[-4:]
        if cache.get(f"failed_api_key_{key_hash}"):
            continue
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model_name,
            "messages": messages,
            "temperature": max(0.0, min(1.0, temperature)),
            "max_tokens": 800,
        }
        try:
            r = requests.post(url, headers=headers, data=json.dumps(body), timeout=25)
            if r.status_code == 200:
                j = r.json()
                choices = j.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content")
                    if content:
                        return content
                logger.warning("Respuesta OpenAI OK sin contenido con clave ...%s: %s", key_hash, j)
            elif r.status_code == 429:
                logger.warning("Cuota excedida (429) con clave ...%s. Activando fallback si procede.", key_hash)
                cache.set(f"failed_api_key_{key_hash}", True, 300)  # penalizar más tiempo
            else:
                logger.warning("Status OpenAI %s con clave ...%s. Respuesta: %s", r.status_code, key_hash, r.text)
                cache.set(f"failed_api_key_{key_hash}", True, 120)
        except requests.exceptions.RequestException as e:
            logger.warning("Error de red OpenAI con clave ...%s: %s", key_hash, e)
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

        # Determinar proveedor según toggles nuevos (exclusivos) con fallback legacy
        if getattr(chatbot_config, 'use_chatgpt', False) and not getattr(chatbot_config, 'use_gemini', False):
            provider = 'chatgpt'
        elif getattr(chatbot_config, 'use_gemini', True) and not getattr(chatbot_config, 'use_chatgpt', False):
            provider = 'gemini'
        elif getattr(chatbot_config, 'use_chatgpt', False) and getattr(chatbot_config, 'use_gemini', False):
            # Si por alguna razón ambos están activos (no debería tras save), usamos el campo legacy
            provider = chatbot_config.chat_provider or 'gemini'
        else:
            provider = chatbot_config.chat_provider or 'gemini'
        api_keys = _get_api_keys(provider)
        if not api_keys:
            return JsonResponse({"response": f"El asistente de IA no está configurado para {provider}."}, status=503)

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
        
        # Selección de proveedor
        temperature = chatbot_config.temperature or DEFAULT_GENERATION_CONFIG["temperature"]
        ai_text = None
        if provider == 'gemini':
            # Priorizar último modelo válido persistido
            model_name = (
                os.environ.get("GEMINI_MODEL")
                or (chatbot_config.last_valid_gemini_model.strip() if getattr(chatbot_config, 'last_valid_gemini_model', '') else None)
                or chatbot_config.gemini_model_name
                or GEMINI_FALLBACK_MODEL
            )
            payload = {
                "contents": contents,
                "systemInstruction": {"parts": [{"text": system_instructions}]},
                "generationConfig": {
                    **DEFAULT_GENERATION_CONFIG,
                    "temperature": temperature,
                },
                "safetySettings": SAFETY_SETTINGS,
            }
            ai_text = _call_gemini_with_rotation(api_keys, payload, model_name)
            # Si funcionó y el modelo usado difiere del persistido, actualizar singleton
            if ai_text and model_name != getattr(chatbot_config, 'last_valid_gemini_model', ''):
                try:
                    chatbot_config.last_valid_gemini_model = model_name
                    chatbot_config.save(update_fields=["last_valid_gemini_model"])
                except Exception:
                    logger.exception("No se pudo actualizar last_valid_gemini_model a '%s'", model_name)
        elif provider == 'chatgpt':
            model_name = os.environ.get("OPENAI_MODEL") or chatbot_config.openai_model_name or "gpt-4o-mini"
            # Convertir a formato messages
            messages = []
            messages.append({"role": "system", "content": system_instructions})
            for c in contents:
                role = c.get("role")
                parts = c.get("parts", [])
                text = parts[0].get("text") if parts else ""
                if role in ("user", "model"):
                    mapped_role = "assistant" if role == "model" else "user"
                    messages.append({"role": mapped_role, "content": text})
            ai_text = _call_openai_with_rotation(api_keys, messages, model_name, temperature)
            if not ai_text:
                # Fallback automático: si hay claves Gemini, intentamos aunque use_gemini esté False (modo resiliencia)
                try:
                    gemini_keys = _get_api_keys('gemini')
                    if gemini_keys:
                        logger.info("Fallback resiliente a Gemini (ChatGPT falló y hay claves Gemini disponibles aunque use_gemini=%s)", getattr(chatbot_config,'use_gemini',None))
                        model_name_gemini = os.environ.get("GEMINI_MODEL") or chatbot_config.gemini_model_name or GEMINI_FALLBACK_MODEL
                        payload = {
                            "contents": contents,
                            "systemInstruction": {"parts": [{"text": system_instructions}]},
                            "generationConfig": {
                                **DEFAULT_GENERATION_CONFIG,
                                "temperature": temperature,
                            },
                            "safetySettings": SAFETY_SETTINGS,
                        }
                        ai_text = _call_gemini_with_rotation(gemini_keys, payload, model_name_gemini)
                        if ai_text and model_name_gemini != getattr(chatbot_config, 'last_valid_gemini_model', ''):
                            try:
                                chatbot_config.last_valid_gemini_model = model_name_gemini
                                chatbot_config.save(update_fields=["last_valid_gemini_model"])
                            except Exception:
                                logger.exception("No se pudo actualizar last_valid_gemini_model en fallback a '%s'", model_name_gemini)
                except Exception:
                    logger.exception("Error realizando fallback resiliente a Gemini")
        else:
            return JsonResponse({"response": f"Proveedor '{provider}' no soportado."}, status=500)
        if ai_text:
            original_ai_text = ai_text
            processed_ai_text = _postprocess_response(user_message, original_ai_text, trimmed_history, context)
            if original_ai_text != processed_ai_text:
                logger.info(f"Post-procesador corrigió la respuesta. Original: '{original_ai_text}', Corregida: '{processed_ai_text}'")
            return JsonResponse({"response": processed_ai_text})

        logger.error("Todas las claves fallaron o sin respuesta válida.")
        config = ConfiguracionSitio.get_solo()
        try:
            prefill = config.whatsapp_prefill_chatbot_resolved
        except Exception:
            prefill = ''
        wa_link = config.whatsapp_link
        if prefill:
            from urllib.parse import quote
            wa_link = f"{wa_link}?text={quote(prefill)}"
        # Hacemos el enlace clicable. Si el frontend escapa HTML, podría mostrarse literal; de ser así
        # se podrá ajustar a markdown posteriormente. Por ahora asumimos render seguro.
        fallback_message = (
            "Estoy con problemitas técnicos 😅. Escríbeme directo a WhatsApp:<br>"
            f"<a href=\"{wa_link}\" target=\"_blank\" rel=\"noopener\" class=\"fi-wa-fallback-link\">"
            "<span class=\"fi-wa-badge\"><i class=\"fab fa-whatsapp\" aria-hidden=\"true\"></i> Enviar a WhatsApp</span>"
            "</a>"
        )
        return JsonResponse({"response": fallback_message}, status=503)

    except (ConfiguracionSitio.DoesNotExist, ConfiguracionChatbot.DoesNotExist):
        logger.exception("Configuración de sitio o chatbot no establecida.")
        return JsonResponse({"response": "Configura la tienda y el chatbot antes de usar el asistente."}, status=500)
    except Exception as e:
        logger.exception("Error inesperado en get_ai_response: %s", e)
        try:
            config = ConfiguracionSitio.get_solo()
            try:
                prefill = config.whatsapp_prefill_chatbot_resolved
            except Exception:
                prefill = ''
            wa_link = config.whatsapp_link
            if prefill:
                from urllib.parse import quote
                wa_link = f"{wa_link}?text={quote(prefill)}"
            fallback_message = (
                "Ocurrió un error inesperado, ¡pero no te preocupes! Escríbeme directo a WhatsApp:<br>"
                f"<a href=\"{wa_link}\" target=\"_blank\" rel=\"noopener\" class=\"fi-wa-fallback-link\">"
                "<span class=\"fi-wa-badge\"><i class=\"fab fa-whatsapp\" aria-hidden=\"true\"></i> Enviar a WhatsApp</span>"
                "</a>"
            )
            return JsonResponse({"response": fallback_message}, status=500)
        except ConfiguracionSitio.DoesNotExist:
            return JsonResponse({"response": "Ocurrió un error inesperado y no se pudo cargar la configuración de contacto."}, status=500)