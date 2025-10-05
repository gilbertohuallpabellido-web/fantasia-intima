from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse
import logging
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, DecimalField, F
from django.db.models.functions import Coalesce
from decimal import Decimal, InvalidOperation
from django.utils import timezone

# Se añade el modelo Pagina a las importaciones
from ..models import Producto, Categoria, Banner, Pagina, ColorVariante, ReservaStock

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
    productos_param = None  # eliminado soporte productos=
    skip_other_filters = False

    if not skip_other_filters and categoria_slug:
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

    if not skip_other_filters:
        q = request.GET.get("q", "").strip()
        if q:
            terms = [t.strip().lower() for t in q.split() if t.strip()]
            q_obj = Q()
            for t in terms:
                q_obj |= Q(nombre_norm__contains=t) | Q(descripcion_norm__contains=t)
            # Fallback adicional
            q_obj |= Q(nombre__icontains=q) | Q(descripcion__icontains=q)
            productos_list = productos_list.filter(q_obj)

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

        # Filtro de solo ofertas (precio_oferta no nulo y < precio)
        if request.GET.get('solo_ofertas') == '1':
            try:
                total_flags = Producto.objects.filter(es_oferta=True).values_list('id', flat=True)
                print(f"DEBUG_OFERTAS: ids_marcados={list(total_flags)}")
            except Exception as e:
                print(f"DEBUG_OFERTAS: error listando marcados: {e}")
            antes = productos_list.count()
            productos_list = productos_list.filter(es_oferta=True)
            try:
                ids_result = list(productos_list.values_list('id', flat=True))
                print(f"SOLO_OFERTAS FILTRO: antes={antes} despues={len(ids_result)} ids_result={ids_result}")
            except Exception as e:
                print(f"SOLO_OFERTAS FILTRO: error obteniendo ids_result {e}")

        orden = request.GET.get("orden")
        if orden == "price-asc":
            productos_list = productos_list.order_by("precio_efectivo")
        elif orden == "price-desc":
            productos_list = productos_list.order_by("-precio_efectivo")
        else:
            productos_list = productos_list.order_by("-id")

    productos_list = productos_list.distinct()

    # DEBUG: cantidad de productos que quedan tras aplicar filtros
    try:
        matched_count = productos_list.count()
    except Exception:
        matched_count = None

    # Log final para verificar que el queryset fue filtrado
    try:
        print(f"CATALOG VIEW: productos_param={productos_param} matched_count={matched_count}")
    except Exception:
        pass

    paginator = Paginator(productos_list, 12)
    page_number = request.GET.get("page")
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # Modo especial activado por banner (cualquier destino que fuerza vista estática):
    banner_mode_active = request.GET.get('solo_ofertas') == '1' or (categoria_slug == 'nueva_coleccion')

    # Flag para mostrar título de banner solo si llegó desde click de banner
    came_from_banner = bool(request.GET.get('banner') or request.GET.get('banner_id'))
    mostrar_titulo_banner = False
    if came_from_banner:
        # Mostrar siempre si viene de banner y no se ha cambiado a otra categoría distinta del target.
        # Permitimos 'nueva_coleccion' porque es el destino natural de modo nueva.
        if not categoria_slug or categoria_slug == 'nueva_coleccion':
            mostrar_titulo_banner = True

    context = {
        "productos": page_obj,
        "page_obj": page_obj,
        "categorias_menu": Categoria.objects.filter(parent__isnull=True).prefetch_related('children'),
        # banners_activos ahora se provee globalmente por el context_processor `banners_context`
        "filtros_activos": request.GET,
        # Solo para mensaje específico de "productos seleccionados" mantenemos filtered_from_banner (lista explícita)
    "filtered_from_banner": False,
    "solo_ofertas": request.GET.get('solo_ofertas') == '1',
    "solo_descuentos": False,
        "matched_count": matched_count,
    "has_grupo_banner": False,
        # Nuevo flag global para desactivar AJAX también en modos 'solo_ofertas' y 'nueva_coleccion'
        "banner_mode_active": banner_mode_active,
        "mostrar_titulo_banner": mostrar_titulo_banner,
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
    # Calcular stock inicial usando la propiedad del modelo (no asignar al property)
    initial_variant = producto.variantes.first()
    initial_stock = initial_variant.stock_disponible if initial_variant else 0
    
    # === INICIO NUEVA LÓGICA DE RELACIONADOS (cross-selling + jerarquía) ===
    # Prioridad añadida según nueva indicación:
    # 0. Si hay categorias_relacionadas definidas (en la categoría o su padre) => usar SOLO productos de esas categorías (hasta 4).
    #    Si encuentra alguno, NO sigue a las demás reglas.
    # Luego reglas jerárquicas anteriores (1..fallback):
    # 1. Misma subcategoría (hermanos) (si la categoría tiene padre) sin rellenar con otros.
    # 2. Si no hay hermanos, usar categoría padre.
    # 3. Si categoría es raíz: otros productos de la misma categoría raíz.
    # 4. Fallback global solo si sigue vacío.

    max_relacionados = 4
    productos_relacionados = []
    categoria_actual = producto.categoria

    if categoria_actual:
        # Paso 0: categorias_relacionadas explícitas (incluyendo descendientes de cada una)
        related_cats_pks = set()
        for cat in categoria_actual.categorias_relacionadas.all():
            related_cats_pks.update(cat.get_descendants(include_self=True).values_list('pk', flat=True))
        if categoria_actual.parent:
            for cat in categoria_actual.parent.categorias_relacionadas.all():
                related_cats_pks.update(cat.get_descendants(include_self=True).values_list('pk', flat=True))
        if related_cats_pks:
            qs = Producto.objects.filter(categoria__pk__in=related_cats_pks).exclude(pk=producto.pk)
            productos_relacionados = list(qs.order_by('?')[:max_relacionados])

        # Solo aplicar jerarquía si aún vacío
        if not productos_relacionados:
            es_subcategoria = categoria_actual.parent is not None
            if es_subcategoria:
                hermanos_qs = Producto.objects.filter(categoria=categoria_actual).exclude(pk=producto.pk)
                productos_relacionados = list(hermanos_qs.order_by('?')[:max_relacionados])
                if not productos_relacionados:
                    padre = categoria_actual.parent
                    if padre:
                        padre_qs = Producto.objects.filter(categoria=padre).exclude(pk=producto.pk)
                        productos_relacionados = list(padre_qs.order_by('?')[:max_relacionados])
            else:
                raiz_qs = Producto.objects.filter(categoria=categoria_actual).exclude(pk=producto.pk)
                productos_relacionados = list(raiz_qs.order_by('?')[:max_relacionados])

    if not productos_relacionados:
        productos_relacionados = list(Producto.objects.exclude(pk=producto.pk).order_by('?')[:max_relacionados])
    # === FIN NUEVA LÓGICA DE RELACIONADOS ===

    context = {
        "producto": producto,
        "productos_relacionados": productos_relacionados,
        "initial_stock": initial_stock,
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


def search_suggest(request):
    """Devuelve sugerencias de productos para el buscador en vivo (JSON)."""
    q = (request.GET.get('q') or '').strip()
    try:
        limit = int(request.GET.get('limit') or 5)
    except ValueError:
        limit = 5

    data = {"query": q, "results": [], "total": 0}
    if len(q) < 2:
        return JsonResponse(data)

    terms = [t.strip().lower() for t in q.split() if t.strip()]
    qs = Producto.objects.select_related('categoria').only('id','nombre','precio','precio_oferta','imagen_principal','categoria')
    q_obj = Q()
    if terms:
        for t in terms:
            q_obj |= Q(nombre_norm__contains=t) | Q(descripcion_norm__contains=t)
    # Fallback adicional siempre presente
    q_obj |= Q(nombre__icontains=q) | Q(descripcion__icontains=q)
    qs = qs.filter(q_obj).order_by('-id')
    total = qs.count()
    prods = list(qs[:limit])

    results = []
    for p in prods:
        # Precio efectivo
        precio = p.precio_oferta if (p.precio_oferta and p.precio_oferta < p.precio) else p.precio
        # Imagen (principal o nada)
        img = ''
        try:
            if p.imagen_principal and getattr(p.imagen_principal, 'url', ''):
                img = p.imagen_principal.url
        except Exception:
            img = ''

        results.append({
            'id': p.id,
            'name': p.nombre,
            'price': str(precio),
            'image': img,
            'url': reverse('producto_detalle', args=[p.id]),
        })

    data['results'] = results
    data['total'] = total
    return JsonResponse(data)