# gastos/models.py

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

    # Usuario propietario (ya existía)
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='facturas',
        null=True,
        blank=True
    )

    # Imagen original (ya existía)
    imagen = models.ImageField(upload_to='facturas/', blank=True, null=True)

    # ✅ NUEVO: indica si fue cargada manualmente (sin OCR)
    carga_manual = models.BooleanField(default=False)

    # Tipo de factura (ya existía)
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='no_electronica'
    )

    # Datos de la factura (ya existían)
    fecha_emision = models.DateField(blank=True, null=True)
    timbrado = models.CharField(max_length=100, blank=True)
    numero_factura = models.CharField(max_length=50, blank=True, help_text="Número de factura (ej: 001-001-0000001)")
    ruc = models.CharField(max_length=20, blank=True)
    nombre_proveedor = models.CharField(max_length=200, blank=True)

    importe_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )

    # ✅ NUEVO: campo para el valor del impuesto (IVA u otro)
    importe_impuesto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Valor del impuesto incluido en la factura (ej: IVA)"
    )

    # Texto OCR (ya existía)
    texto_ocr = models.TextField(blank=True)

    # Estado y notas (ya existían)
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente'
    )
    notas = models.TextField(blank=True)

    # Fechas automáticas (ya existían)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        ordering = ['-creado']

    def __str__(self):
        return f"{self.usuario} | {self.nombre_proveedor} | {self.importe_total}"


# ✅ NUEVO: Modelo de Ingresos (carga manual, sin imagen)
class Ingreso(models.Model):

    CATEGORIA_CHOICES = [
        ('sueldo', 'Sueldo'),
        ('freelance', 'Freelance'),
        ('venta', 'Venta'),
        ('alquiler', 'Alquiler'),
        ('transferencia', 'Transferencia'),
        ('otro', 'Otro'),
    ]

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ingresos'
    )

    descripcion = models.CharField(max_length=255)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    categoria = models.CharField(
        max_length=50,
        choices=CATEGORIA_CHOICES,
        default='otro'
    )
    fecha = models.DateField()
    notas = models.TextField(blank=True)

    # Fechas automáticas
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ingreso'
        verbose_name_plural = 'Ingresos'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.usuario} | {self.descripcion} | {self.monto}"