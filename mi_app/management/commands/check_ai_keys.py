import json
import time
import requests
from django.core.management.base import BaseCommand
from mi_app.models import ApiKey, ConfiguracionChatbot

GEMINI_TEST_MODELS = ["gemini-1.5-flash", "gemini-pro", "gemini-1.0-pro"]
OPENAI_TEST_MODEL = "gpt-4o-mini"

class Command(BaseCommand):
    help = "Verifica el estado de las claves de IA (Gemini y ChatGPT) intentando una petición mínima."

    def add_arguments(self, parser):
        parser.add_argument('--provider', choices=['gemini','chatgpt','all'], default='all', help='Filtrar proveedor a validar.')
        parser.add_argument('--timeout', type=int, default=12, help='Timeout por clave (segundos).')
        parser.add_argument('--model', type=str, default=None, help='Forzar un modelo Gemini específico (omite lista).')

    def handle(self, *args, **options):
        provider = options['provider']
        timeout = options['timeout']
        summary = {}
        if provider in ('gemini','all'):
            summary['gemini'] = self._check_gemini(timeout, model=options.get('model'))
        if provider in ('chatgpt','all'):
            summary['chatgpt'] = self._check_openai(timeout)
        self.stdout.write(self.style.SUCCESS(json.dumps(summary, ensure_ascii=False, indent=2)))

    def _check_gemini(self, timeout, model=None):
        results = []
        keys = list(ApiKey.objects.filter(provider='gemini', activa=True).values_list('key', flat=True))
        if not keys:
            return {"status": "sin_claves"}
        payload = {"contents": [{"role":"user","parts":[{"text":"ping"}]}]}
        models_to_try = [model] if model else GEMINI_TEST_MODELS
        for key in keys:
            ok = False
            err = None
            for m in models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"
                try:
                    r = requests.post(url, json=payload, timeout=timeout)
                    if r.status_code == 200:
                        ok = True
                        break
                    elif r.status_code == 404:
                        err = f"404 modelo {m}"; continue
                    else:
                        err = f"{r.status_code} {r.text[:80]}"; break
                except requests.exceptions.RequestException as e:
                    err = str(e); break
                time.sleep(0.5)
            results.append({"key_tail": key[-6:], "ok": ok, "error": err, "model_forzado": model})
        return {"total": len(results), "validas": sum(1 for r in results if r['ok']), "detalle": results}

    def _check_openai(self, timeout):
        results = []
        keys = list(ApiKey.objects.filter(provider='chatgpt', activa=True).values_list('key', flat=True))
        if not keys:
            return {"status": "sin_claves"}
        url = "https://api.openai.com/v1/chat/completions"
        body = {"model": OPENAI_TEST_MODEL, "messages": [{"role":"user","content":"ping"}], "max_tokens": 5}
        headers_base = {"Content-Type": "application/json"}
        for key in keys:
            headers = dict(headers_base)
            headers["Authorization"] = f"Bearer {key}"
            ok = False
            quota = False
            err = None
            try:
                r = requests.post(url, headers=headers, data=json.dumps(body), timeout=timeout)
                if r.status_code == 200:
                    ok = True
                elif r.status_code == 429:
                    quota = True
                    err = "429 quota"
                else:
                    err = f"{r.status_code} {r.text[:80]}"
            except requests.exceptions.RequestException as e:
                err = str(e)
            results.append({"key_tail": key[-6:], "ok": ok, "quota": quota, "error": err})
            time.sleep(0.5)
        return {"total": len(results), "validas": sum(1 for r in results if r['ok']), "cuota": sum(1 for r in results if r['quota']), "detalle": results}
