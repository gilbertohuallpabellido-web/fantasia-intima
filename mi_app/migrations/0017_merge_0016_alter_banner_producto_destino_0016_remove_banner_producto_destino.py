from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('mi_app', '0016_alter_banner_producto_destino'),
        ('mi_app', '0016_remove_banner_producto_destino'),
    ]

    operations = [
        # Ambas ramas se fusionan. El campo producto_destino queda eliminado
        # porque la segunda migración lo quita. No se requieren operaciones extra.
    ]
