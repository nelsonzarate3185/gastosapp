# facturas/serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Factura, Ingreso


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