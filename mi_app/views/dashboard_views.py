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
    if categoria_slug:
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

    # --- LÓGICA DE FILTRO POR COLOR ELIMINADA ---
    # color = request.GET.get("color")
    # if color:
    #     productos_list = productos_list.filter(variantes__color__iexact=color)

    # 3. Aplicar orden
    orden = request.GET.get("orden")
    if orden == "price-asc":
        productos_list = productos_list.order_by("precio_efectivo")
    elif orden == "price-desc":
        productos_list = productos_list.order_by("-precio_efectivo")
    else:
        productos_list = productos_list.order_by("-id")

    productos_list = productos_list.distinct()

    # 4. Paginación
    paginator = Paginator(productos_list, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # 5. Contexto (limpio, asume que context_processors provee 'categorias_menu')
    context = {
        "productos": page_obj,
        "page_obj": page_obj,
        "banner": Banner.objects.filter(activo=True).first(),
        "filtros_activos": request.GET,
    }
    
    if request.headers.get('x-requested-with') == 'fetch':
        return render(request, 'partials/_product_list_ajax.html', context)

    return render(request, "mi_app/catalogo_publico.html", context)