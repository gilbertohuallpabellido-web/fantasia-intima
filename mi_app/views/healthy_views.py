from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from datetime import timedelta
try:
    from zoneinfo import ZoneInfo
    LIMA_TZ = ZoneInfo("America/Lima")
except Exception:
    LIMA_TZ = None

def health_check(request):
    """
    Endpoint de health multifomato (sin tocar la BD):
    - ?format=json   -> JSON {status, server_time, timezone}
    - ?format=plain  -> Texto plano "OK" (compatibilidad UptimeRobot)
    - Por defecto (sin format) -> HTML simple con tarjetita de estado.
    - También se acepta Accept: application/json para JSON.
    - Siempre añade cabecera X-Server-Time.
    """
    now = timezone.now()  # UTC
    server_time_iso = now.isoformat()
    if LIMA_TZ:
        lima_dt = now.astimezone(LIMA_TZ)
        lima_iso = lima_dt.isoformat()
    else:
        # Fallback (UTC-05 aproximado) sin DST
        lima_dt = now - timedelta(hours=5)
        lima_iso = lima_dt.isoformat()

    # Formatos solicitados
    utc_fmt = now.strftime("%Y-%m-%d %H:%M:%S")
    ampm = lima_dt.strftime("%I:%M %p").lstrip('0')  # ej. 12:55 PM
    offset = lima_dt.utcoffset() or timedelta(0)
    total_sec = int(offset.total_seconds())
    sign = '+' if total_sec >= 0 else '-'
    total_sec_abs = abs(total_sec)
    off_h = total_sec_abs // 3600
    off_m = (total_sec_abs % 3600) // 60
    tz_label = f"GMT{sign}{off_h}" if off_m == 0 else f"GMT{sign}{off_h}:{off_m:02d}"
    local_fmt = f"{ampm} ({tz_label})"

    fmt = request.GET.get('format')  # json | plain | None
    accept = request.headers.get('Accept', '')

    # Responder HEAD como 200 sin cuerpo
    if request.method == 'HEAD':
        resp = HttpResponse(status=200)
        resp["X-Server-Time"] = server_time_iso
        resp["X-Server-Time-Local"] = lima_iso
        resp["Cache-Control"] = "no-store, no-cache, must-revalidate"
        resp["Pragma"] = "no-cache"
        resp["X-Content-Type-Options"] = "nosniff"
        resp["Referrer-Policy"] = "no-referrer"
        return resp

    wants_json = (fmt == 'json') or ('application/json' in accept)
    wants_plain = (fmt == 'plain') or ('text/plain' in accept and fmt is None)

    if wants_json:
        data = {
            'status': 'ok',
            'server_time_utc': server_time_iso,
            'server_time_local': lima_iso,
            'local_timezone': 'America/Lima',
            'credit': 'Gracias a Aldo C.P.'
        }
        # También devolvemos los formatos "bonitos"
        data['server_time_utc_pretty'] = utc_fmt
        data['server_time_local_pretty'] = local_fmt
        resp = JsonResponse(data, status=200)
        resp["X-Server-Time"] = server_time_iso
        resp["X-Server-Time-Local"] = lima_iso
        resp["Cache-Control"] = "no-store, no-cache, must-revalidate"
        resp["Pragma"] = "no-cache"
        resp["X-Content-Type-Options"] = "nosniff"
        resp["Referrer-Policy"] = "no-referrer"
        return resp

    if wants_plain:
        resp = HttpResponse("OK", content_type="text/plain")
        resp["X-Server-Time"] = server_time_iso
        resp["X-Server-Time-Local"] = lima_iso
        resp["Cache-Control"] = "no-store, no-cache, must-revalidate"
        resp["Pragma"] = "no-cache"
        resp["X-Content-Type-Options"] = "nosniff"
        resp["Referrer-Policy"] = "no-referrer"
        return resp

    # HTML por defecto (sin consultas a BD)
    html = f"""
    <!DOCTYPE html>
    <html lang=\"es\">
    <head>
        <meta charset=\"UTF-8\">
        <title>Estado del Servidor</title>
        <meta name=\"robots\" content=\"noindex,nofollow\" />
        <style>
            :root {{ color-scheme: light dark; }}
            body {{
                font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
                background: #f4f4f9;
                margin:0; padding:40px; text-align:center;
            }}
            @media (prefers-color-scheme: dark) {{
                body {{ background:#1e1f24; color:#ddd; }}
                .card {{ background:#262830; color:#eee; box-shadow:0 4px 16px rgba(0,0,0,.5); }}
            }}
            .card {{
                background:#fff; padding:22px 30px; border-radius:14px;
                box-shadow:0 4px 12px rgba(0,0,0,0.08);
                display:inline-block; min-width:280px; max-width:480px;
            }}
            h1 {{ font-size:1.4rem; margin:0 0 10px; color:#2e7d32; }}
            p {{ margin:6px 0 0; font-size:.95rem; line-height:1.4; }}
            .meta {{ margin-top:14px; font-size:.75rem; opacity:.7; }}
            code {{ background:#ececec; padding:2px 4px; border-radius:4px; font-size:.75rem; }}
            @media (prefers-color-scheme: dark) {{ code {{ background:#333842; }} }}
        </style>
    </head>
    <body>
        <div class=\"card\">
            <h1>✅ Servidor Activo</h1>
            <p>Todo funcionando correctamente.</p>
            <div class=\"meta\">UTC: <code>{utc_fmt}</code></div>
            <div class=\"meta\">Hora Local (Perú): <code>{local_fmt}</code></div>
            <div class=\"meta\" style=\"margin-top:18px;\">✨ Gracias a Aldo C.P.</div>
        </div>
    </body>
    </html>
    """
    # HTML por defecto
    html += f"""
    <div style=\"margin-top:20px\"> 
        <a href=\"?format=plain\">Ver texto plano</a> · 
        <a href=\"?format=json\">Ver JSON</a>
    </div>
    """
    resp = HttpResponse(html, content_type="text/html; charset=utf-8")
    resp["X-Server-Time"] = server_time_iso
    resp["X-Server-Time-Local"] = lima_iso
    resp["Cache-Control"] = "no-store, no-cache, must-revalidate"
    resp["Pragma"] = "no-cache"
    resp["X-Content-Type-Options"] = "nosniff"
    resp["Referrer-Policy"] = "no-referrer"
    return resp
