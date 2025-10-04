from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.forms import TextInput, ModelForm
from django import forms
from mptt.admin import DraggableMPTTAdmin
from .models import (
    Producto, ColorVariante, PedidoWhatsApp, DetallePedidoWhatsApp, 
    ConfiguracionSitio, Categoria, Banner, Pagina, ApiKey, Direccion,
    ConfiguracionRuleta, PremioRuleta, Cupon, TiradaRuleta, ConfiguracionChatbot
)
from solo.admin import SingletonModelAdmin

# --- Inline para subcategorías ---
class SubCategoriaInline(admin.TabularInline):
    model = Categoria
    fk_name = 'parent'
    extra = 1
    verbose_name = "Subcategoría"
    verbose_name_plural = "Subcategorías"
    fields = ('nombre', 'slug')
    show_change_link = True

# --- Admin de Categorías ---
@admin.register(Categoria)
class CategoriaAdmin(DraggableMPTTAdmin):
    list_display = ('tree_actions', 'indented_title',)
    list_display_links = ('indented_title',)
    prepopulated_fields = {'slug': ('nombre',)}
    search_fields = ('nombre',)
    inlines = [SubCategoriaInline]
    filter_horizontal = ('categorias_relacionadas',)
    fieldsets = (
        (None, {
            'fields': ('nombre', 'slug', 'parent')
        }),
        ('Cross-Selling (Venta Cruzada)', {
            'fields': ('categorias_relacionadas',)
        }),
    )

# --- Formulario para el selector de color ---
class ColorVarianteForm(ModelForm):
    class Meta:
        model = ColorVariante
        fields = '__all__'
        widgets = {
            'color': TextInput(attrs={'type': 'color'}),
        }

# --- Inline para Variantes de Color (usado en ProductoAdmin) ---
class ColorVarianteInline(admin.TabularInline):
    model = ColorVariante
    form = ColorVarianteForm
    extra = 1
    # === INICIO DE LA MEJORA: Añadimos el nuevo campo al formulario ===
    fields = ('codigo', 'color', 'imagen_textura', 'imagen', 'stock') 
    # === FIN DE LA MEJORA ===


# --- Formulario Personalizado para Producto ---
class ProductoAdminForm(forms.ModelForm):
    categoria_padre = forms.ModelChoiceField(
        queryset=Categoria.objects.filter(parent=None),
        required=False,
        label="Categoría principal"
    )
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.none(),
        label="Subcategoría",
        required=False
    )

    class Meta:
        model = Producto
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.categoria:
            categoria_obj = self.instance.categoria
            if categoria_obj.parent:
                self.fields['categoria_padre'].initial = categoria_obj.parent
                self.fields['categoria'].queryset = Categoria.objects.filter(parent=categoria_obj.parent)
                self.fields['categoria'].initial = categoria_obj
            else:
                self.fields['categoria_padre'].initial = categoria_obj
                self.fields['categoria'].queryset = Categoria.objects.filter(parent=categoria_obj)
        else:
            self.fields['categoria'].queryset = Categoria.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        categoria = cleaned_data.get('categoria')
        categoria_padre = cleaned_data.get('categoria_padre')
        if not categoria and categoria_padre:
            cleaned_data['categoria'] = categoria_padre
        if not self.instance.pk and not categoria and not categoria_padre:
            pass
        elif not cleaned_data.get('categoria'):
            self.add_error('categoria', 'Este campo es obligatorio.')

        # Validación de oferta (relajada):
        # - es_oferta puede ir sin precio_oferta (solo etiqueta y filtro)
        # - si hay precio_oferta, debe ser menor al precio normal
        es_oferta = cleaned_data.get('es_oferta')
        precio = cleaned_data.get('precio')
        precio_oferta = cleaned_data.get('precio_oferta')
        if precio_oferta is not None and precio is not None:
            try:
                if precio_oferta >= precio:
                    self.add_error('precio_oferta', 'Debe ser menor que el precio normal.')
            except Exception:
                pass
        if not es_oferta and not precio_oferta:
            # nada especial; si quieres limpiar explícitamente podrías hacerlo
            pass
        return cleaned_data

    class Media:
        js = ('admin/js/dynamic_subcategories.js',)

# --- Admin de Productos ---
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    form = ProductoAdminForm
    list_display = ('nombre', 'get_categoria_padre', 'categoria', 'precio', 'precio_oferta', 'tiene_descuento_real', 'es_oferta', 'es_nueva_coleccion')
    fieldsets = (
        (None, {
            'fields': ('nombre', 'categoria_padre', 'categoria', 'descripcion', 'imagen_principal')
        }),
        ('Precios y Ofertas', {
            'fields': ('precio', 'precio_oferta', 'es_oferta')
        }),
    ('Opciones Adicionales', {
        'fields': ('es_nueva_coleccion',)
        }),
    )
    # Filtros: añadimos filtro booleano manual para distinguir descuento real (precio_oferta < precio)
    class DescuentoRealFilter(admin.SimpleListFilter):
        title = 'Descuento real'
        parameter_name = 'descuento_real'

        def lookups(self, request, model_admin):
            return (
                ('1', 'Sí'),
                ('0', 'No'),
            )

        def queryset(self, request, queryset):
            val = self.value()
            if val == '1':
                return queryset.filter(precio_oferta__isnull=False, precio_oferta__lt=models.F('precio'))
            if val == '0':
                # Sin descuento real: o no tiene precio_oferta o no es menor
                return queryset.exclude(precio_oferta__isnull=False, precio_oferta__lt=models.F('precio'))
            return queryset

    list_filter = ('categoria__parent', 'categoria', 'es_nueva_coleccion', 'es_oferta', DescuentoRealFilter)
    search_fields = ('nombre', 'descripcion', 'categoria__nombre')
    list_editable = ('precio', 'precio_oferta', 'es_oferta', 'es_nueva_coleccion')
    inlines = [ColorVarianteInline]

    class Media:
        # Incluimos también el JS de subcategorías ya usado más un script para UX de ofertas
        js = ('admin/js/dynamic_subcategories.js', 'admin/js/producto_oferta_toggle.js')

    # Columna calculada: indica si existe descuento real (precio_oferta menor)
    def tiene_descuento_real(self, obj):
        return obj.descuento_porcentaje > 0
    tiene_descuento_real.boolean = True
    tiene_descuento_real.short_description = 'Desc. real'

    def get_categoria_padre(self, obj):
        return obj.categoria_padre
    get_categoria_padre.short_description = 'Categoría Padre'

# --- Admin de Variantes de Color (para vista individual) ---
@admin.register(ColorVariante)
class ColorVarianteAdmin(admin.ModelAdmin):
    form = ColorVarianteForm
    list_display = ('producto', 'codigo', 'color_con_muestra', 'stock')
    list_filter = ('producto__categoria',)
    search_fields = ('producto__nombre', 'codigo')
    list_editable = ('codigo', 'stock',)

    def color_con_muestra(self, obj):
        color_code = obj.color
        return format_html(
            '<span style="display: inline-block; width: 20px; height: 20px; border-radius: 50%; background-color: {color_code}; border: 1px solid #ccc; vertical-align: middle; margin-right: 8px;"></span>{color_code}',
            color_code=color_code
        )
    color_con_muestra.short_description = 'Color'

# --- Admin de Pedidos ---
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

# --- Formulario con selectores de color para la configuración ---
class ConfiguracionSitioForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionSitio
        fields = '__all__'
        widgets = {
            'color_primario': TextInput(attrs={'type': 'color'}),
            'color_secundario': TextInput(attrs={'type': 'color'}),
            'color_acento': TextInput(attrs={'type': 'color'}),
            'color_marron': TextInput(attrs={'type': 'color'}),
            'color_texto': TextInput(attrs={'type': 'color'}),
        }

# --- Admin de Configuración del Sitio con Pestañas de Tema ---
@admin.register(ConfiguracionSitio)
class ConfiguracionSitioAdmin(SingletonModelAdmin):
    form = ConfiguracionSitioForm
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre_tienda', 'logo')
        }),
        ('Redes Sociales y Contacto', {
            'fields': ('whatsapp_link', 'facebook_link', 'instagram_link', 'tiktok_link', 'numero_yape_plin')
        }),
        ('Promociones emergentes', {
            'fields': (
                'show_promo_new_collection',
                'show_promo_offers',
                'show_promo_whatsapp',
                'promo_cooldown_seconds',
            ),
            'description': 'Activa/desactiva cada tipo de promoción y define el intervalo de aparición.'
        }),
        ('WhatsApp (mensaje del carrito)', {
            'fields': (
                'whatsapp_message_prefix',
                'whatsapp_message_template',
            ),
            'description': 'Personaliza el mensaje que se envía por WhatsApp desde el carrito. Usa {store_name}, {prefix}, {order_code}, {order_url}, {items}, {total}.'
        }),
        ('Experiencia de Producto', {
            'fields': ('product_zoom_factor',),
            'description': 'Controla el nivel de zoom por defecto en la imagen del detalle de producto (PC y móvil).'
        }),
        # === INICIO DE LA MEJORA: Añadir sección para imágenes de pago ===
        ('Imágenes de Métodos de Pago', {
            'classes': ('collapse',),
            'fields': ('imagen_yape', 'imagen_plin'),
            'description': 'Sube aquí los logos de Yape y Plin para que se muestren en la página de pago.'
        }),
        # === FIN DE LA MEJORA ===
        ('🎨 Personalización de Colores', {
            'classes': ('collapse',),
            'fields': (
                'color_primario', 'color_secundario', 'color_acento',
                'color_marron', 'color_texto'
            )
        }),
        ('✍️ Personalización de Fuentes', {
            'classes': ('collapse',),
            'fields': (
                'fuente_principal_url', 'fuente_principal_nombre', 
                'fuente_marca_url', 'fuente_marca_nombre'
            )
        }),
        ('🔄 Acciones', {
            'fields': ('resetear_estilos',)
        }),
    )

# --- Admin de Banners ---
@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    class BannerAdminForm(forms.ModelForm):
        # Checkboxes virtuales
        opt_nueva = forms.BooleanField(label="Nueva Colección", required=False)
        opt_ofertas = forms.BooleanField(label="Ofertas (precio oferta)", required=False)
        opt_link = forms.BooleanField(label="Link personalizado", required=False)
        opt_producto = forms.BooleanField(label="Producto individual", required=False)

        class Meta:
            model = Banner
            fields = '__all__'
            widgets = {}

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Inicializar checkboxes según modo_destino guardado
            modo = getattr(self.instance, 'modo_destino', 'nueva') or 'nueva'
            self.fields['opt_nueva'].initial = (modo == 'nueva')
            self.fields['opt_ofertas'].initial = (modo == 'ofertas')
            self.fields['opt_link'].initial = (modo == 'enlace')
            self.fields['opt_producto'].initial = (modo == 'producto')

        def clean(self):
            cleaned = super().clean()
            seleccionados = [
                cleaned.get('opt_nueva'),
                cleaned.get('opt_ofertas'),
                cleaned.get('opt_link'),
                cleaned.get('opt_producto'),
            ]
            count_sel = sum(bool(x) for x in seleccionados)
            if count_sel == 0:
                cleaned['opt_nueva'] = True
            elif count_sel > 1:
                raise forms.ValidationError("Selecciona solo una opción de destino (una casilla).")

            # Validaciones dependientes
            if cleaned.get('opt_link') and not cleaned.get('enlace'):
                self.add_error('enlace', 'Debes ingresar un enlace.')
            if cleaned.get('opt_producto'):
                prod_multi = cleaned.get('productos_destacados')
                if not prod_multi or prod_multi.count() == 0:
                    self.add_error('productos_destacados', 'Selecciona al menos un producto.')
            return cleaned

    list_display = ('titulo', 'activo')
    list_filter = ('activo','fecha_inicio','fecha_fin')
    list_editable = ('activo',)
    filter_horizontal = ('productos_destacados',)
    form = BannerAdminForm
    fieldsets = (
        (None, {'fields': ('titulo', 'subtitulo', 'imagen', 'activo')}),
        ('Destino (elige UNA casilla)', {
            'fields': (
                'opt_nueva', 'opt_ofertas', 'opt_link', 'opt_producto',
                'productos_destacados', 'enlace', 'texto_boton'
            ),
            'description': 'Marca solo UNA opción:\n- Nueva Colección → filtra nueva.\n- Ofertas → solo ofertas.\n- Link → usa el enlace.\n- Producto → se listan los productos seleccionados (múltiples soportados).'
        }),
        ('Rango de Fechas (Opcional)', {
            'fields': ('fecha_inicio', 'fecha_fin'),
            'classes': ('collapse',),
            'description': 'Mostrar solo dentro del intervalo.'
        }),
    )

    def save_model(self, request, obj, form, change):
        # Mapear checkbox a modo_destino
        if form.cleaned_data.get('opt_nueva'):
            obj.modo_destino = 'nueva'
            obj.enlace = ''
        elif form.cleaned_data.get('opt_ofertas'):
            obj.modo_destino = 'ofertas'
            obj.enlace = ''
        elif form.cleaned_data.get('opt_producto'):
            obj.modo_destino = 'producto'
            obj.enlace = ''
        elif form.cleaned_data.get('opt_link'):
            obj.modo_destino = 'enlace'
        super().save_model(request, obj, form, change)

    class Media:
        js = ('admin/js/banner_modes.js',)
        css = {'all': ('admin/css/banner_modes.css',)}

# --- Admin de Páginas Informativas ---
@admin.register(Pagina)
class PaginaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'slug', 'publicada')
    list_filter = ('publicada',)
    search_fields = ('titulo', 'contenido')
    prepopulated_fields = {'slug': ('titulo',)}

# --- Admin para las Claves de API de Gemini ---
@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'activa', 'notas', 'fecha_creacion')
    list_filter = ('activa',)
    search_fields = ('notas',)
    list_editable = ('activa',)
    fields = ('key', 'activa', 'notas')
    
# --- Admin para Direcciones ---
@admin.register(Direccion)
class DireccionAdmin(admin.ModelAdmin):
    list_display = ('user', 'alias', 'destinatario', 'ciudad', 'predeterminada')
    list_filter = ('ciudad', 'predeterminada')
    search_fields = ('user__username', 'alias', 'destinatario')

# --- Admin para la Ruleta de la Suerte ---
class PremioRuletaInline(admin.TabularInline):
    model = PremioRuleta
    extra = 1
    fields = ('nombre', 'activo')

@admin.register(ConfiguracionRuleta)
class ConfiguracionRuletaAdmin(SingletonModelAdmin):
    inlines = [PremioRuletaInline]
    list_display = ('__str__', 'activa', 'titulo', 'fecha_inicio', 'fecha_fin')
    fieldsets = (
        (None, {
            'fields': ('activa', 'titulo')
        }),
        ('Ventana de tiempo (opcional)', {
            'classes': ('collapse',),
            'fields': ('fecha_inicio', 'fecha_fin')
        }),
        ('Sonidos (Opcional)', {
            'classes': ('collapse',),
            'fields': ('sonido_giro', 'sonido_premio')
        }),
    )

@admin.register(Cupon)
class CuponAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'usuario', 'premio', 'fecha_creacion', 'fecha_expiracion', 'usado')
    list_filter = ('usado', 'fecha_creacion')
    search_fields = ('codigo', 'usuario__username')
    list_editable = ('usado',)
    readonly_fields = ('codigo', 'usuario', 'premio', 'fecha_creacion', 'fecha_expiracion')
    list_per_page = 20

@admin.register(TiradaRuleta)
class TiradaRuletaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'ultima_tirada')
    search_fields = ('usuario__username',)
    readonly_fields = ('usuario', 'ultima_tirada')

# === INICIO DE LA MEJORA: Registro del Centro de Control del Chatbot ===
@admin.register(ConfiguracionChatbot)
class ConfiguracionChatbotAdmin(SingletonModelAdmin):
    list_display = ('__str__', 'activo')
    
    fieldsets = (
        (None, {
            'fields': ('activo',)
        }),
        ('Personalidad y Reglas de Fanty (Cerebro del Bot)', {
            'classes': ('collapse',),
            'fields': ('instrucciones_sistema',),
            'description': """
                <p><strong>ADVERTENCIA:</strong> Estás editando el "cerebro" de Fanty.</p>
                <ul>
                    <li>El texto aquí controlará cómo responde, su personalidad y sus reglas.</li>
                    <li>La variable <code>{user_name}</code> se reemplazará por el nombre del cliente.</li>
                    <li>Para mostrar botones, usa <code>[BOTONES: Opción 1; Opción 2]</code> (separados por punto y coma).</li>
                </ul>
            """
        }),
    )
# === FIN DE LA MEJORA ===
