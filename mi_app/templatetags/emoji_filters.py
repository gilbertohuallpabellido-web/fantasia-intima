from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
import re

register = template.Library()

# Patrón amplio para emojis comunes (incluye banderas, pictogramas, emoticonos, etc.)
# Nota: no cubre el 100% de combinaciones ZWJ complejas, pero es suficiente para casos habituales (💖, 🔥, ⭐, etc.).
_EMOJI_REGEX = re.compile(
    r"("  # inicio del grupo de captura
    r"[\U0001F1E6-\U0001F1FF]{2}"  # banderas (pares de indicadores regionales)
    r"|[\U0001F600-\U0001F64F]"     # emoticonos
    r"|[\U0001F300-\U0001F5FF]"     # símbolos y pictogramas
    r"|[\U0001F680-\U0001F6FF]"     # transporte y mapas
    r"|[\u2600-\u26FF]"             # símbolos misceláneos
    r"|[\u2700-\u27BF]"             # dingbats
    r"|[\U0001F900-\U0001F9FF]"     # símbolos y pictogramas suplementarios
    r"|[\U0001FA70-\U0001FAFF]"     # símbolos y pictogramas extendidos-A
    r")"  # fin del grupo de captura
    r"(\uFE0F)?"                     # selector de variación opcional
)


@register.filter(name="wrap_emojis")
def wrap_emojis(value: str) -> str:
    """Envuelve emojis detectados en span.keep-emoji para preservar su color nativo.

    - Escapa primero el texto para evitar inyección de HTML.
    - Rodea coincidencias de emoji con <span class="keep-emoji">…</span>.
    - Devuelve HTML seguro (mark_safe) listo para usar en plantillas.
    """
    if value is None:
        return ""
    text = conditional_escape(str(value))

    def _repl(match: re.Match) -> str:
        return f'<span class="keep-emoji">{match.group(0)}</span>'

    wrapped = _EMOJI_REGEX.sub(_repl, text)
    return mark_safe(wrapped)
