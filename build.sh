#!/usr/bin/env bash
# exit on error
set -o errexit

# Instala dependencias
pip install -r requirements.txt

# Recolecta archivos estáticos
python manage.py collectstatic --no-input

# Aplica migraciones
python manage.py migrate

# Crea superusuario automáticamente si no existe
python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
import os;
username = os.environ.get('DJANGO_SUPERUSER_USERNAME');
email = os.environ.get('DJANGO_SUPERUSER_EMAIL');
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD');
if username and password and not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
"
