from django.db import migrations, models


def set_default_provider(apps, schema_editor):
    ApiKey = apps.get_model('mi_app', 'ApiKey')
    ApiKey.objects.filter(provider__isnull=True).update(provider='gemini')

class Migration(migrations.Migration):

    dependencies = [
        ('mi_app', '0029_configuracionsitio_product_zoom_factor'),
    ]

    operations = [
        migrations.AddField(
            model_name='apikey',
            name='provider',
            field=models.CharField(choices=[('gemini', 'Gemini'), ('chatgpt', 'ChatGPT')], default='gemini', help_text='Proveedor al que pertenece esta clave.', max_length=20),
        ),
        migrations.AlterModelOptions(
            name='apikey',
            options={'ordering': ['-fecha_creacion'], 'verbose_name': 'Clave de API de IA', 'verbose_name_plural': 'Claves de API de IA'},
        ),
        migrations.AddField(
            model_name='configuracionchatbot',
            name='chat_provider',
            field=models.CharField(choices=[('gemini', 'Gemini'), ('chatgpt', 'ChatGPT')], default='gemini', help_text='Proveedor de IA que utilizará el chatbot.', max_length=20),
        ),
        migrations.AddField(
            model_name='configuracionchatbot',
            name='gemini_model_name',
            field=models.CharField(blank=True, default='gemini-1.5-flash-latest', help_text='Nombre del modelo Gemini (variable de entorno GEMINI_MODEL tiene prioridad si está definida).', max_length=100),
        ),
        migrations.AddField(
            model_name='configuracionchatbot',
            name='openai_model_name',
            field=models.CharField(blank=True, default='gpt-4o-mini', help_text='Nombre del modelo de OpenAI (variable de entorno OPENAI_MODEL tiene prioridad si está definida).', max_length=100),
        ),
        migrations.AddField(
            model_name='configuracionchatbot',
            name='temperature',
            field=models.FloatField(default=0.75, help_text='Temperatura creativa (0-1). Aplica a ambos proveedores.'),
        ),
        migrations.RunPython(set_default_provider, migrations.RunPython.noop),
    ]
