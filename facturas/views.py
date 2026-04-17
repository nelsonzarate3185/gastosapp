# facturas/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from .models import Factura, Ingreso
from .serializers import FacturaSerializer, IngresoSerializer, UsuarioSerializer
import requests
import re
import csv
import io
from django.http import HttpResponse
from django.db.models.functions import TruncMonth
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# ══════════════════════════════════════════════════════
# OCR - Sin cambios en la lógica, solo se mantiene
# ══════════════════════════════════════════════════════

def ocr_con_api(imagen):
    api_key = settings.OCR_API_KEY
    response = requests.post(
        'https://api.ocr.space/parse/image',
        files={'image': imagen},
        data={
            'apikey': api_key,
            'language': 'spa',
            'isOverlayRequired': False,
        },
        timeout=30
    )
    result = response.json()
    if result.get('IsErroredOnProcessing'):
        raise Exception(result.get('ErrorMessage', 'Error en OCR'))
    parsed = result.get('ParsedResults', [])
    if not parsed:
        return ''
    return parsed[0].get('ParsedText', '')


def extraer_datos_ocr(texto):
    datos = {
        'texto_ocr': texto,
        'nombre_proveedor': '',
        'timbrado': '',
        'ruc': '',
        'importe_total': None,
        'fecha_emision': None,
    }

    lineas = texto.upper().split('\n')
    texto_upper = texto.upper()

    timbrado = re.search(r'TIMBRADO\s*N[°º]?\s*(\d{6,8})', texto_upper)
    if timbrado:
        datos['timbrado'] = timbrado.group(1)
    else:
        timbrado2 = re.search(r'\b(\d{8})\b', texto)
        if timbrado2:
            datos['timbrado'] = timbrado2.group(1)

    ruc = re.search(r'RUC[:\s]*(\d{5,8}-\d{1})', texto_upper)
    if ruc:
        datos['ruc'] = ruc.group(1)
    else:
        ruc2 = re.search(r'\b(\d{5,8}-\d{1})\b', texto)
        if ruc2:
            datos['ruc'] = ruc2.group(1)

    for i, linea in enumerate(lineas):
        if any(p in linea for p in ['CASA', 'EMPRESA', 'S.A', 'S.R.L', 'CONSORCIO', 'COMERCIAL']):
            if i + 1 < len(lineas) and len(lineas[i+1].strip()) > 3:
                datos['nombre_proveedor'] = lineas[i+1].strip().title()
            else:
                datos['nombre_proveedor'] = linea.strip().title()
            break

    if not datos['nombre_proveedor']:
        razon = re.search(r'NOMBRE O RAZ[OÓ]N SOCIAL[:\s]*(.+)', texto_upper)
        if razon:
            datos['nombre_proveedor'] = razon.group(1).strip().title()

    total = re.search(r'TOTAL A PAGAR[:\s]*([\d.,]+)', texto_upper)
    if total:
        monto_str = total.group(1).replace('.', '').replace(',', '').strip()
        try:
            datos['importe_total'] = float(monto_str)
        except ValueError:
            pass
    else:
        montos = re.findall(r'\b(\d{3,3}\.\d{3})\b', texto)
        if montos:
            monto_str = montos[-1].replace('.', '')
            try:
                datos['importe_total'] = float(monto_str)
            except ValueError:
                pass

    fecha = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', texto)
    if fecha:
        from datetime import datetime
        try:
            datos['fecha_emision'] = datetime.strptime(fecha.group(), '%d/%m/%Y').date()
        except ValueError:
            pass
    else:
        meses = {
            'ENERO': '01', 'FEBRERO': '02', 'MARZO': '03',
            'ABRIL': '04', 'MAYO': '05', 'JUNIO': '06',
            'JULIO': '07', 'AGOSTO': '08', 'SEPTIEMBRE': '09',
            'OCTUBRE': '10', 'NOVIEMBRE': '11', 'DICIEMBRE': '12'
        }
        fecha_escrita = re.search(
            r'(\d{1,2})\s+DE\s+(ENERO|FEBRERO|MARZO|ABRIL|MAYO|JUNIO|JULIO|AGOSTO|SEPTIEMBRE|OCTUBRE|NOVIEMBRE|DICIEMBRE)\s+(\d{4})',
            texto_upper
        )
        if fecha_escrita:
            from datetime import datetime
            dia = fecha_escrita.group(1).zfill(2)
            mes = meses[fecha_escrita.group(2)]
            anio = fecha_escrita.group(3)
            try:
                datos['fecha_emision'] = datetime.strptime(
                    f"{dia}/{mes}/{anio}", '%d/%m/%Y'
                ).date()
            except ValueError:
                pass

    return datos


# ══════════════════════════════════════════════════════
# FACTURAS - ENDPOINTS API
# ══════════════════════════════════════════════════════

class FacturaUploadView(APIView):
    """Procesa imagen con OCR y devuelve datos extraídos (sin guardar)."""
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        imagen = request.FILES.get('imagen')
        if not imagen:
            return Response(
                {'error': 'No se recibió ninguna imagen.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            texto = ocr_con_api(imagen)
            datos = extraer_datos_ocr(texto)
            return Response(
                {'texto_ocr': texto, 'datos_extraidos': datos},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FacturaConfirmarView(APIView):
    """
    Guarda la factura en la DB.
    - Si viene usuario en el body, lo usa (admin puede asignar a otro usuario).
    - Si no viene, asigna el usuario logueado.
    - Si carga_manual=true, no requiere imagen.
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        data = request.data.copy()

        # Asignar usuario: usa el del body si existe, sino el logueado
        if not data.get('usuario') and request.user.is_authenticated:
            data['usuario'] = request.user.id

        # Marcar como carga manual si no hay imagen
        if not request.FILES.get('imagen'):
            data['carga_manual'] = True

        serializer = FacturaSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FacturaListView(APIView):
    """Lista facturas del usuario logueado."""

    def get(self, request):
        facturas = Factura.objects.filter(
            usuario=request.user
        ).select_related('usuario')
        serializer = FacturaSerializer(facturas, many=True)
        return Response(serializer.data)


class FacturaDetailView(APIView):
    """Obtiene o edita una factura específica."""

    def get(self, request, pk):
        try:
            factura = Factura.objects.get(pk=pk, usuario=request.user)
            return Response(FacturaSerializer(factura).data)
        except Factura.DoesNotExist:
            return Response(
                {'error': 'Factura no encontrada.'},
                status=status.HTTP_404_NOT_FOUND
            )

    def patch(self, request, pk):
        try:
            factura = Factura.objects.get(pk=pk, usuario=request.user)
            serializer = FacturaSerializer(factura, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Factura.DoesNotExist:
            return Response(
                {'error': 'Factura no encontrada.'},
                status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request, pk):
        try:
            factura = Factura.objects.get(pk=pk, usuario=request.user)
            factura.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Factura.DoesNotExist:
            return Response(
                {'error': 'Factura no encontrada.'},
                status=status.HTTP_404_NOT_FOUND
            )


# ══════════════════════════════════════════════════════
# IMPORTACIÓN CSV DE FACTURAS
# ══════════════════════════════════════════════════════

# Encabezados esperados en el CSV (insensible a mayúsculas/espacios)
_CSV_COLUMNAS = ['tipo', 'timbrado', 'ruc', 'nombre_proveedor', 'numero_factura', 'total_factura', 'total_iva']

_TIPO_MAP = {
    'ELECTRONICA': 'electronica',
    'NO ELECTRONICA': 'no_electronica',
    'NO_ELECTRONICA': 'no_electronica',
}


def _normalizar_monto(valor):
    """Convierte '1.500.000' o '1500000' o '1,500,000' a Decimal."""
    valor = valor.strip().replace(' ', '')
    # Si tiene punto como separador de miles (ej: 1.500.000) → quitar puntos
    # Si tiene coma como separador decimal (ej: 1500,50) → reemplazar por punto
    # Heurística: si hay más de un punto, son separadores de miles
    if valor.count('.') > 1:
        valor = valor.replace('.', '')
    elif valor.count('.') == 1 and valor.count(',') == 0:
        # puede ser separador decimal o de miles — si hay 3 dígitos después del punto, es miles
        partes = valor.split('.')
        if len(partes[1]) == 3:
            valor = valor.replace('.', '')
    valor = valor.replace(',', '.')
    return valor


class FacturaImportCSVView(APIView):
    """
    Importa facturas desde un archivo CSV separado por punto y coma (;).

    Columnas requeridas (en cualquier orden, insensibles a mayúsculas):
        TIPO ; fecha_emision ; timbrado ; RUC ; nombre_proveedor ; numero_factura ; total_factura ; total_IVA

    TIPO aceptados: ELECTRONICA, NO ELECTRONICA, NO_ELECTRONICA
    fecha_emision: formato DD/MM/YYYY
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Debe iniciar sesión.'}, status=status.HTTP_401_UNAUTHORIZED)

        archivo = request.FILES.get('archivo')
        if not archivo:
            return Response({'error': 'No se recibió ningún archivo.'}, status=status.HTTP_400_BAD_REQUEST)

        if not archivo.name.lower().endswith('.csv'):
            return Response({'error': 'El archivo debe tener extensión .csv.'}, status=status.HTTP_400_BAD_REQUEST)

        # Leer el contenido detectando la codificación
        contenido = archivo.read()
        for encoding in ('utf-8-sig', 'utf-8', 'latin-1'):
            try:
                texto = contenido.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            return Response({'error': 'No se pudo decodificar el archivo. Use UTF-8 o Latin-1.'}, status=status.HTTP_400_BAD_REQUEST)

        reader = csv.DictReader(io.StringIO(texto), delimiter=';')

        # Normalizar nombres de columna
        if reader.fieldnames is None:
            return Response({'error': 'El archivo CSV está vacío o no tiene encabezados.'}, status=status.HTTP_400_BAD_REQUEST)

        col_map = {col.strip().lower(): col for col in reader.fieldnames}
        columnas_requeridas = {
            'tipo': None, 'fecha_emision': None, 'timbrado': None, 'ruc': None,
            'nombre_proveedor': None, 'numero_factura': None,
            'total_factura': None, 'total_iva': None,
        }
        alias = {
            'fecha de emision': 'fecha_emision',
            'fecha de emisión': 'fecha_emision',
            'fecha': 'fecha_emision',
            'nombre del proveedor': 'nombre_proveedor',
            'numero factura': 'numero_factura',
            'número factura': 'numero_factura',
            'total factura': 'total_factura',
            'total iva': 'total_iva',
            'iva': 'total_iva',
        }
        for col_raw, col_original in col_map.items():
            key = alias.get(col_raw, col_raw)
            if key in columnas_requeridas:
                columnas_requeridas[key] = col_original

        faltantes = [k for k, v in columnas_requeridas.items() if v is None]
        if faltantes:
            return Response(
                {'error': f'Faltan las columnas: {", ".join(faltantes)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        importadas = []
        errores = []

        for num_fila, fila in enumerate(reader, start=2):  # start=2 porque fila 1 es encabezado
            def campo(key):
                return (fila.get(columnas_requeridas[key]) or '').strip()

            tipo_raw = campo('tipo').upper()
            tipo = _TIPO_MAP.get(tipo_raw)
            if not tipo:
                errores.append({
                    'fila': num_fila,
                    'error': f'TIPO inválido: "{campo("tipo")}". Use ELECTRONICA o NO ELECTRONICA.'
                })
                continue

            timbrado = campo('timbrado')
            ruc = campo('ruc')
            nombre_proveedor = campo('nombre_proveedor')
            numero_factura = campo('numero_factura')
            total_factura_str = campo('total_factura')
            total_iva_str = campo('total_iva')
            fecha_str = campo('fecha_emision')

            if not nombre_proveedor:
                errores.append({'fila': num_fila, 'error': 'nombre_proveedor está vacío.'})
                continue

            # Parsear fecha DD/MM/YYYY
            from datetime import datetime as dt
            fecha_emision = None
            if fecha_str:
                try:
                    fecha_emision = dt.strptime(fecha_str, '%d/%m/%Y').date()
                except ValueError:
                    errores.append({'fila': num_fila, 'error': f'fecha_emision inválida: "{fecha_str}". Use DD/MM/YYYY.'})
                    continue

            try:
                importe_total = _normalizar_monto(total_factura_str) if total_factura_str else None
                importe_total = float(importe_total) if importe_total else None
            except (ValueError, AttributeError):
                errores.append({'fila': num_fila, 'error': f'total_factura inválido: "{total_factura_str}".'})
                continue

            try:
                importe_impuesto = _normalizar_monto(total_iva_str) if total_iva_str else None
                importe_impuesto = float(importe_impuesto) if importe_impuesto else None
            except (ValueError, AttributeError):
                errores.append({'fila': num_fila, 'error': f'total_iva inválido: "{total_iva_str}".'})
                continue

            factura = Factura(
                usuario=request.user,
                tipo=tipo,
                fecha_emision=fecha_emision,
                timbrado=timbrado,
                ruc=ruc,
                nombre_proveedor=nombre_proveedor,
                numero_factura=numero_factura,
                importe_total=importe_total,
                importe_impuesto=importe_impuesto,
                carga_manual=True,
            )
            factura.save()
            importadas.append({
                'fila': num_fila,
                'id': factura.pk,
                'nombre_proveedor': nombre_proveedor,
                'importe_total': importe_total,
            })

        return Response({
            'importadas': len(importadas),
            'errores': len(errores),
            'detalle_errores': errores,
            'detalle_importadas': importadas,
        }, status=status.HTTP_200_OK)


# ══════════════════════════════════════════════════════
# REPORTE DE GASTOS — lista detallada con filtros
# ══════════════════════════════════════════════════════

class FacturaReporteGastosView(APIView):
    """
    Lista paginada de facturas con filtros combinables.

    Parámetros GET:
      - desde        YYYY-MM-DD  (fecha_emision >=)
      - hasta        YYYY-MM-DD  (fecha_emision <=)
      - ruc          texto parcial
      - proveedor    texto parcial
      - usuario_id   int  (solo superuser)
      - page         int  (default 1)
      - page_size    int  (default 50, max 200)
    """

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'No autenticado.'}, status=status.HTTP_401_UNAUTHORIZED)

        qs = Factura.objects.select_related('usuario').order_by('-fecha_emision', '-creado')

        # Permisos: superuser ve todos, usuario normal solo los propios
        if request.user.is_superuser:
            usuario_id = request.GET.get('usuario_id')
            if usuario_id:
                qs = qs.filter(usuario_id=usuario_id)
        else:
            qs = qs.filter(usuario=request.user)

        # Filtros
        desde = request.GET.get('desde')
        hasta = request.GET.get('hasta')
        ruc = request.GET.get('ruc', '').strip()
        proveedor = request.GET.get('proveedor', '').strip()

        if desde:
            qs = qs.filter(fecha_emision__gte=desde)
        if hasta:
            qs = qs.filter(fecha_emision__lte=hasta)
        if ruc:
            qs = qs.filter(ruc__icontains=ruc)
        if proveedor:
            qs = qs.filter(nombre_proveedor__icontains=proveedor)

        total = qs.count()
        total_importe = qs.aggregate(s=Sum('importe_total'))['s'] or 0

        # Paginación
        try:
            page = max(1, int(request.GET.get('page', 1)))
            page_size = min(200, max(1, int(request.GET.get('page_size', 50))))
        except (ValueError, TypeError):
            page, page_size = 1, 50

        offset = (page - 1) * page_size
        facturas = qs[offset:offset + page_size]

        def ruc_sin_dv(ruc_str):
            """Devuelve solo la parte numérica antes del guion."""
            return ruc_str.split('-')[0].strip() if ruc_str else ''

        items = []
        for f in facturas:
            items.append({
                'id': f.pk,
                'usuario': f.usuario.get_full_name() or f.usuario.username if f.usuario else '—',
                'tipo': f.get_tipo_display(),
                'fecha_emision': str(f.fecha_emision) if f.fecha_emision else None,
                'timbrado': f.timbrado,
                'numero_factura': f.numero_factura,
                'ruc': ruc_sin_dv(f.ruc),
                'nombre_proveedor': f.nombre_proveedor,
                'importe_total': float(f.importe_total) if f.importe_total is not None else None,
                'importe_impuesto': float(f.importe_impuesto) if f.importe_impuesto is not None else None,
                'estado': f.get_estado_display(),
            })

        return Response({
            'total': total,
            'total_importe': float(total_importe),
            'page': page,
            'page_size': page_size,
            'pages': -(-total // page_size),   # ceil division
            'items': items,
        })


# ══════════════════════════════════════════════════════
# EXPORTACIÓN EXCEL DE GASTOS
# ══════════════════════════════════════════════════════

def _ruc_sin_dv(ruc_str):
    return ruc_str.split('-')[0].strip() if ruc_str else ''


class FacturaExportExcelView(APIView):
    """
    Descarga un archivo Excel con las facturas filtradas.

    Parámetros GET:
      - desde        YYYY-MM-DD
      - hasta        YYYY-MM-DD
      - usuario_id   int (solo superuser)
    """

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'No autenticado.'}, status=status.HTTP_401_UNAUTHORIZED)

        qs = Factura.objects.select_related('usuario').order_by('fecha_emision', 'nombre_proveedor')

        if request.user.is_superuser:
            usuario_id = request.GET.get('usuario_id')
            if usuario_id:
                qs = qs.filter(usuario_id=usuario_id)
        else:
            qs = qs.filter(usuario=request.user)

        desde = request.GET.get('desde')
        hasta = request.GET.get('hasta')
        if desde:
            qs = qs.filter(fecha_emision__gte=desde)
        if hasta:
            qs = qs.filter(fecha_emision__lte=hasta)

        # ── Construir Excel ────────────────────────────────────────────────────
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Gastos'

        # Estilos
        hdr_fill   = PatternFill('solid', fgColor='1A73E8')
        hdr_font   = Font(bold=True, color='FFFFFF', size=11)
        hdr_align  = Alignment(horizontal='center', vertical='center')
        total_fill = PatternFill('solid', fgColor='E8F0FE')
        total_font = Font(bold=True, size=11)
        thin = Side(style='thin', color='CCCCCC')
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        # Encabezados
        columnas = ['Usuario', 'Tipo', 'Fecha', 'Timbrado', 'N° Factura', 'RUC', 'Proveedor', 'Importe (Gs.)']
        for col_idx, titulo in enumerate(columnas, 1):
            cell = ws.cell(row=1, column=col_idx, value=titulo)
            cell.fill  = hdr_fill
            cell.font  = hdr_font
            cell.alignment = hdr_align
            cell.border = border

        ws.row_dimensions[1].height = 22

        # Datos
        total_importe = 0
        for row_idx, f in enumerate(qs, start=2):
            usuario_str = ''
            if f.usuario:
                usuario_str = f.usuario.get_full_name() or f.usuario.username
            importe = float(f.importe_total) if f.importe_total is not None else 0
            total_importe += importe

            fila = [
                usuario_str,
                f.get_tipo_display(),
                f.fecha_emision.strftime('%d/%m/%Y') if f.fecha_emision else '',
                f.timbrado,
                f.numero_factura,
                _ruc_sin_dv(f.ruc),
                f.nombre_proveedor,
                importe,
            ]
            for col_idx, valor in enumerate(fila, 1):
                cell = ws.cell(row=row_idx, column=col_idx, value=valor)
                cell.border = border
                cell.alignment = Alignment(vertical='center')
                if col_idx == 8:  # Importe
                    cell.number_format = '#,##0'

        # Fila total
        total_row = qs.count() + 2
        ws.cell(row=total_row, column=7, value='TOTAL').font = total_font
        ws.cell(row=total_row, column=7).fill = total_fill
        ws.cell(row=total_row, column=7).alignment = Alignment(horizontal='right')
        total_cell = ws.cell(row=total_row, column=8, value=total_importe)
        total_cell.font = total_font
        total_cell.fill = total_fill
        total_cell.number_format = '#,##0'

        # Anchos de columna
        anchos = [22, 18, 14, 14, 20, 14, 32, 18]
        for i, ancho in enumerate(anchos, 1):
            ws.column_dimensions[get_column_letter(i)].width = ancho

        ws.freeze_panes = 'A2'

        # Nombre de archivo
        from datetime import date
        sufijo = ''
        if desde or hasta:
            sufijo = f"_{desde or ''}_{hasta or ''}"
        filename = f"gastos{sufijo}_{date.today().strftime('%Y%m%d')}.xlsx"

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        return response


# ══════════════════════════════════════════════════════
# INGRESOS - ENDPOINTS API  ✅ NUEVO
# ══════════════════════════════════════════════════════

class IngresoListCreateView(APIView):
    """Lista y crea ingresos del usuario logueado."""

    def get(self, request):
        ingresos = Ingreso.objects.filter(
            usuario=request.user
        ).select_related('usuario')
        serializer = IngresoSerializer(ingresos, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data.copy()
        data['usuario'] = request.user.id
        serializer = IngresoSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IngresoDetailView(APIView):
    """Obtiene, edita o elimina un ingreso específico."""

    def _get_ingreso(self, pk, user):
        try:
            return Ingreso.objects.get(pk=pk, usuario=user)
        except Ingreso.DoesNotExist:
            return None

    def get(self, request, pk):
        ingreso = self._get_ingreso(pk, request.user)
        if not ingreso:
            return Response(
                {'error': 'Ingreso no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(IngresoSerializer(ingreso).data)

    def patch(self, request, pk):
        ingreso = self._get_ingreso(pk, request.user)
        if not ingreso:
            return Response(
                {'error': 'Ingreso no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = IngresoSerializer(ingreso, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        ingreso = self._get_ingreso(pk, request.user)
        if not ingreso:
            return Response(
                {'error': 'Ingreso no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )
        ingreso.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ══════════════════════════════════════════════════════
# DASHBOARD - RESUMEN FINANCIERO  ✅ NUEVO
# ══════════════════════════════════════════════════════

class DashboardView(APIView):
    """
    Retorna resumen financiero del usuario:
    - Balance mensual (ingresos - egresos del mes actual)
    - Totales anuales de ingresos y egresos
    - Últimas facturas e ingresos
    """

    def get(self, request):
        hoy = timezone.now().date()
        mes_actual = hoy.month
        anio_actual = hoy.year

        usuario = request.user

        # ── Egresos (facturas) ───────────────────────────────────────────────
        egresos_mes = Factura.objects.filter(
            usuario=usuario,
            fecha_emision__year=anio_actual,
            fecha_emision__month=mes_actual,
        ).aggregate(total=Sum('importe_total'))['total'] or 0

        egresos_anio = Factura.objects.filter(
            usuario=usuario,
            fecha_emision__year=anio_actual,
        ).aggregate(total=Sum('importe_total'))['total'] or 0

        # ── Ingresos ─────────────────────────────────────────────────────────
        ingresos_mes = Ingreso.objects.filter(
            usuario=usuario,
            fecha__year=anio_actual,
            fecha__month=mes_actual,
        ).aggregate(total=Sum('monto'))['total'] or 0

        ingresos_anio = Ingreso.objects.filter(
            usuario=usuario,
            fecha__year=anio_actual,
        ).aggregate(total=Sum('monto'))['total'] or 0

        # ── Balance ──────────────────────────────────────────────────────────
        balance_mes = ingresos_mes - egresos_mes
        balance_anio = ingresos_anio - egresos_anio

        # ── Últimos registros ─────────────────────────────────────────────────
        ultimas_facturas = Factura.objects.filter(
            usuario=usuario
        ).order_by('-creado')[:5]

        ultimos_ingresos = Ingreso.objects.filter(
            usuario=usuario
        ).order_by('-creado')[:5]

        return Response({
            'periodo': {
                'mes': mes_actual,
                'anio': anio_actual,
            },
            'mensual': {
                'ingresos': float(ingresos_mes),
                'egresos': float(egresos_mes),
                'balance': float(balance_mes),
            },
            'anual': {
                'ingresos': float(ingresos_anio),
                'egresos': float(egresos_anio),
                'balance': float(balance_anio),
            },
            'ultimas_facturas': FacturaSerializer(
                ultimas_facturas, many=True
            ).data,
            'ultimos_ingresos': IngresoSerializer(
                ultimos_ingresos, many=True
            ).data,
        })


# ══════════════════════════════════════════════════════
# USUARIOS - Endpoint para selector de usuario
# ══════════════════════════════════════════════════════

class UsuarioListView(APIView):
    """Lista usuarios disponibles para asignar a una factura."""

    def get(self, request):
        usuarios = User.objects.filter(is_active=True).order_by('username')
        serializer = UsuarioSerializer(usuarios, many=True)
        return Response(serializer.data)


# ══════════════════════════════════════════════════════
# VISTAS DJANGO (HTML/PWA) - Sin cambios estructurales
# ══════════════════════════════════════════════════════

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    return render(request, 'pwa/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required(login_url='login')
def home_view(request):
    facturas = Factura.objects.filter(
        usuario=request.user
    ).order_by('-creado')[:50]
    context = {'facturas': facturas}
    return render(request, 'pwa/home.html', context)

@login_required(login_url='login')
def reporte_view(request):
    """Vista HTML para la página de reportería."""
    return render(request, 'pwa/reporte.html')

class ReporteDashboardView(APIView):
    """
    Dashboard con filtro por usuario.
    Parámetros GET:
      - usuario_id: int (opcional, solo admin)
      - anio: int (opcional, default año actual)
    """

    def get(self, request):
        from django.db.models.functions import ExtractMonth
        import calendar

        anio = int(request.GET.get('anio', timezone.now().year))

        # Determinar qué usuario filtrar
        # Si es superuser puede ver cualquier usuario
        usuario_id = request.GET.get('usuario_id')
        if usuario_id and request.user.is_superuser:
            try:
                usuario_filtro = User.objects.get(pk=usuario_id)
            except User.DoesNotExist:
                usuario_filtro = request.user
        else:
            usuario_filtro = request.user

        meses_nombres = [
            'Ene','Feb','Mar','Abr','May','Jun',
            'Jul','Ago','Sep','Oct','Nov','Dic'
        ]

        # Construir tabla mensual
        mensual = []
        total_ing = 0
        total_egr = 0

        for mes in range(1, 13):
            ing = Ingreso.objects.filter(
                usuario=usuario_filtro,
                fecha__year=anio,
                fecha__month=mes,
            ).aggregate(t=Sum('monto'))['t'] or 0

            egr = Factura.objects.filter(
                usuario=usuario_filtro,
                fecha_emision__year=anio,
                fecha_emision__month=mes,
            ).aggregate(t=Sum('importe_total'))['t'] or 0

            total_ing += float(ing)
            total_egr += float(egr)

            mensual.append({
                'mes': mes,
                'nombre': meses_nombres[mes - 1],
                'ingresos': float(ing),
                'egresos': float(egr),
                'balance': float(ing) - float(egr),
            })

        # Totales generales
        mes_actual = timezone.now().month
        ing_mes = Ingreso.objects.filter(
            usuario=usuario_filtro,
            fecha__year=anio,
            fecha__month=mes_actual,
        ).aggregate(t=Sum('monto'))['t'] or 0

        egr_mes = Factura.objects.filter(
            usuario=usuario_filtro,
            fecha_emision__year=anio,
            fecha_emision__month=mes_actual,
        ).aggregate(t=Sum('importe_total'))['t'] or 0

        return Response({
            'usuario': {
                'id': usuario_filtro.id,
                'username': usuario_filtro.username,
                'nombre': usuario_filtro.get_full_name() or usuario_filtro.username,
            },
            'anio': anio,
            'mes_actual': mes_actual,
            'mensual': mensual,
            'resumen': {
                'ingresos_mes':  float(ing_mes),
                'egresos_mes':   float(egr_mes),
                'balance_mes':   float(ing_mes) - float(egr_mes),
                'ingresos_anio': total_ing,
                'egresos_anio':  total_egr,
                'balance_anio':  total_ing - total_egr,
            },
        })

