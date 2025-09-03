from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('mi_app', '0007_banner_fecha_fin_banner_fecha_inicio'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='en_grupo_banner',
            field=models.BooleanField(default=False, help_text='Marcado automáticamente cuando el producto forma parte del grupo destacado del banner activo.'),
        ),
    ]
