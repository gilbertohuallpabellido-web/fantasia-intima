#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. Instala todas las herramientas de la lista
pip install -r requirements.txt

# 2. Reúne todos los archivos de diseño (CSS, JS, etc.)
python manage.py collectstatic --no-input

# 3. Construye la base de datos con los planos más recientes
python manage.py migrate
```

### ¿Ahora qué? (Los 3 Pasos Finales para la Victoria)

Ahora que ya tienes el "manual de instrucciones" correcto, solo sigue estos tres simples pasos para enviárselo a Render.

**1. Actualiza tu `build.sh`:**

* Ve a tu archivo `build.sh` en tu proyecto.
* **Reemplaza todo su contenido** con el código que te acabo de dar.

**2. Guarda y Envía la Actualización a GitHub:**

Ejecuta estos tres comandos en tu terminal, uno por uno:

```bash
# 1. Reúne los cambios (el nuevo build.sh)
git add .

# 2. Sella la caja con una etiqueta clara
git commit -m "Corrige el script de construcción build.sh"

# 3. Envía la actualización a la nube
git push
