from django.contrib import admin
from .models import Factura

@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):

    list_display = [
        'nombre_proveedor',
        'timbrado',
        'ruc',
        'fecha_emision',
        'importe_total',
        'tipo',
        'estado',
        'creado',
    ]

    list_filter = ['tipo', 'estado', 'fecha_emision']

    search_fields = ['nombre_proveedor', 'timbrado', 'ruc', 'notas']

    readonly_fields = ['texto_ocr', 'creado', 'actualizado']

    fieldsets = (
        ('Imagen', {
            'fields': ('imagen',)
        }),
        ('Tipo de Factura', {
            'fields': ('tipo',)
        }),
        ('Datos de la Factura', {
            'fields': (
                'fecha_emision',
                'timbrado',
                'ruc',
                'nombre_proveedor',
                'importe_total',
                'estado',
            )
        }),
        ('Información Adicional', {
            'fields': ('notas', 'texto_ocr')
        }),
        ('Fechas del Sistema', {
            'fields': ('creado', 'actualizado'),
            'classes': ('collapse',)
        }),
    )