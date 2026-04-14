from django.db import models
from django.contrib.auth.models import User

class Factura(models.Model):

    TIPO_CHOICES = [
        ('electronica', 'Factura Electrónica'),
        ('no_electronica', 'Factura No Electrónica'),
    ]

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagada', 'Pagada'),
        ('vencida', 'Vencida'),
    ]

    # Usuario propietario
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='facturas',
        null=True,
        blank=True
    )

    # Imagen original de la factura
    imagen = models.ImageField(upload_to='facturas/', blank=True, null=True)

    # Tipo de factura
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='no_electronica'
    )

    # Datos de la factura
    fecha_emision = models.DateField(blank=True, null=True)
    timbrado = models.CharField(max_length=100, blank=True)
    ruc = models.CharField(max_length=20, blank=True)
    nombre_proveedor = models.CharField(max_length=200, blank=True)
    importe_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )

    # Texto completo extraído por OCR
    texto_ocr = models.TextField(blank=True)

    # Estado y notas
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente'
    )
    notas = models.TextField(blank=True)

    # Fechas automáticas
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        ordering = ['-creado']

    def __str__(self):
        return f"{self.usuario} | {self.nombre_proveedor} | {self.importe_total}"