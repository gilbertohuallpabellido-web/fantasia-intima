from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('mi_app', '0028_configuracionsitio_whatsapp_message_prefix_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracionsitio',
            name='product_zoom_factor',
            field=models.FloatField(
                default=2.0,
                validators=[
                    django.core.validators.MinValueValidator(1.0),
                    django.core.validators.MaxValueValidator(5.0)
                ],
                verbose_name='Factor de zoom de producto',
                help_text='Cuánto se amplía la imagen del producto al hacer hover (PC) o pinch/doble tap (móvil). Rango recomendado 1.0 a 5.0.'
            ),
        ),
    ]
