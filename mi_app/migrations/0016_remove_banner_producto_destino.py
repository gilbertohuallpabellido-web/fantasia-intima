from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('mi_app', '0015_merge_0014_alter_banner_enlace_0014_banner_productos_destacados'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='banner',
            name='producto_destino',
        ),
    ]
