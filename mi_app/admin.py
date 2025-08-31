from django.contrib import admin
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
    fields = ('codigo', 'color', 'imagen', 'stock') 

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
        return cleaned_data

    class Media:
        js = ('admin/js/dynamic_subcategories.js',)

# --- Admin de Productos ---
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    form = ProductoAdminForm
    list_display = ('nombre', 'get_categoria_padre', 'categoria', 'precio', 'precio_oferta', 'es_nueva_coleccion')
    fieldsets = (
        (None, {
            'fields': ('nombre', 'categoria_padre', 'categoria', 'descripcion', 'imagen_principal')
        }),
        ('Precios y Ofertas', {
            'fields': ('precio', 'precio_oferta')
        }),
        ('Opciones Adicionales', {
            'fields': ('es_nueva_coleccion',)
        }),
    )
    list_filter = ('categoria__parent', 'categoria', 'es_nueva_coleccion')
    search_fields = ('nombre', 'descripcion', 'categoria__nombre')
    list_editable = ('precio', 'precio_oferta', 'es_nueva_coleccion')
    inlines = [ColorVarianteInline]

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
    list_display = ('titulo', 'activo')
    list_filter = ('activo',)
    list_editable = ('activo',)
    filter_horizontal = ('productos_destacados',)
    fieldsets = (
        (None, {'fields': ('titulo', 'subtitulo', 'imagen', 'activo')}),
        ('Acción del Banner', {'fields': ('texto_boton', 'enlace')}),
        ('Colección Destacada (Opcional)', {'fields': ('productos_destacados',)}),
    )

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
    list_display = ('__str__', 'activa', 'titulo')
    fieldsets = (
        (None, {
            'fields': ('activa', 'titulo')
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
                    <li>Para mostrar botones, añade <code>[BOTONES: Opción 1, Opción 2]</code> al final de una pregunta.</li>
                </ul>
            """
        }),
    )
# === FIN DE LA MEJORA ===