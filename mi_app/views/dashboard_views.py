from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.db.models import Q, DecimalField
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from decimal import Decimal, InvalidOperation

from ..models import Producto, Categoria, Banner
from ..forms import ProductoForm, ColorVarianteFormSet

@login_required
def dashboard(request):
    if not request.user.is_staff:
        return redirect('catalogo_publico')
    # Prefetch corregido para evitar error con 'categoria_padre'
    productos = (Producto.objects
                 .select_related('categoria__parent')
                 .prefetch_related('variantes')
                 .all())
    return render(request, 'mi_app/dashboard.html', {'productos': productos})

@login_required
def subir_producto(request, pk=None):
    if not request.user.is_staff:
        return redirect('catalogo_publico')
        
    if pk:
        producto = get_object_or_404(Producto, pk=pk)
        titulo = "Modificar Producto"
    else:
        producto = None
        titulo = "Añadir Nuevo Producto"
    
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        formset = ColorVarianteFormSet(request.POST, request.FILES, instance=producto)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                producto = form.save()
                formset.instance = producto
                formset.save()
            return redirect('dashboard')
    else:
        form = ProductoForm(instance=producto)
        formset = ColorVarianteFormSet(instance=producto)

    contexto = {
        'titulo': titulo,
        'producto': producto,
        'form': form,
        'formset': formset,
    }
    return render(request, 'mi_app/subir_producto.html', contexto)

@login_required
def eliminar_producto(request, pk):
    if not request.user.is_staff:
        return redirect('catalogo_publico')
        
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.delete()
        messages.success(request, f'El producto "{producto.nombre}" ha sido eliminado correctamente.')
        return redirect('dashboard')
    return render(request, 'mi_app/eliminar_confirmacion.html', {'producto': producto})

def get_subcategories_json(request):
    parent_id = request.GET.get('parent_id')
    if not parent_id:
        return JsonResponse([], safe=False)
    subcategories = Categoria.objects.filter(parent_id=parent_id).values('id', 'nombre')
    return JsonResponse(list(subcategories), safe=False)

def catalogo_publico(request):
    """
    Muestra el catálogo público con filtros avanzados, búsqueda y paginación.
    Versión limpia y funcional.
    """
    # 1. Query base optimizada
    productos_list = (
        Producto.objects.select_related("categoria__parent")
        .prefetch_related("variantes")
        .annotate(
            precio_efectivo=Coalesce("precio_oferta", "precio", output_field=DecimalField())
        )
        .all()
    )

    # 2. Aplicar filtros (Lógica unificada y corregida)
    categoria_slug = request.GET.get("categoria")
    producto_unico_id = request.GET.get('producto')
    productos_multi = request.GET.get('productos')  # coma separada
    if productos_multi:
        ids = [p for p in productos_multi.split(',') if p.isdigit()]
        if ids:
            productos_list = productos_list.filter(pk__in=ids)
            print(f"DEBUG_PRODUCTOS_MULTI: filtrando ids={ids}")
    elif producto_unico_id:
        if producto_unico_id.isdigit():
            productos_list = productos_list.filter(pk=int(producto_unico_id))
            print(f"DEBUG_PRODUCTO_UNICO: filtrando producto id={producto_unico_id}")
        # Si se pasa producto, ignoramos el resto de filtros de categoría
    elif categoria_slug:
        if categoria_slug == "nueva_coleccion":
            productos_list = productos_list.filter(es_nueva_coleccion=True)
        else:
            try:
                cat = Categoria.objects.get(slug=categoria_slug)
                categorias_a_filtrar = cat.get_descendants(include_self=True)
                productos_list = productos_list.filter(categoria__in=categorias_a_filtrar)
            except Categoria.DoesNotExist:
                pass

    q = request.GET.get("q", "").strip()
    if q:
        # Buscar sobre campos normalizados + fallback original
        terms = [t.strip().lower() for t in q.split() if t.strip()]
        q_obj = Q()
        for t in terms:
            q_obj |= Q(nombre_norm__contains=t) | Q(descripcion_norm__contains=t)
        # Fallback por si faltan norm fields en algún registro
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

    # --- LÓGICA DE FILTRO POR COLOR ELIMINADA ---
    # color = request.GET.get("color")
    # if color:
    #     productos_list = productos_list.filter(variantes__color__iexact=color)

    # 3. Filtro solo_ofertas (checkbox es_oferta)
    if request.GET.get('solo_ofertas') == '1':
        try:
            marcados = list(Producto.objects.filter(es_oferta=True).values_list('id', flat=True))
            print(f"DEBUG_OFERTAS2: ids_marcados={marcados}")
        except Exception as e:
            print(f"DEBUG_OFERTAS2 error listando marcados: {e}")
        antes = productos_list.count()
        productos_list = productos_list.filter(es_oferta=True)
        try:
            ids_res = list(productos_list.values_list('id', flat=True))
            print(f"SOLO_OFERTAS2 FILTRO: antes={antes} despues={len(ids_res)} ids={ids_res}")
        except Exception:
            pass

    # 4. Aplicar orden
    orden = request.GET.get("orden")
    if orden == "price-asc":
        productos_list = productos_list.order_by("precio_efectivo")
    elif orden == "price-desc":
        productos_list = productos_list.order_by("-precio_efectivo")
    else:
        productos_list = productos_list.order_by("-id")

    productos_list = productos_list.distinct()

    # 5. Paginación (calculamos coincidencias antes)
    matched_count = productos_list.count()
    paginator = Paginator(productos_list, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # 6. Banner y flag mostrar_titulo_banner (mismo criterio que versión pública)
    banner_obj = Banner.objects.filter(activo=True).first()
    came_from_banner = bool(request.GET.get('banner') or request.GET.get('banner_id'))
    mostrar_titulo_banner = False
    if came_from_banner:
        if not categoria_slug or categoria_slug == 'nueva_coleccion':
            mostrar_titulo_banner = True

    context = {
        "productos": page_obj,
        "page_obj": page_obj,
        "banner": banner_obj,
        "filtros_activos": request.GET,
    "categorias_menu": Categoria.objects.filter(parent__isnull=True).prefetch_related('children'),
        "solo_ofertas": request.GET.get('solo_ofertas') == '1',
        "producto_unico": bool(producto_unico_id) and not productos_multi,
        "productos_multi": productos_multi,
        "matched_count": matched_count,
        "mostrar_titulo_banner": mostrar_titulo_banner,
    }
    
    # Responder parcial tanto para fetch personalizado como para peticiones estándar AJAX
    if request.headers.get('x-requested-with') in ('fetch', 'XMLHttpRequest'):
        return render(request, 'partials/_product_list_ajax.html', context)

    return render(request, "mi_app/catalogo_publico.html", context)