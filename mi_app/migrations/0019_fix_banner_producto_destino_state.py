from django.db import migrations, models

# Esta migración intenta estabilizar el estado cuando el grafo cree que debe
# quitar 'producto_destino' pero el campo ya no existe en models ni en DB.

def noop(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('mi_app', '0018_remove_banner_producto_destino'),
    ]

    operations = [
        # No hacemos nada; solo avanzamos el estado del proyecto.
        migrations.RunPython(noop, noop),
    ]
