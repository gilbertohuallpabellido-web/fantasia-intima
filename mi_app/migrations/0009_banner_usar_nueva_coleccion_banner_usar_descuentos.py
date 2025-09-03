from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('mi_app', '0008_producto_en_grupo_banner'),
    ]

    operations = [
        migrations.AddField(
            model_name='banner',
            name='usar_nueva_coleccion',
            field=models.BooleanField(default=False, help_text="Si se marca, el botón llevará a la vista filtrada de 'Nueva Colección'. Ignora productos seleccionados."),
        ),
        migrations.AddField(
            model_name='banner',
            name='usar_descuentos',
            field=models.BooleanField(default=False, help_text="Si se marca (y no 'nueva colección'), el botón llevará a productos con oferta activa."),
        ),
    ]
