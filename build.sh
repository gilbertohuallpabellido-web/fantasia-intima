#!/usr/bin/env bash
# exit on error
set -o errexit

# Instala todas las dependencias listadas en requirements.txt
pip install -r requirements.txt

# Recolecta todos los archivos estáticos (CSS, JS, etc.) en un solo lugar
python manage.py collectstatic --no-input

# Aplica las migraciones de la base de datos para crear las tablas
python manage.py migrate
```

### ⚠️ ¡Paso Secreto de Sensei! (Súper Importante)

Como probablemente estás trabajando en Windows, necesitamos darle "permiso de ejecución" a este archivo para que los servidores de Render (que usan Linux) puedan usarlo.

Después de crear y guardar el archivo `build.sh`, abre tu terminal de `git` (Git Bash) y ejecuta este comando:

```bash
git update-index --chmod=+x build.sh