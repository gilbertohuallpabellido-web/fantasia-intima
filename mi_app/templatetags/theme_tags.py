# mi_app/templatetags/theme_tags.py

from django import template
from django.utils.safestring import mark_safe
from ..models import ConfiguracionSitio

register = template.Library()

def hex_to_rgb_tuple(hex_color):
    """Convierte un color HEX (ej: #ff0000) a una tupla RGB (ej: (255, 0, 0))."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return (249, 168, 212) # Color por defecto si el formato es incorrecto

@register.simple_tag
def inject_theme_styles():
    """
    Obtiene la configuración del tema y la inyecta como variables CSS,
    incluyendo una versión RGB del color primario para transparencias.
    """
    try:
        config = ConfiguracionSitio.get_solo()
        
        # --- INICIO DE LA MEJORA: Convertir color primario a RGB ---
        rgb_primary = hex_to_rgb_tuple(config.color_primario)
        # --- FIN DE LA MEJORA ---
        
        font_imports = f"""
        @import url('{config.fuente_principal_url}');
        @import url('{config.fuente_marca_url}');
        """

        css_variables = f"""
        :root {{
            --brand-primary: {config.color_primario};
            --brand-primary-rgb: {rgb_primary[0]}, {rgb_primary[1]}, {rgb_primary[2]};
            --brand-secondary: {config.color_secundario};
            --brand-accent: {config.color_acento};
            --brand-brown: {config.color_marron};
            --brand-text: {config.color_texto};
        }}
        body {{
            font-family: {config.fuente_principal_nombre};
            background-color: #fffbff;
            color: var(--brand-text);
        }}
        .font-brand {{
            font-family: {config.fuente_marca_nombre};
        }}
        """
        
        style_html = f"<style>{font_imports}{css_variables}</style>"
        
        return mark_safe(style_html)

    except ConfiguracionSitio.DoesNotExist:
        return ""
