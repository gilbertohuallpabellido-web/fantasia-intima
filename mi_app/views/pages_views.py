# mi_app/views/pages_views.py
from django.shortcuts import render, get_object_or_404
from ..models import Pagina

def pagina_detalle(request, slug):
    """
    Muestra el contenido de una página informativa específica.
    """
    # Busca la página por su 'slug' y se asegura de que esté marcada como 'publicada'.
    pagina = get_object_or_404(Pagina, slug=slug, publicada=True)
    
    context = {
        'pagina': pagina,
    }
    return render(request, 'mi_app/pagina_detalle.html', context)
