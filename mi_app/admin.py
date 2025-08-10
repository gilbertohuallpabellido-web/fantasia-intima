# mi_app/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Producto, ColorVariante, PedidoWhatsApp, DetallePedidoWhatsApp
import json # <-- Importante para pasar datos a la plantilla

# --- Mapeo de colores para las muestras visuales ---
COLOR_MAP = {
    'black': '#000000',
    'white': '#FFFFFF',
    'red': '#FF0000',
    'wine': '#722F37',
    'nude': '#E3BC9A',
    'navy': '#000080',
    'pink': '#FFC0CB',
    'fuchsia': '#FF00FF',
    'purple': '#800080',
    'blue': '#0000FF',
    'green': '#008000',
    'yellow': '#FFFF00',
    'gold': '#FFD700',
    'silver': '#C0C0C0',
    'leopard': 'linear-gradient(45deg, #D4AF37, #A47B2A)',
    'snake': 'linear-gradient(45deg, #8A9A5B, #556B2F)',
}

# Permite añadir variantes de color directamente desde la página del producto
class ColorVarianteInline(admin.TabularInline):
    model = ColorVariante
    extra = 1

# --- AHORA USA UN TEMPLATE PERSONALIZADO ---
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio', 'es_nueva_coleccion', 'total_stock')
    list_filter = ('categoria', 'es_nueva_coleccion')
    search_fields = ('nombre', 'descripcion')
    inlines = [ColorVarianteInline]

    # Indica a Django que use un template personalizado para el formulario de añadir/editar
    change_form_template = 'admin/producto_change_form.html'

    # Pasa el mapa de colores al contexto del template para que el JavaScript pueda usarlo
    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['color_map'] = json.dumps(COLOR_MAP)
        return super().add_view(request, form_url, extra_context=extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['color_map'] = json.dumps(COLOR_MAP)
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

@admin.register(ColorVariante)
class ColorVarianteAdmin(admin.ModelAdmin):
    list_display = ('producto', 'color_con_muestra', 'stock')
    list_filter = ('producto__categoria',)
    search_fields = ('producto__nombre',)
    list_editable = ('stock',)

    def color_con_muestra(self, obj):
        color_code = COLOR_MAP.get(obj.color, '#FFFFFF')
        style = f'background: {color_code};'
        border = 'border: 1px solid #ccc;' if obj.color == 'white' else ''
        return format_html(
            '<span style="display: inline-block; width: 20px; height: 20px; border-radius: 50%; {style} {border} vertical-align: middle; margin-right: 8px;"></span>{color_name}',
            style=style,
            border=border,
            color_name=obj.get_color_display()
        )
    color_con_muestra.short_description = 'Color'

class DetallePedidoInline(admin.TabularInline):
    model = DetallePedidoWhatsApp
    readonly_fields = ('producto_nombre', 'variante_color', 'cantidad', 'precio_unitario', 'subtotal')
    extra = 0
    can_delete = False
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(PedidoWhatsApp)
class PedidoWhatsAppAdmin(admin.ModelAdmin):
    list_display = ('codigo_pedido', 'user', 'fecha_creacion', 'total')
    list_filter = ('fecha_creacion',)
    search_fields = ('codigo_pedido', 'user__username')
    readonly_fields = ('id', 'codigo_pedido', 'fecha_creacion', 'total', 'subtotal', 'costo_envio')
    inlines = [DetallePedidoInline]