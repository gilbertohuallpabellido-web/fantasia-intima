from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal, InvalidOperation

# Se añade el modelo Pagina a las importaciones
from ..models import Producto, Categoria, Banner, Pagina

def catalogo_publico(request):
    """
    Muestra el catálogo público con filtros avanzados, búsqueda, ordenamiento 
    y paginación.
    """
    productos_list = (
        Producto.objects.select_related("categoria__parent")
        .prefetch_related("variantes")
        .annotate(
            precio_efectivo=Coalesce("precio_oferta", "precio", output_field=DecimalField())
        )
        .all()
    )

    categoria_slug = request.GET.get("categoria")
    if categoria_slug:
        if categoria_slug == "nueva_coleccion":
            productos_list = productos_list.filter(es_nueva_coleccion=True)
        else:
            try:
                cat = Categoria.objects.get(slug=categoria_slug)
                productos_list = productos_list.filter(
                    Q(categoria__in=cat.get_descendants(include_self=True))
                )
            except Categoria.DoesNotExist:
                pass

    q = request.GET.get("q", "").strip()
    if q:
        productos_list = productos_list.filter(
            Q(nombre__icontains=q) | Q(descripcion__icontains=q)
        )

    try:
        pmin = request.GET.get("precio_min")
        if pmin:
            productos_list = productos_list.filter(precio_efectivo__gte=Decimal(pmin))
            
        pmax = request.GET.get("precio_max")
        if pmax:
            productos_list = productos_list.filter(precio_efectivo__lte=Decimal(pmax))
    except (InvalidOperation, TypeError):
        pass

    color = request.GET.get("color")
    if color:
        productos_list = productos_list.filter(variantes__color__iexact=color)

    orden = request.GET.get("orden")
    if orden == "price-asc":
        productos_list = productos_list.order_by("precio_efectivo")
    elif orden == "price-desc":
        productos_list = productos_list.order_by("-precio_efectivo")
    else:
        productos_list = productos_list.order_by("-id")

    productos_list = productos_list.distinct()

    paginator = Paginator(productos_list, 12)
    page_number = request.GET.get("page")
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        "productos": page_obj,
        "page_obj": page_obj,
        "categorias_menu": Categoria.objects.filter(parent__isnull=True).prefetch_related('children'),
        "banner": Banner.objects.filter(activo=True).first(),
        "filtros_activos": request.GET,
    }
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'partials/_product_list_ajax.html', context)

    return render(request, "mi_app/catalogo_publico.html", context)


def producto_detalle(request, pk):
    """
    Muestra los detalles de un producto específico y una selección de productos
    relacionados con una lógica de prioridades EXCLUSIVA y REFACTORIZADA.
    """
    producto = get_object_or_404(
        Producto.objects.select_related("categoria__parent").prefetch_related(
            "variantes", 
            "categoria__categorias_relacionadas__children",
            "categoria__parent__categorias_relacionadas__children"
        ), 
        pk=pk
    )
    
    # === INICIO DE LA MEJORA: Lógica de relacionados más limpia y eficiente ===
    pks_excluidos = {producto.pk}
    productos_relacionados = []
    max_relacionados = 4

    def obtener_relacionados(queryset):
        """Función auxiliar para añadir productos sin duplicados."""
        nuevos = list(queryset.exclude(pk__in=pks_excluidos).order_by("?")[:max_relacionados - len(productos_relacionados)])
        if nuevos:
            productos_relacionados.extend(nuevos)
            pks_excluidos.update(p.pk for p in nuevos)

    if producto.categoria:
        # 1. Prioridad: Categorías explícitamente relacionadas
        related_categories_pks = set()
        for cat in producto.categoria.categorias_relacionadas.all():
            related_categories_pks.update(cat.get_descendants(include_self=True).values_list('pk', flat=True))
        if producto.categoria.parent:
             for cat in producto.categoria.parent.categorias_relacionadas.all():
                related_categories_pks.update(cat.get_descendants(include_self=True).values_list('pk', flat=True))
        
        if related_categories_pks:
            obtener_relacionados(Producto.objects.filter(categoria__pk__in=related_categories_pks))

        # 2. Si no se llenó, buscar en la misma categoría
        if len(productos_relacionados) < max_relacionados:
            obtener_relacionados(Producto.objects.filter(categoria=producto.categoria))

        # 3. Si aún no se llenó, buscar en la categoría padre
        if len(productos_relacionados) < max_relacionados and producto.categoria.parent:
            obtener_relacionados(Producto.objects.filter(categoria=producto.categoria.parent))
    
    # 4. Fallback final: Si no hay NADA, mostrar productos aleatorios
    if not productos_relacionados:
         productos_relacionados = list(Producto.objects.exclude(pk__in=pks_excluidos).order_by("?")[:max_relacionados])

    # === FIN DE LA MEJORA ===

    context = {
        "producto": producto,
        "productos_relacionados": productos_relacionados,
    }
    return render(request, "mi_app/producto_detalle.html", context)


def pagina_informativa_view(request, slug):
    """
    Muestra el contenido de una página informativa específica.
    """
    pagina = get_object_or_404(Pagina, slug=slug, publicada=True)
    context = {
        'pagina': pagina
    }
    return render(request, 'mi_app/pagina_informativa.html', context)