from django.contrib import admin
from django.http import HttpResponse
from django.urls import path
from django.template.response import TemplateResponse
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth, TruncYear
from django.utils import timezone
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from .models import Factura


# ─────────────────────────────────────────────
# ACCIÓN: Exportar a Excel
# ─────────────────────────────────────────────
def exportar_excel(modeladmin, request, queryset):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Facturas"

    # Estilos
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill("solid", fgColor="1a73e8")
    total_fill = PatternFill("solid", fgColor="E8F0FE")
    center = Alignment(horizontal="center", vertical="center")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Encabezados
    columnas = [
        ("Proveedor", 30),
        ("RUC", 15),
        ("Timbrado", 15),
        ("Fecha Emisión", 18),
        ("Importe Total (₲)", 20),
        ("Tipo", 22),
        ("Estado", 15),
        ("Notas", 40),
        ("Fecha Carga", 22),
    ]

    for col_num, (titulo, ancho) in enumerate(columnas, start=1):
        celda = ws.cell(row=1, column=col_num, value=titulo)
        celda.font = header_font
        celda.fill = header_fill
        celda.alignment = center
        celda.border = border
        ws.column_dimensions[celda.column_letter].width = ancho

    ws.row_dimensions[1].height = 25

    # Datos
    for row_num, f in enumerate(queryset, start=2):
        valores = [
            f.nombre_proveedor,
            f.ruc,
            f.timbrado,
            str(f.fecha_emision) if f.fecha_emision else "",
            float(f.importe_total) if f.importe_total else 0,
            f.get_tipo_display(),
            f.get_estado_display(),
            f.notas,
            f.creado.strftime("%Y-%m-%d %H:%M") if f.creado else "",
        ]
        for col_num, valor in enumerate(valores, start=1):
            celda = ws.cell(row=row_num, column=col_num, value=valor)
            celda.border = border
            celda.alignment = Alignment(vertical="center")

    # Fila de total
    fila_total = queryset.count() + 2
    total = queryset.aggregate(Sum('importe_total'))['importe_total__sum'] or 0

    ws.cell(row=fila_total, column=4, value="TOTAL").font = Font(bold=True)
    celda_total = ws.cell(row=fila_total, column=5, value=float(total))
    celda_total.font = Font(bold=True)
    celda_total.fill = total_fill
    celda_total.border = border

    # Respuesta
    nombre = f"facturas_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{nombre}"'
    wb.save(response)
    return response

exportar_excel.short_description = "📥 Exportar seleccionados a Excel"


# ─────────────────────────────────────────────
# ADMIN
# ─────────────────────────────────────────────
@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):

    actions = [exportar_excel]

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
        ('Imagen', {'fields': ('imagen',)}),
        ('Tipo de Factura', {'fields': ('tipo',)}),
        ('Datos de la Factura', {
            'fields': ('fecha_emision', 'timbrado', 'ruc', 'nombre_proveedor', 'importe_total', 'estado')
        }),
        ('Información Adicional', {'fields': ('notas', 'texto_ocr')}),
        ('Fechas del Sistema', {
            'fields': ('creado', 'actualizado'),
            'classes': ('collapse',)
        }),
    )

    # ── URLs personalizadas del admin ──
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('dashboard/', self.admin_site.admin_view(self.dashboard_view), name='facturas_dashboard'),
        ]
        return custom + urls

    # ── Vista Dashboard ──
    def dashboard_view(self, request):

        # Resumen general
        total_facturas = Factura.objects.count()
        total_importe = Factura.objects.aggregate(Sum('importe_total'))['importe_total__sum'] or 0
        pendientes = Factura.objects.filter(estado='pendiente').count()
        pagadas = Factura.objects.filter(estado='pagada').count()
        vencidas = Factura.objects.filter(estado='vencida').count()

        # Resumen anual
        resumen_anual = (
            Factura.objects
            .filter(fecha_emision__isnull=False)
            .annotate(anio=TruncYear('fecha_emision'))
            .values('anio')
            .annotate(
                total=Sum('importe_total'),
                cantidad=Count('id')
            )
            .order_by('-anio')
        )

        # Resumen mensual (último año)
        anio_actual = timezone.now().year
        resumen_mensual = (
            Factura.objects
            .filter(fecha_emision__isnull=False, fecha_emision__year=anio_actual)
            .annotate(mes=TruncMonth('fecha_emision'))
            .values('mes')
            .annotate(
                total=Sum('importe_total'),
                cantidad=Count('id')
            )
            .order_by('mes')
        )

        # Datos para gráfico mensual (Chart.js)
        meses_labels = []
        meses_valores = []
        MESES = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
        for item in resumen_mensual:
            meses_labels.append(MESES[item['mes'].month - 1])
            meses_valores.append(float(item['total'] or 0))

        # Datos para gráfico por estado (Chart.js)
        estado_labels = ['Pendiente', 'Pagada', 'Vencida']
        estado_valores = [pendientes, pagadas, vencidas]

        context = {
            **self.admin_site.each_context(request),
            'title': 'Dashboard de Facturas',
            'total_facturas': total_facturas,
            'total_importe': total_importe,
            'pendientes': pendientes,
            'pagadas': pagadas,
            'vencidas': vencidas,
            'resumen_anual': resumen_anual,
            'resumen_mensual': resumen_mensual,
            'meses_labels': meses_labels,
            'meses_valores': meses_valores,
            'estado_labels': estado_labels,
            'estado_valores': estado_valores,
            'anio_actual': anio_actual,
            'MESES': MESES,
        }

        return TemplateResponse(request, 'admin/facturas/dashboard.html', context)
        
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['dashboard_url'] = '/admin/facturas/factura/dashboard/'
        return super().changelist_view(request, extra_context=extra_context)