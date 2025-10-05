from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('mi_app', '0032_configuracionchatbot_last_valid_gemini_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracionsitio',
            name='whatsapp_prefill_message',
            field=models.CharField(
                max_length=200,
                blank=True,
                default='Hola {store_name}, quiero más información.',
                help_text='Mensaje inicial para el enlace flotante de WhatsApp (redes sociales). Puedes usar {store_name}. Dejar vacío para no añadir texto.'
            ),
        ),
    ]
