import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proyento_fantasia.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

username = os.environ.get("SU_USERNAME", "admin")
email = os.environ.get("SU_EMAIL", "admin@example.com")
password = os.environ.get("SU_PASSWORD", "admin123")

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superusuario '{username}' creado con éxito.")
else:
    print(f"El superusuario '{username}' ya existe.")
