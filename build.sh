#!/usr/bin/env bash
# exit on error
set -o errexit

# Instala dependencias
pip install -r requirements.txt

# Recolecta archivos estáticos
python manage.py collectstatic --no-input

# Aplica migraciones
python manage.py migrate

# Registrar información de build (fallback si no hay variables de entorno en runtime)
COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "")
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "")
cat > build_info.json <<EOF
{"commit":"${COMMIT_SHA}","branch":"${BRANCH}","built_at":"${BUILD_TIME}"}
EOF

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
