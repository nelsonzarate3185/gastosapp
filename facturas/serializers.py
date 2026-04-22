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