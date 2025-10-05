from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("mi_app", "0031_chatbot_provider_toggles"),
    ]

    operations = [
        migrations.AddField(
            model_name="configuracionchatbot",
            name="last_valid_gemini_model",
            field=models.CharField(
                max_length=120,
                blank=True,
                default="",
                help_text="(Auto) Último modelo Gemini que respondió correctamente. Tiene prioridad mientras exista."
            ),
        ),
    ]
