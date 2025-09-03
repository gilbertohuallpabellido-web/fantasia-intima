from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('mi_app', '0013_remove_banner_productos_destacados_remove_producto_en_grupo_banner'),
    ]

    operations = [
        migrations.AddField(
            model_name='banner',
            name='productos_destacados',
            field=models.ManyToManyField(blank=True, help_text="Selecciona uno o varios productos para este banner si el modo es 'Producto Individual'. Si seleccionas solo uno se irá directo al detalle; si son varios, se listarán filtrados en el catálogo.", related_name='banners_productos', to='mi_app.producto'),
        ),
    ]
