#!/usr/bin/env bash
# exit on error
set -o errexit

# Instala dependencias
pip install -r requirements.txt

# Recolecta archivos estáticos
python manage.py collectstatic --no-input

# Aplica migraciones
python manage.py migrate
