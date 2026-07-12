# facturas/serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Factura, Ingreso, ContadorUsuario


# ── Serializer auxiliar para mostrar datos del usuario ──────────────────────
class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


# ── Factura ──────────────────────────────────────────────────────────────────
class FacturaSerializer(serializers.ModelSerializer):
    # Muestra datos del usuario en lectura, acepta ID en escritura
    usuario_detalle = UsuarioSerializer(source='usuario', read_only=True)

    class Meta:
        model = Factura
        fields = [
            'id',
            'usuario',           # FK para escritura (enviar user.id)
            'usuario_detalle',   # Objeto completo para lectura
            'imagen',
            'carga_manual',      # ✅ NUEVO
            'tipo',
            'fecha_emision',
            'timbrado',
            'numero_factura',
            'ruc',
            'nombre_proveedor',
            'importe_total',
            'importe_impuesto',  # ✅ NUEVO
            'texto_ocr',
            'estado',
            'notas',
            'creado',
            'actualizado',
        ]
        read_only_fields = ['creado', 'actualizado']

    def validate(self, data):
        ruc = data.get('ruc', '') or ''
        timbrado = data.get('timbrado', '') or ''
        numero_factura = data.get('numero_factura', '') or ''
        usuario = data.get('usuario')

        if ruc and timbrado and numero_factura and usuario:
            qs = Factura.objects.filter(
                usuario=usuario,
                ruc=ruc,
                timbrado=timbrado,
                numero_factura=numero_factura,
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    f'Ya existe una factura con RUC {ruc}, timbrado {timbrado} y número {numero_factura}.'
                )
        return data


# ── Ingreso ──────────────────────────────────────────────────────────────────
class IngresoSerializer(serializers.ModelSerializer):
    usuario_detalle = UsuarioSerializer(source='usuario', read_only=True)

    class Meta:
        model = Ingreso
        fields = [
            'id',
            'usuario',
            'usuario_detalle',
            'descripcion',
            'monto',
            'categoria',
            'fecha',
            'notas',
            'creado',
            'actualizado',
        ]
        read_only_fields = ['creado', 'actualizado']


# ── Contador / Usuarios Normales ─────────────────────────────────────────────

class ContadorUsuarioListSerializer(serializers.ModelSerializer):
    usuario_normal_username = serializers.CharField(source='usuario_normal.username', read_only=True)
    usuario_normal_email = serializers.CharField(source='usuario_normal.email', read_only=True)
    usuario_normal_nombre = serializers.SerializerMethodField()

    class Meta:
        model = ContadorUsuario
        fields = [
            'id', 'usuario_normal', 'usuario_normal_username',
            'usuario_normal_email', 'usuario_normal_nombre',
            'ruc_usuario', 'nombre_razon_social', 'direccion', 'telefono', 'email',
            'puede_crear_facturas', 'puede_crear_ingresos',
            'puede_editar_transacciones', 'puede_ver_reportes',
            'activo', 'creado',
        ]

    def get_usuario_normal_nombre(self, obj):
        u = obj.usuario_normal
        return u.get_full_name() or u.username


class ContadorUsuarioDetailSerializer(serializers.ModelSerializer):
    usuario_normal_data = serializers.SerializerMethodField()

    class Meta:
        model = ContadorUsuario
        fields = [
            'id', 'usuario_normal', 'usuario_normal_data',
            'ruc_usuario', 'nombre_razon_social', 'direccion', 'telefono', 'email',
            'puede_crear_facturas', 'puede_crear_ingresos',
            'puede_editar_transacciones', 'puede_ver_reportes',
            'activo', 'fecha_bloqueo', 'razon_bloqueo', 'creado', 'actualizado',
        ]

    def get_usuario_normal_data(self, obj):
        u = obj.usuario_normal
        return {
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'first_name': u.first_name,
            'last_name': u.last_name,
        }


class ContadorUsuarioCreateSerializer(serializers.Serializer):
    """Crea o actualiza la relación contador-usuario buscando por email o username."""
    email = serializers.EmailField()
    username = serializers.CharField(max_length=150, required=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    ruc_usuario = serializers.CharField(max_length=20, required=False, allow_blank=True)
    nombre_razon_social = serializers.CharField(max_length=255, required=False, allow_blank=True)
    direccion = serializers.CharField(max_length=255, required=False, allow_blank=True)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)
    puede_crear_facturas = serializers.BooleanField(default=True)
    puede_crear_ingresos = serializers.BooleanField(default=True)
    puede_editar_transacciones = serializers.BooleanField(default=True)
    puede_ver_reportes = serializers.BooleanField(default=True)


class ContadorFacturaSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)
    registrado_por_username = serializers.CharField(source='registrado_por.username', read_only=True)

    class Meta:
        model = Factura
        fields = [
            'id', 'usuario', 'usuario_username', 'registrado_por', 'registrado_por_username',
            'tipo', 'fecha_emision', 'timbrado', 'numero_factura', 'ruc',
            'nombre_proveedor', 'importe_total', 'importe_impuesto',
            'estado', 'notas', 'creado',
        ]
        read_only_fields = ['registrado_por', 'creado']


class ContadorIngresoSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)
    registrado_por_username = serializers.CharField(source='registrado_por.username', read_only=True)

    class Meta:
        model = Ingreso
        fields = [
            'id', 'usuario', 'usuario_username', 'registrado_por', 'registrado_por_username',
            'descripcion', 'monto', 'categoria', 'fecha', 'notas', 'creado',
        ]
        read_only_fields = ['registrado_por', 'creado']