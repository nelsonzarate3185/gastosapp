# gastos/models.py

from django.db import models
from django.db.models import Q
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

    # Contador que registró esta factura en nombre del usuario
    registrado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='facturas_registradas',
        help_text='Contador que registró esta factura'
    )

    # Fechas automáticas (ya existían)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        ordering = ['-creado']
        permissions = [
            ('ver_todo', 'Puede ver transacciones de todos los usuarios'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['usuario', 'ruc', 'timbrado', 'numero_factura'],
                condition=~Q(ruc='') & ~Q(timbrado='') & ~Q(numero_factura=''),
                name='unique_factura_por_usuario_ruc_timbrado_numero',
            )
        ]

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

    # Contador que registró este ingreso en nombre del usuario
    registrado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ingresos_registrados',
        help_text='Contador que registró este ingreso'
    )

    # Fechas automáticas
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ingreso'
        verbose_name_plural = 'Ingresos'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.usuario} | {self.descripcion} | {self.monto}"


class GoogleSheetConfig(models.Model):
    """Almacena tokens OAuth2 y configuración de Google Sheets por usuario."""

    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='sheet_config'
    )
    spreadsheet_id = models.CharField(max_length=300, blank=True)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expiry = models.DateTimeField(null=True, blank=True)
    ultima_sincronizacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Configuración Google Sheets'
        verbose_name_plural = 'Configuraciones Google Sheets'

    def __str__(self):
        return f"{self.usuario.username} — {self.spreadsheet_id or 'sin hoja'}"

    @property
    def conectado(self):
        return bool(self.refresh_token)


class UserRole(models.Model):
    """Rol de usuario: normal o contador."""

    ROLE_CHOICES = [
        ('usuario_normal', 'Usuario Normal'),
        ('contador', 'Contador'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='rol'
    )
    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default='usuario_normal'
    )
    activo = models.BooleanField(
        default=True,
        help_text='Desactiva para bloquear el usuario'
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Rol de Usuario'
        verbose_name_plural = 'Roles de Usuario'
        ordering = ['user__username']

    def __str__(self):
        return f"{self.user.username} — {self.get_role_display()}"


class ContadorUsuario(models.Model):
    """
    Un usuario normal tiene UN contador asociado.
    Un contador puede gestionar múltiples usuarios normales (relación 1:N).
    """

    usuario_normal = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='mi_contador_asoc',
        help_text='Usuario normal que tiene este contador'
    )
    contador = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mis_usuarios_normales',
        help_text='Contador responsable de este usuario'
    )

    # Datos de identificación para auditoría
    ruc_usuario = models.CharField(max_length=20, blank=True)
    nombre_razon_social = models.CharField(max_length=255, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    # Permisos del contador sobre este usuario
    puede_crear_facturas = models.BooleanField(default=True)
    puede_crear_ingresos = models.BooleanField(default=True)
    puede_editar_transacciones = models.BooleanField(default=True)
    puede_ver_reportes = models.BooleanField(default=True)

    # Estado y control
    activo = models.BooleanField(
        default=True,
        help_text='Desactiva para bloquear usuario sin eliminar'
    )
    fecha_bloqueo = models.DateTimeField(null=True, blank=True)
    razon_bloqueo = models.TextField(blank=True)

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Contador Usuario'
        verbose_name_plural = 'Contadores Usuario'
        ordering = ['-creado']

    def __str__(self):
        contador_str = self.contador.username if self.contador else 'Sin contador'
        return f"{self.usuario_normal.username} → {contador_str}"