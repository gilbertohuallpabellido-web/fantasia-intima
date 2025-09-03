from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('mi_app', '0012_producto_es_oferta'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='banner',
            name='productos_destacados',
        ),
        migrations.RemoveField(
            model_name='producto',
            name='en_grupo_banner',
        ),
    ]
