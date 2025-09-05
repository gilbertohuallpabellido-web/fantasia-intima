from django.db import models
from django.db.models import Sum
import os
from django.conf import settings
import uuid
from solo.models import SingletonModel
from django.utils.text import slugify
from mptt.models import MPTTModel, TreeForeignKey
from django.utils import timezone
from datetime import timedelta
import random
import string
from django.db.models.signals import post_save, pre_delete, pre_save, post_delete
from django.dispatch import receiver
import unicodedata
import re
# === INICIO DE LA MEJORA: Importamos la herramienta de Cloudinary ===
from cloudinary.models import CloudinaryField
import cloudinary.api
import cloudinary.uploader
# === FIN DE LA MEJORA ===
# ... (El resto de tus modelos como Categoria, Producto, etc., se mantienen igual)
class Categoria(MPTTModel):
    nombre = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True, help_text="Se genera automáticamente.")
    
    parent = TreeForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='children',
        db_index=True,
        verbose_name='Categoría Padre'
    )
    
    categorias_relacionadas = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        verbose_name="Categorías Relacionadas (para cross-selling)",
        help_text="Selecciona otras categorías para mostrar sus productos como relacionados."
    )

    class MPTTMeta:
        order_insertion_by = ['nombre']

    class Meta:
        verbose_name = "Categoría de Producto"
        verbose_name_plural = "Categorías de Productos"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    categoria = TreeForeignKey(
        'Categoria',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='productos',
        verbose_name="Categoría"
    )
    
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2, help_text="Precio original del producto.")
    
    precio_oferta = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        help_text="Opcional: Si este precio está fijado, se mostrará como una oferta (con el precio original tachado)."
    )
    es_oferta = models.BooleanField(default=False, help_text="Márcalo para incluir este producto en el filtro 'Solo ofertas' aunque no tenga precio_oferta menor. Si hay precio_oferta menor que precio, se mostrará el % de descuento.")
    imagen_principal = models.ImageField(upload_to='productos/', blank=True, null=True)
    es_nueva_coleccion = models.BooleanField(default=False, verbose_name="¿Es de la Nueva Colección?")
    # Campos normalizados para búsqueda (sin tildes y en minúsculas)
    nombre_norm = models.CharField(max_length=255, default='', db_index=True)
    descripcion_norm = models.TextField(blank=True, default='')
    # Campo eliminado: en_grupo_banner (ya no se usa grupo de productos del banner)
    
    @property
    def categoria_padre(self):
        if self.categoria:
            return self.categoria.parent
        return None

    @property
    def total_stock(self):
        return sum(variant.stock for variant in self.variantes.all())

    @property
    def descuento_porcentaje(self):
        if self.precio_oferta and self.precio and self.precio > 0 and self.precio > self.precio_oferta:
            descuento = ((self.precio - self.precio_oferta) / self.precio) * 100
            return int(round(descuento))
        return 0

    def __str__(self):
        return self.nombre

    @staticmethod
    def _normalize_text(text):
        if not text:
            return ''
        # Quitar tildes/diacríticos y pasar a minúsculas
        norm = unicodedata.normalize('NFKD', str(text))
        norm = norm.encode('ascii', 'ignore').decode('ascii').lower()
        # Colapsar espacios
        norm = re.sub(r"\s+", " ", norm).strip()
        return norm

    def save(self, *args, **kwargs):
        # Actualizar campos normalizados antes de guardar
        self.nombre_norm = self._normalize_text(self.nombre)
        self.descripcion_norm = self._normalize_text(self.descripcion)
        super().save(*args, **kwargs)


class ColorVariante(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='variantes')
    
    codigo = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        unique=True,
        help_text='Código único (SKU) para esta variante específica (ej: DIS-COL-001-ROJO).'
    )
    
    color = models.CharField(max_length=7, default='#FFFFFF', help_text='Haz clic para seleccionar un color exacto.')
    
        # === INICIO DE LA MEJORA: Campo para la "Muestra de Tela" ===
    imagen_textura = models.ImageField(
        upload_to='productos/texturas/', 
        blank=True, 
        null=True,
        help_text="Opcional: Sube aquí una imagen pequeña (ej: 50x50px) del estampado o textura si el color es complejo."
    )
    # === FIN DE LA MEJORA ===
    
    imagen = models.ImageField(upload_to='productos/variantes/')
    stock = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.producto.nombre} - {self.codigo or self.color}"

    @property
    def stock_disponible(self):
        """Stock disponible efectivo (stock físico menos reservas activas)."""
        reserved = self.reservas.filter(expires_at__gt=timezone.now()).aggregate(total=Sum('quantity'))['total'] or 0
        return max(self.stock - reserved, 0)


class PedidoWhatsApp(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo_pedido = models.CharField(max_length=20, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    nombre_cliente = models.CharField(max_length=255, blank=True, null=True)
    dni_cliente = models.CharField(max_length=20, blank=True, null=True)
    email_cliente = models.EmailField(max_length=255, blank=True, null=True)
    celular_cliente = models.CharField(max_length=20, blank=True, null=True)
    ciudad_envio = models.CharField(max_length=100, blank=True, null=True)
    direccion_envio = models.CharField(max_length=255, blank=True, null=True)

    @property
    def subtotal(self):
        return sum(detalle.subtotal for detalle in self.detalles.all())

    @property
    def costo_envio(self):
        if self.total >= self.subtotal:
            return self.total - self.subtotal
        return 0

    def __str__(self):
        return self.codigo_pedido


class DetallePedidoWhatsApp(models.Model):
    pedido = models.ForeignKey(PedidoWhatsApp, related_name='detalles', on_delete=models.CASCADE)
    producto_nombre = models.CharField(max_length=200)
    variante_color = models.CharField(max_length=100)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    imagen_url = models.CharField(max_length=255)

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f"{self.producto_nombre} ({self.cantidad})"


class ReservaStock(models.Model):
    """Reserva de stock por sesión para bloquear unidades por 24h."""
    variante = models.ForeignKey(ColorVariante, on_delete=models.CASCADE, related_name='reservas')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='reservas_stock')
    session_key = models.CharField(max_length=40, db_index=True)
    quantity = models.PositiveIntegerField(default=0)
    reserved_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"Reserva {self.quantity}x {self.variante} (sesión {self.session_key})"


class Carrito(models.Model):
    """Carrito persistente por usuario (sincroniza dispositivos)."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='carrito')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Carrito de {self.user}"

    @property
    def total_items(self):
        return sum(i.quantity for i in self.items.all())


class CarritoItem(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items')
    variante = models.ForeignKey(ColorVariante, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image_url = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        unique_together = ('carrito', 'variante')

    @property
    def subtotal(self):
        return self.quantity * self.price


class ConfiguracionSitio(SingletonModel):
    nombre_tienda = models.CharField(max_length=100, default="Fantasía Íntima")
    logo = models.ImageField(upload_to='configuracion/', blank=True, null=True)
    whatsapp_link = models.URLField(default="https://wa.me/51932187068")
    facebook_link = models.URLField(default="https://web.facebook.com/fantasiaintimaa/")
    instagram_link = models.URLField(default="https://www.instagram.com/fantasia_intima_lenceria")
    tiktok_link = models.URLField(default="https://www.tiktok.com/@fantasa.ntima")
    numero_yape_plin = models.CharField(max_length=15, default="987 654 321")

    # === INICIO DE LA MEJORA: Imágenes de pago dinámicas ===
    imagen_yape = models.ImageField(upload_to='configuracion/pagos/', blank=True, null=True, help_text="Logo de Yape que se mostrará en el checkout.")
    imagen_plin = models.ImageField(upload_to='configuracion/pagos/', blank=True, null=True, help_text="Logo de Plin que se mostrará en el checkout.")
    # === FIN DE LA MEJORA ===

    # Paleta de Colores
    color_primario = models.CharField(max_length=7, default='#f9a8d4', help_text="Color principal (rosa claro)")
    # ... (el resto de los campos de color y fuente se mantienen igual)
    color_secundario = models.CharField(max_length=7, default='#f472b6', help_text="Color secundario (rosa medio)")
    color_acento = models.CharField(max_length=7, default='#ec4899', help_text="Color de acento para botones (rosa fuerte)")
    color_marron = models.CharField(max_length=7, default='#5C2C0C', help_text="Color marrón para títulos")
    color_texto = models.CharField(max_length=7, default='#4b4244', help_text="Color del texto general")
    fuente_principal_url = models.URLField(max_length=500, default="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap")
    fuente_principal_nombre = models.CharField(max_length=100, default="'Inter', sans-serif")
    fuente_marca_url = models.URLField(max_length=500, default="https://fonts.googleapis.com/css2?family=Parisienne&display=swap")
    fuente_marca_nombre = models.CharField(max_length=100, default="'Parisienne', cursive")
    resetear_estilos = models.BooleanField(default=False, help_text="MARCA ESTA CASILLA Y GUARDA para restaurar todos los colores y fuentes a sus valores originales.")

    def __str__(self):
        return "Configuración del Sitio"

    class Meta:
        verbose_name = "Configuración del Sitio"

    def save(self, *args, **kwargs):
        if self.resetear_estilos:
            for field in self._meta.fields:
                if field.name.startswith('color_') or field.name.startswith('fuente_'):
                    setattr(self, field.name, field.get_default())
            self.resetear_estilos = False
        super().save(*args, **kwargs)


class Banner(models.Model):
    # Simplificado: se elimina productos_destacados (ya no se seleccionan varios productos)
    titulo = models.CharField(max_length=100, help_text="Ej: ¡Ofertas de Fin de Semana!")
    subtitulo = models.CharField(max_length=200, blank=True, help_text="Ej: Hasta 50% en productos seleccionados")
    imagen = models.ImageField(upload_to='banners/', help_text="Imagen de fondo (1200x400px recomendado)")
    
    enlace = models.URLField(blank=True, help_text="URL a la que dirigirá el botón si el modo es 'Enlace'.")
    texto_boton = models.CharField(max_length=50, default="Ver ahora")
    activo = models.BooleanField(default=False, help_text="Marca esta casilla para que este banner se muestre en la página principal.")
    # Opcional: activar banner por rango de fechas (si se usan, el banner solo aparece dentro del rango)
    fecha_inicio = models.DateTimeField(blank=True, null=True, help_text="Opcional: fecha/hora de inicio para mostrar el banner")
    fecha_fin = models.DateTimeField(blank=True, null=True, help_text="Opcional: fecha/hora de fin para mostrar el banner")
    MODO_OPCIONES = [
        ('nueva', 'Nueva Colección'),
        ('ofertas', 'Productos en Oferta'),
        ('producto', 'Producto Individual'),
        ('enlace', 'Enlace Personalizado'),
    ]
    modo_destino = models.CharField(max_length=20, choices=MODO_OPCIONES, default='nueva', help_text="Qué mostrará el botón del banner.")
    productos_destacados = models.ManyToManyField(
        'Producto',
        blank=True,
        related_name='banners_productos',
        help_text="Selecciona uno o varios productos para este banner si el modo es 'Producto Individual'. Si seleccionas solo uno se irá directo al detalle; si son varios, se listarán filtrados en el catálogo."
    )
    # Campos antiguos (deprecated) mantenidos para compatibilidad
    usar_nueva_coleccion = models.BooleanField(default=False, editable=False)
    usar_descuentos = models.BooleanField(default=False, editable=False)

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        if self.activo:
            Banner.objects.filter(activo=True).exclude(pk=self.pk).update(activo=False)
        super(Banner, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "Banner Promocional"
        verbose_name_plural = "Banners Promocionales"

@receiver(post_save, sender=Banner)
def banner_post_save(sender, instance, **kwargs):
    # Solo aseguramos exclusividad de banner activo; no más sincronización de grupos
    pass

class Pagina(models.Model):
# ... (código existente sin cambios)
    titulo = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, help_text="La URL de la página (ej: 'nosotros', 'politicas-de-envio')")
    contenido = models.TextField(help_text="Escribe aquí todo el contenido de la página. Puedes usar HTML si lo necesitas.")
    publicada = models.BooleanField(default=True, help_text="Desmarca esta casilla para ocultar la página temporalmente.")

    def __str__(self):
        return self.titulo

    class Meta:
        verbose_name = "Página Informativa"
        verbose_name_plural = "Páginas Informativas"
        ordering = ['titulo']

class Direccion(models.Model):
# ... (código existente sin cambios)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='direcciones')
    alias = models.CharField(max_length=50, help_text="Ej: Casa, Oficina, Casa de mi tía")
    destinatario = models.CharField(max_length=100, verbose_name="Nombre del destinatario")
    direccion = models.CharField(max_length=255, verbose_name="Dirección (Calle, número, etc.)")
    referencia = models.CharField(max_length=255, blank=True, verbose_name="Referencia (Opcional)")
    ciudad = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20)
    predeterminada = models.BooleanField(default=False, verbose_name="¿Es dirección predeterminada?")

    class Meta:
        verbose_name = "Dirección"
        verbose_name_plural = "Direcciones"
        unique_together = ('user', 'alias')

    def __str__(self):
        return f"{self.alias} ({self.user.username})"

    def save(self, *args, **kwargs):
        if self.predeterminada:
            Direccion.objects.filter(user=self.user, predeterminada=True).update(predeterminada=False)
        super().save(*args, **kwargs)

class ApiKey(models.Model):
# ... (código existente sin cambios)
    key = models.CharField(max_length=255, unique=True, verbose_name="Clave de API")
    activa = models.BooleanField(default=True, help_text="Desmarca esta casilla para desactivar la clave temporalmente.")
    notas = models.TextField(blank=True, help_text="Notas internas (ej: 'Clave de cuenta personal', 'Clave de prueba').")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Clave de API de Gemini"
        verbose_name_plural = "Claves de API de Gemini"

    def __str__(self):
        return f"{self.key[:8]}...{self.key[-4:]}"

class ConfiguracionRuleta(SingletonModel):
# ... (código existente sin cambios)
    activa = models.BooleanField(default=False, help_text="Marca esta casilla para mostrar la ruleta en la web.")
    titulo = models.CharField(max_length=100, default="¡Gira y Gana!", help_text="El título que aparecerá en el pop-up de la ruleta (ej: 'Especial de Halloween').")
    # Ventana de tiempo (opcional): si se establecen, la ruleta solo estará activa entre estas fechas
    fecha_inicio = models.DateTimeField(null=True, blank=True, help_text="Inicio de la promoción de la ruleta (opcional)")
    fecha_fin = models.DateTimeField(null=True, blank=True, help_text="Fin de la promoción de la ruleta (opcional)")
     # === INICIO DE LA MEJORA: Campos de archivo inteligentes para Cloudinary ===
    sonido_giro = CloudinaryField(
        'sonido_giro',
        resource_type='raw', # Le decimos que es un archivo de audio/raw
        folder='sonidos_ruleta',
        blank=True,
        null=True,
        help_text="Sonido (MP3) que se reproduce mientras la ruleta gira."
    )
    sonido_premio = CloudinaryField(
        'sonido_premio',
        resource_type='raw', # Le decimos que es un archivo de audio/raw
        folder='sonidos_ruleta',
        blank=True,
        null=True,
        help_text="Sonido (MP3) que se reproduce al ganar un premio."
    )
    # === FIN DE LA MEJORA ===
    
    class Meta:
        verbose_name = "Configuración de la Ruleta"

    def __str__(self):
        return "Configuración de la Ruleta"

    def is_active_now(self):
        """Devuelve True si la ruleta está marcada como activa y además la hora actual
        está dentro de [fecha_inicio, fecha_fin) cuando dichas fechas están definidas."""
        if not self.activa:
            return False
        now = timezone.now()
        if self.fecha_inicio and now < self.fecha_inicio:
            return False
        if self.fecha_fin and now >= self.fecha_fin:
            return False
        return True

class PremioRuleta(models.Model):
# ... (código existente sin cambios)
    configuracion = models.ForeignKey(ConfiguracionRuleta, on_delete=models.CASCADE, related_name='premios')
    nombre = models.CharField(max_length=50, help_text="Texto que aparecerá en la ruleta (ej: '10% OFF', 'Envío Gratis'). Mantenlo corto.")
    activo = models.BooleanField(default=True, help_text="Desmarca para quitar este premio de la ruleta.")

    class Meta:
        verbose_name = "Premio de la Ruleta"
        verbose_name_plural = "Premios de la Ruleta"

    def __str__(self):
        return self.nombre

def generar_codigo_cupon():
    return f"FANTY-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"

class Cupon(models.Model):
# ... (código existente sin cambios)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cupones')
    premio = models.ForeignKey(PremioRuleta, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=15, default=generar_codigo_cupon, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateTimeField()
    usado = models.BooleanField(default=False, help_text="Marca esta casilla cuando el cliente haya canjeado el cupón por WhatsApp.")

    class Meta:
        verbose_name = "Cupón Generado"
        verbose_name_plural = "Cupones Generados"

    def save(self, *args, **kwargs):
        if not self.id:
            self.fecha_expiracion = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Cupón {self.codigo} para {self.usuario.username}"

class TiradaRuleta(models.Model):
# ... (código existente sin cambios)
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True)
    ultima_tirada = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0, help_text="Número total de intentos realizados (límite 3).")

    class Meta:
        verbose_name = "Tirada de Ruleta"
        verbose_name_plural = "Tiradas de Ruleta"

    def puede_jugar(self):
        return self.attempts < 3

    def __str__(self):
        return f"Última tirada de {self.usuario.username}: {self.ultima_tirada.strftime('%Y-%m-%d %H:%M')}"

class ConfiguracionChatbot(SingletonModel):
# ... (código existente sin cambios)
    """
    Un modelo Singleton para almacenar la configuración global del chatbot.
    """
    activo = models.BooleanField(
        default=False, 
        help_text="Marca esta casilla para activar el chatbot 'Fanty' en todo el sitio web."
    )
    instrucciones_sistema = models.TextField(
        help_text="El 'cerebro' de Fanty. Define su personalidad, reglas y comportamiento. Edita con cuidado.",
        default="""
# ROL Y OBJETIVO
Eres 'Fanty', una asesora de ventas estrella de 'Fantasía Íntima'. Eres amable, coqueta, y una vendedora inteligente que NUNCA pierde el hilo de la conversación y JAMÁS inventa información. Tu objetivo es crear una experiencia de compra agradable y seductora.

# REGLAS DE CONVERSACIÓN (OBLIGATORIAS E INQUEBRANTABLES)
1.  **VERACIDAD ABSOLUTA:** PROHIBIDO INVENTAR PRODUCTOS. Toda tu información DEBE provenir EXCLUSIVAMENTE del `catalogo_relevante`.
2.  **MEMORIA CONTEXTUAL:** CERO SALUDOS REPETIDOS. NUNCA PIERDAS EL HILO. NO REPITAS PREGUNTAS YA RESUELTAS.
3.  **FLUJO DE VENTA IDEAL (SECUENCIAL):**
    * **PASO 1 - PRESENTAR:** Ofrece un producto (nombre, SKU, precio) y pregunta si quieren saber más.
    * **PASO 2 - DETALLAR:** Si el cliente dice "sí", PRIMERO describe el producto de forma seductora.
    * **PASO 3 - CIERRE SUAVE:** DESPUÉS de describir, pregunta si se animan a llevarlo.
    * **PASO 4 - FACILITAR PAGO:** Si confirman, el siguiente paso OBLIGATORIO es facilitar la compra, indicando los métodos de pago.
    * **REGLA ANTI-BUCLES:** Es un error CRÍTICO repetir un paso. Si ya describiste el producto, avanza.
4.  **TONO Y PERSONALIZACIÓN:** Usa el nombre del cliente `{user_name}` SÓLO EN EL PRIMER SALUDO. Si es 'admin' o 'Desconocido', usa un saludo neutral como "¡Bienvenid@!".
5.  **COMPORTAMIENTO PROACTIVO:** Si la pregunta es general ("hola"), recomienda un producto popular. Maneja objeciones de precio con promociones y ofrece accesorios (upsell) solo si existen en el catálogo. Al final, invita a seguir las redes sociales.

# USO DE BOTONES
Para guiar al cliente, puedes ofrecer respuestas predefinidas. Usa el formato `[BOTONES: Opción 1, Opción 2, Opción 3]`. El sistema lo convertirá en botones clickeables. Úsalo para preguntas de opción múltiple.
Ejemplo: "Para darte la mejor recomendación, ¿qué buscas? [BOTONES: Algo atrevido, Algo elegante, Algo divertido]"
"""
    )

    def __str__(self):
        return "Configuración del Chatbot"

    class Meta:
        verbose_name = "Configuración del Chatbot"

class Profile(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    avatar = CloudinaryField('avatar', folder='media/foto_de_perfil', blank=True, null=True)
    nombre = models.CharField(max_length=100, blank=True)
    apellido = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.user.username

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Crea un perfil para el usuario si es nuevo, o simplemente lo guarda si ya existe.
    """
    # Evitar acceder a instance.profile si no existe aún (caso usuarios antiguos)
    # En login, Django actualiza last_login y dispara post_save: aquí garantizamos el Profile.
    Profile.objects.get_or_create(user=instance)

# === LIMPIEZA AUTOMÁTICA DE ARCHIVOS EN CLOUDINARY ===
def _destroy_cloudinary_resource(field_value, resource_type=None):
    """Intenta eliminar el recurso en Cloudinary usando su public_id.
    No lanza excepción si falla (modo best-effort).
    """
    try:
        if not field_value:
            return
        public_id = getattr(field_value, 'public_id', None)
        if not public_id:
            return

        def debug_lookup(public_id):
            if not settings.DEBUG:
                return
            for rt in ['raw', 'video', 'image']:
                for typ in ['upload', 'authenticated', 'private']:
                    try:
                        info = cloudinary.api.resource(public_id, resource_type=rt, type=typ)
                        print(f"[CLOUDINARY LOOKUP HIT] pid={public_id} rt={rt} type={typ} bytes={info.get('bytes')} format={info.get('format')}")
                    except Exception as e:
                        # Silencio los misses para no saturar
                        pass

        debug_lookup(public_id)

        def attempt_uploader(rt=None, typ=None):
            try:
                kwargs = {'invalidate': True}
                if rt:
                    kwargs['resource_type'] = rt
                if typ:
                    kwargs['type'] = typ
                if settings.DEBUG:
                    print(f"[CLOUDINARY DESTROY] public_id={public_id} rt={rt} type={typ}")
                res = cloudinary.uploader.destroy(public_id, **kwargs)
                if settings.DEBUG:
                    print(f"[CLOUDINARY DESTROY RES] => {res}")
                return res
            except Exception as e:
                if settings.DEBUG:
                    print(f"[CLOUDINARY DESTROY ERR] rt={rt} type={typ} err={e}")
                return None

        def attempt_api(rt, typ):
            try:
                if settings.DEBUG:
                    print(f"[CLOUDINARY API DELETE] public_id={public_id} rt={rt} type={typ}")
                res = cloudinary.api.delete_resources([public_id], resource_type=rt, type=typ)
                if settings.DEBUG:
                    print(f"[CLOUDINARY API DELETE RES] => {res}")
                return res
            except Exception as e:
                if settings.DEBUG:
                    print(f"[CLOUDINARY API DELETE ERR] rt={rt} type={typ} err={e}")
                return None

        tried_ok = False
        rts = []
        if resource_type:
            rts.append(resource_type)
        for rt in ['video', 'raw', 'image', 'auto']:
            if rt not in rts:
                rts.append(rt)
        types = [None, 'upload', 'authenticated', 'private']

        # Candidatos de public_id: base y, para raw, intentar con extensión
        pid_candidates = [public_id]
        url_str = None
        try:
            url_str = str(field_value)
        except Exception:
            url_str = None
        ext_candidates = []
        if url_str and '/upload/' in url_str:
            tail = url_str.split('/upload/', 1)[-1]
            last = tail.split('?')[0].split('#')[0].split('/')[-1]
            if '.' in last:
                ext = last.rsplit('.', 1)[-1].lower()
                if ext and ext not in ('', 'jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'webm', 'mov'):
                    ext_candidates.append(ext)
        # Audio comunes
        for ext in ['mp3', 'wav', 'ogg']:
            if ext not in ext_candidates:
                ext_candidates.append(ext)
        for ext in ext_candidates:
            pid_with_ext = f"{public_id}.{ext}"
            if pid_with_ext not in pid_candidates:
                pid_candidates.append(pid_with_ext)

        for pid in pid_candidates:
            if settings.DEBUG and pid != public_id:
                print(f"[CLOUDINARY PID VARIANT] trying {pid}")
            for rt in rts:
                for typ in types:
                    # parche: sobrescribir public_id localmente
                    saved_pid = public_id
                    public_id = pid
                    res = attempt_uploader(rt, typ)
                    public_id = saved_pid
                    if isinstance(res, dict) and res.get('result') == 'ok':
                        tried_ok = True
                        break
                if tried_ok:
                    break
            if tried_ok:
                break

        if not tried_ok:
            for pid in pid_candidates:
                for rt in ['video', 'raw', 'image', 'auto']:
                    for typ in ['upload', 'authenticated', 'private']:
                        try:
                            if settings.DEBUG:
                                print(f"[CLOUDINARY API DELETE] public_id={pid} rt={rt} type={typ}")
                            res = cloudinary.api.delete_resources([pid], resource_type=rt, type=typ)
                            if settings.DEBUG:
                                print(f"[CLOUDINARY API DELETE RES] => {res}")
                        except Exception as e:
                            if settings.DEBUG:
                                print(f"[CLOUDINARY API DELETE ERR] rt={rt} type={typ} err={e}")
    except Exception as e:
        if settings.DEBUG:
            print(f"[CLOUDINARY DESTROY FATAL] err={e}")

def _delete_filefield_file(file_field_file):
    """Elimina el archivo de un FileField/ImageField usando su storage backend."""
    try:
        if not file_field_file:
            return
        name = getattr(file_field_file, 'name', None)
        storage = getattr(file_field_file, 'storage', None)
        if name and storage:
            if settings.DEBUG:
                print(f"[STORAGE DELETE] name={name}")
            storage.delete(name)
            # Mejor esfuerzo: también borrar directamente en Cloudinary por public_id
            public_id = name.replace('\\', '/').lstrip('/')
            if public_id.startswith('media/'):
                public_id = public_id[len('media/'):]
            public_id, _ext = os.path.splitext(public_id)
            try:
                if settings.DEBUG:
                    print(f"[CLOUDINARY DESTROY FROM NAME] public_id={public_id}")
                cloudinary.uploader.destroy(public_id, resource_type='image', invalidate=True)
            except Exception:
                pass
    except Exception:
        pass


@receiver(pre_delete, sender=Profile)
def _profile_avatar_delete(sender, instance, **kwargs):
    # Avatar es una imagen
    _destroy_cloudinary_resource(instance.avatar, resource_type='image')


# Redundancia por si algún backend no dispara pre_delete
@receiver(post_delete, sender=Profile)
def _profile_avatar_post_delete(sender, instance, **kwargs):
    # Redundancia por si algún backend no dispara pre_delete
    _destroy_cloudinary_resource(instance.avatar, resource_type='image')


@receiver(pre_save, sender=Profile)
def _profile_avatar_replace(sender, instance, **kwargs):
    # Si cambia el avatar, borramos el anterior
    if not instance.pk:
        return
    try:
        old = Profile.objects.get(pk=instance.pk)
    except Profile.DoesNotExist:
        return
    if getattr(old, 'avatar', None):
        old_pid = getattr(old.avatar, 'public_id', None)
        new_pid = getattr(getattr(instance, 'avatar', None), 'public_id', None)
        if old_pid and old_pid != new_pid:
            _destroy_cloudinary_resource(old.avatar, resource_type='image')


@receiver(pre_delete, sender=ConfiguracionRuleta)
def _ruleta_sounds_delete(sender, instance, **kwargs):
    # Sonidos son recursos tipo 'raw'
    if settings.DEBUG:
        print("[RULETA pre_delete] Eliminando sonidos si existen")
    _destroy_cloudinary_resource(instance.sonido_giro, resource_type='raw')
    _destroy_cloudinary_resource(instance.sonido_premio, resource_type='raw')


@receiver(post_delete, sender=ConfiguracionRuleta)
def _ruleta_sounds_post_delete(sender, instance, **kwargs):
    _destroy_cloudinary_resource(instance.sonido_giro, resource_type='raw')
    _destroy_cloudinary_resource(instance.sonido_premio, resource_type='raw')


@receiver(pre_save, sender=ConfiguracionRuleta)
def _ruleta_sounds_replace(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = ConfiguracionRuleta.objects.get(pk=instance.pk)
    except ConfiguracionRuleta.DoesNotExist:
        return
    if getattr(old, 'sonido_giro', None):
        old_pid = getattr(old.sonido_giro, 'public_id', None)
        new_pid = getattr(getattr(instance, 'sonido_giro', None), 'public_id', None)
        if settings.DEBUG:
            print(f"[RULETA pre_save] sonido_giro old={old_pid} new={new_pid}")
        if old_pid and old_pid != new_pid:
            _destroy_cloudinary_resource(old.sonido_giro, resource_type='raw')
    if getattr(old, 'sonido_premio', None):
        old_pid = getattr(old.sonido_premio, 'public_id', None)
        new_pid = getattr(getattr(instance, 'sonido_premio', None), 'public_id', None)
        if settings.DEBUG:
            print(f"[RULETA pre_save] sonido_premio old={old_pid} new={new_pid}")
        if old_pid and old_pid != new_pid:
            _destroy_cloudinary_resource(old.sonido_premio, resource_type='raw')


# === LIMPIEZA PARA ImageField (CloudinaryStorage) ===
@receiver(pre_delete, sender=Banner)
def _banner_image_delete(sender, instance, **kwargs):
    _delete_filefield_file(instance.imagen)


@receiver(pre_save, sender=Banner)
def _banner_image_replace(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = Banner.objects.get(pk=instance.pk)
    except Banner.DoesNotExist:
        return
    if getattr(old, 'imagen', None) and old.imagen and old.imagen.name != getattr(instance.imagen, 'name', None):
        _delete_filefield_file(old.imagen)


@receiver(pre_delete, sender=Producto)
def _producto_image_delete(sender, instance, **kwargs):
    _delete_filefield_file(instance.imagen_principal)


@receiver(pre_save, sender=Producto)
def _producto_image_replace(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = Producto.objects.get(pk=instance.pk)
    except Producto.DoesNotExist:
        return
    if getattr(old, 'imagen_principal', None) and old.imagen_principal and old.imagen_principal.name != getattr(instance.imagen_principal, 'name', None):
        _delete_filefield_file(old.imagen_principal)


@receiver(pre_delete, sender=ColorVariante)
def _colorvariante_images_delete(sender, instance, **kwargs):
    _delete_filefield_file(instance.imagen)
    _delete_filefield_file(instance.imagen_textura)


@receiver(pre_save, sender=ColorVariante)
def _colorvariante_images_replace(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = ColorVariante.objects.get(pk=instance.pk)
    except ColorVariante.DoesNotExist:
        return
    if getattr(old, 'imagen', None) and old.imagen and old.imagen.name != getattr(instance.imagen, 'name', None):
        _delete_filefield_file(old.imagen)
    if getattr(old, 'imagen_textura', None) and old.imagen_textura and old.imagen_textura.name != getattr(instance.imagen_textura, 'name', None):
        _delete_filefield_file(old.imagen_textura)


@receiver(pre_delete, sender=ConfiguracionSitio)
def _config_sitio_images_delete(sender, instance, **kwargs):
    _delete_filefield_file(instance.logo)
    _delete_filefield_file(instance.imagen_yape)
    _delete_filefield_file(instance.imagen_plin)


@receiver(pre_save, sender=ConfiguracionSitio)
def _config_sitio_images_replace(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = ConfiguracionSitio.objects.get(pk=instance.pk)
    except ConfiguracionSitio.DoesNotExist:
        return
    if getattr(old, 'logo', None) and old.logo and old.logo.name != getattr(instance.logo, 'name', None):
        _delete_filefield_file(old.logo)
    if getattr(old, 'imagen_yape', None) and old.imagen_yape and old.imagen_yape.name != getattr(instance.imagen_yape, 'name', None):
        _delete_filefield_file(old.imagen_yape)
    if getattr(old, 'imagen_plin', None) and old.imagen_plin and old.imagen_plin.name != getattr(instance.imagen_plin, 'name', None):
        _delete_filefield_file(old.imagen_plin)