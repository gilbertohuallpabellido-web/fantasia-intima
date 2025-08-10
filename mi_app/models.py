# mi_app/models.py
from django.db import models
from django.conf import settings
import uuid

class Producto(models.Model):
    # --- LISTA DE COLORES AMPLIADA ---
    COLORES_CHOICES = [
        # Colores Clásicos
        ('black', 'Negro'),
        ('white', 'Blanco'),
        ('red', 'Rojo'),
        ('wine', 'Vino'),
        ('nude', 'Nude'),
        ('navy', 'Azul Marino'),

        # Colores Vibrantes
        ('pink', 'Rosa'),
        ('fuchsia', 'Fucsia'),
        ('purple', 'Púrpura'),
        ('blue', 'Azul Eléctrico'),
        ('green', 'Verde Esmeralda'),
        ('yellow', 'Amarillo'),
        
        # Tonos Metálicos y Estampados
        ('gold', 'Dorado'),
        ('silver', 'Plateado'),
        ('leopard', 'Leopardo'),
        ('snake', 'Serpiente'),
    ]
    # ---------------------------------

    CATEGORIAS_CHOICES = [
        ('mallas_enterizas', 'Mallas enterizas'),
        ('lenceria', 'Lencería'),
        ('disfraz_sexi', 'Disfraz sexi'),
    ]
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.CharField(max_length=50, choices=CATEGORIAS_CHOICES, default='lenceria')
    color_principal = models.CharField(max_length=50, choices=COLORES_CHOICES, default='red')
    imagen_principal = models.ImageField(upload_to='productos/', blank=True, null=True)
    es_nueva_coleccion = models.BooleanField(default=False, verbose_name="¿Es de la Nueva Colección?")

    @property
    def total_stock(self):
        return sum(variant.stock for variant in self.variantes.all())

    def __str__(self):
        return self.nombre

class ColorVariante(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='variantes')
    # Asegúrate que las variantes también usen la lista de colores actualizada
    color = models.CharField(max_length=50, choices=Producto.COLORES_CHOICES)
    imagen = models.ImageField(upload_to='productos/')
    stock = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.producto.nombre} - {self.get_color_display()}"

class PedidoWhatsApp(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo_pedido = models.CharField(max_length=20, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    @property
    def subtotal(self):
        return sum(detalle.subtotal for detalle in self.detalles.all())

    @property
    def costo_envio(self):
        # Asegurarse de que total sea mayor o igual a subtotal para evitar valores negativos
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