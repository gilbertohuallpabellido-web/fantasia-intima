#!/usr/bin/env bash
# exit on error
set -o errexit

# Instala dependencias
pip install -r requirements.txt

# Recolecta archivos estáticos
python manage.py collectstatic --no-input

# Aplica migraciones
python manage.py migrate
```

### 2. ¿Ahora qué? (Los 3 Pasos Finales para la Victoria)

Ahora que ya tienes el "manual de instrucciones" correcto y limpio, solo sigue estos tres simples pasos para enviárselo a Render.

**1. Guarda y Envía la Actualización a GitHub:**

Ejecuta estos tres comandos en tu terminal, uno por uno:

```bash
# 1. Reúne los cambios (el nuevo build.sh)
git add .

# 2. Sella la caja con una etiqueta clara
git commit -m "Limpia el script de construcción para Render"

# 3. Envía la actualización a la nube
git push