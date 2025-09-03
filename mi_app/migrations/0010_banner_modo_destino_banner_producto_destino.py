from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('mi_app', '0009_banner_usar_nueva_coleccion_banner_usar_descuentos'),
    ]

    operations = [
        migrations.AddField(
            model_name='banner',
            name='modo_destino',
            field=models.CharField(choices=[('nueva', 'Nueva Colección'), ('ofertas', 'Productos en Oferta'), ('producto', 'Producto Individual'), ('enlace', 'Enlace Personalizado')], default='nueva', help_text='Qué mostrará el botón del banner.', max_length=20),
        ),
        migrations.AddField(
            model_name='banner',
            name='producto_destino',
            field=models.ForeignKey(blank=True, help_text="Selecciona el producto a mostrar si el modo es 'Producto Individual'.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='banners_destino', to='mi_app.producto'),
        ),
    ]
