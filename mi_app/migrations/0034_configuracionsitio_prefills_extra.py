from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('mi_app', '0033_configuracionsitio_whatsapp_prefill'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracionsitio',
            name='whatsapp_prefill_promo',
            field=models.CharField(
                max_length=200,
                blank=True,
                default='Hola {store_name}, vi la promoción y quiero saber más.',
                help_text='Prefill para el popup / pill de promoción que abre WhatsApp. Usa {store_name}.'
            ),
        ),
        migrations.AddField(
            model_name='configuracionsitio',
            name='whatsapp_prefill_chatbot',
            field=models.CharField(
                max_length=200,
                blank=True,
                default='Hola {store_name}, el asistente no pudo responder mi duda.',
                help_text='Prefill usado cuando el chatbot ofrece ir a WhatsApp (fallback). Usa {store_name}.'
            ),
        ),
        migrations.AddField(
            model_name='configuracionsitio',
            name='whatsapp_roulette_win_message',
            field=models.TextField(
                blank=True,
                default='¡Hola {store_name}! Gané el premio "{prize_name}" en la ruleta y quiero reclamarlo. 🎉',
                help_text='Plantilla del mensaje para reclamar premio de la ruleta. Placeholders: {store_name}, {prize_name}.'
            ),
        ),
    ]
