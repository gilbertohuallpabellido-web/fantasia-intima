from django.db import migrations


def update_old_message(apps, schema_editor):
    ConfiguracionSitio = apps.get_model('mi_app', 'ConfiguracionSitio')
    try:
        cfg = ConfiguracionSitio.objects.get()
    except ConfiguracionSitio.DoesNotExist:
        return
    if not cfg.whatsapp_roulette_win_message:
        return
    if '"{prize_name}"' in cfg.whatsapp_roulette_win_message and '{coupon_code}' in cfg.whatsapp_roulette_win_message:
        new_msg = cfg.whatsapp_roulette_win_message.replace('"{prize_name}"', "'{prize_name}'")
        new_msg = new_msg.replace('{store_name}! ', '')
        new_msg = new_msg.replace('¡Hola  Acabo', '¡Hola! Acabo')
        if not new_msg.startswith('¡Hola!'):
            if new_msg.startswith('¡Hola '):
                new_msg = new_msg.replace('¡Hola ', '¡Hola! ', 1)
        cfg.whatsapp_roulette_win_message = new_msg
        cfg.save(update_fields=['whatsapp_roulette_win_message'])


def noop(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('mi_app', '0035_chatgptapikey_geminiapikey_and_more'),
    ]

    operations = [
        migrations.RunPython(update_old_message, noop)
    ]
