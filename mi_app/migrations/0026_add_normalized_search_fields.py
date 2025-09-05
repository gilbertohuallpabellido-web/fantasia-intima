from django.db import migrations, models
import unicodedata
import re


def normalize_text(text):
    if not text:
        return ''
    norm = unicodedata.normalize('NFKD', str(text))
    norm = norm.encode('ascii', 'ignore').decode('ascii').lower()
    norm = re.sub(r"\s+", " ", norm).strip()
    return norm


def populate_norm_fields(apps, schema_editor):
    Producto = apps.get_model('mi_app', 'Producto')
    for p in Producto.objects.all().iterator():
        p.nombre_norm = normalize_text(p.nombre)
        p.descripcion_norm = normalize_text(p.descripcion)
        p.save(update_fields=['nombre_norm', 'descripcion_norm'])


class Migration(migrations.Migration):
    dependencies = [
        ('mi_app', '0025_reservastock_user_carrito_carritoitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='nombre_norm',
            field=models.CharField(default='', max_length=255, db_index=True),
        ),
        migrations.AddField(
            model_name='producto',
            name='descripcion_norm',
            field=models.TextField(default='', blank=True),
        ),
        migrations.RunPython(populate_norm_fields, migrations.RunPython.noop),
    ]
