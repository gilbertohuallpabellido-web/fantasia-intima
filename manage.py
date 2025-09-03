#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
try:
    import dotenv
except ImportError:  # fallback silencioso si no está instalado
    dotenv = None

def main():
    """Run administrative tasks."""
    if dotenv:
        dotenv.load_dotenv()
    # === INICIO DE LA MEJORA: Apuntamos al cerebro correcto ===
    # Le decimos a Django que SIEMPRE use la configuración de 'mi_proyecto'.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mi_proyecto.settings')
    # === FIN DE LA MEJORA ===
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()