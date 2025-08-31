from django.db import models
from django.conf import settings
import uuid
from solo.models import SingletonModel
from django.utils.text import slugify
from mptt.models import MPTTModel, TreeForeignKey
from django.utils import timezone
from datetime import timedelta
import random
import string

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
    imagen_principal = models.ImageField(upload_to='productos/', blank=True, null=True)
    es_nueva_coleccion = models.BooleanField(default=False, verbose_name="¿Es de la Nueva Colección?")
    
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
    imagen = models.ImageField(upload_to='productos/variantes/')
    stock = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.producto.nombre} - {self.codigo or self.color}"


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


class ConfiguracionSitio(SingletonModel):
    nombre_tienda = models.CharField(max_length=100, default="Fantasía Íntima")
    logo = models.ImageField(upload_to='configuracion/', blank=True, null=True)
    whatsapp_link = models.URLField(default="https://wa.me/51932187068")
    facebook_link = models.URLField(default="https://web.facebook.com/fantasiaintimaa/")
    instagram_link = models.URLField(default="https://www.instagram.com/fantasia_intima_lenceria")
    tiktok_link = models.URLField(default="https://www.tiktok.com/@fantasa.ntima")
    numero_yape_plin = models.CharField(max_length=15, default="987 654 321")

    # Paleta de Colores
    color_primario = models.CharField(max_length=7, default='#f9a8d4', help_text="Color principal (rosa claro)")
    color_secundario = models.CharField(max_length=7, default='#f472b6', help_text="Color secundario (rosa medio)")
    color_acento = models.CharField(max_length=7, default='#ec4899', help_text="Color de acento para botones (rosa fuerte)")
    color_marron = models.CharField(max_length=7, default='#5C2C0C', help_text="Color marrón para títulos")
    color_texto = models.CharField(max_length=7, default='#4b4244', help_text="Color del texto general")

    # Tipografía (Fuentes de Google Fonts)
    fuente_principal_url = models.URLField(max_length=500, default="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap")
    fuente_principal_nombre = models.CharField(max_length=100, default="'Inter', sans-serif")
    fuente_marca_url = models.URLField(max_length=500, default="https://fonts.googleapis.com/css2?family=Parisienne&display=swap")
    fuente_marca_nombre = models.CharField(max_length=100, default="'Parisienne', cursive")

    # Botón de Reseteo
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
    titulo = models.CharField(max_length=100, help_text="Ej: ¡Ofertas de Fin de Semana!")
    subtitulo = models.CharField(max_length=200, blank=True, help_text="Ej: Hasta 50% en productos seleccionados")
    imagen = models.ImageField(upload_to='banners/', help_text="Imagen de fondo (1200x400px recomendado)")
    
    productos_destacados = models.ManyToManyField(Producto, blank=True, related_name="banners")
    enlace = models.URLField(blank=True, help_text="URL a la que dirigirá el botón si NO hay productos destacados.")
    texto_boton = models.CharField(max_length=50, default="Ver ahora")
    activo = models.BooleanField(default=False, help_text="Marca esta casilla para que este banner se muestre en la página principal.")

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        if self.activo:
            Banner.objects.filter(activo=True).exclude(pk=self.pk).update(activo=False)
        super(Banner, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "Banner Promocional"
        verbose_name_plural = "Banners Promocionales"

class Pagina(models.Model):
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
    key = models.CharField(max_length=255, unique=True, verbose_name="Clave de API")
    activa = models.BooleanField(default=True, help_text="Desmarca esta casilla para desactivar la clave temporalmente.")
    notas = models.TextField(blank=True, help_text="Notas internas (ej: 'Clave de cuenta personal', 'Clave de prueba').")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Clave de API de Gemini"
        verbose_name_plural = "Claves de API de Gemini"

    def __str__(self):
        return f"{self.key[:8]}...{self.key[-4:]}"

# --- INICIO DE LA MEJORA: Modelos para la Ruleta de la Suerte v3 ---

class ConfiguracionRuleta(SingletonModel):
    activa = models.BooleanField(default=False, help_text="Marca esta casilla para mostrar la ruleta en la web.")
    titulo = models.CharField(max_length=100, default="¡Gira y Gana!", help_text="El título que aparecerá en el pop-up de la ruleta (ej: 'Especial de Halloween').")
    sonido_giro = models.FileField(upload_to='sonidos_ruleta/', blank=True, null=True, help_text="Sonido (MP3) que se reproduce mientras la ruleta gira.")
    sonido_premio = models.FileField(upload_to='sonidos_ruleta/', blank=True, null=True, help_text="Sonido (MP3) que se reproduce al ganar un premio.")
    
    class Meta:
        verbose_name = "Configuración de la Ruleta"

    def __str__(self):
        return "Configuración de la Ruleta"

class PremioRuleta(models.Model):
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
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True)
    ultima_tirada = models.DateTimeField()

    class Meta:
        verbose_name = "Tirada de Ruleta"
        verbose_name_plural = "Tiradas de Ruleta"

    def puede_jugar(self):
        return timezone.now() > self.ultima_tirada + timedelta(hours=24)

    def __str__(self):
        return f"Última tirada de {self.usuario.username}: {self.ultima_tirada.strftime('%Y-%m-%d %H:%M')}"
# --- FIN DE LA MEJORA ---

# === INICIO DE LA MEJORA: Modelo para el Centro de Control del Chatbot ===
class ConfiguracionChatbot(SingletonModel):
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

# === FIN DE LA MEJORA ===
