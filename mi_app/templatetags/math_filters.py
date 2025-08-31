# mi_app/templatetags/math_filters.py

from django import template

register = template.Library()

@register.filter
def mult(value, arg):
    """Multiplica el valor por el argumento."""
    try:
        return value * arg
    except (ValueError, TypeError):
        return ''
