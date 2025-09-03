from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('mi_app', '0011_alter_banner_usar_descuentos_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='es_oferta',
            field=models.BooleanField(default=False, help_text="Márcalo para incluir este producto en el filtro 'Solo ofertas' aunque no tenga precio_oferta menor. Si hay precio_oferta menor que precio, se mostrará el % de descuento."),
        ),
    ]
