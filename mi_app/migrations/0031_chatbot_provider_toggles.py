from django.db import migrations, models


def sync_existing(apps, schema_editor):
    Config = apps.get_model('mi_app', 'ConfiguracionChatbot')
    for cfg in Config.objects.all():
        # Ajustar toggles según el valor previo de chat_provider
        if cfg.chat_provider == 'chatgpt':
            cfg.use_chatgpt = True
            cfg.use_gemini = False
        else:
            cfg.use_gemini = True
            cfg.use_chatgpt = False
        cfg.save()

class Migration(migrations.Migration):

    dependencies = [
        ('mi_app', '0030_chatbot_multi_provider'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracionchatbot',
            name='use_chatgpt',
            field=models.BooleanField(default=False, help_text='Activa ChatGPT como proveedor. Solo uno debe estar activo.'),
        ),
        migrations.AddField(
            model_name='configuracionchatbot',
            name='use_gemini',
            field=models.BooleanField(default=True, help_text='Activa Gemini como proveedor. Si marcas este y ChatGPT, se prioriza el último guardado que esté marcado solo.'),
        ),
        migrations.RunPython(sync_existing, migrations.RunPython.noop),
    ]
