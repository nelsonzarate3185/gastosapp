from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum, Q
from django.utils import timezone
from .models import Factura
from .serializers import FacturaSerializer
import requests
import re
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from datetime import date


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
                datos['fecha_emision'] = datetime.strptime(f"{dia}/{mes}/{anio}", '%d/%m/%Y').date()
            except ValueError:
                pass

    return datos


class FacturaUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        imagen = request.FILES.get('imagen')
        if not imagen:
            return Response({'error': 'No se recibió ninguna imagen.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            texto = ocr_con_api(imagen)
            datos = extraer_datos_ocr(texto)
            return Response({'texto_ocr': texto, 'datos_extraidos': datos}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FacturaConfirmarView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        data = request.data.copy()
        # Asignar usuario autenticado
        if request.user.is_authenticated:
            data['usuario'] = request.user.id
        serializer = FacturaSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FacturaListView(APIView):
    def get(self, request):
        facturas = Factura.objects.filter(usuario=request.user)
        serializer = FacturaSerializer(facturas, many=True)
        return Response(serializer.data)


class FacturaDetailView(APIView):
    def get(self, request, pk):
        try:
            factura = Factura.objects.get(pk=pk, usuario=request.user)
            serializer = FacturaSerializer(factura)
            return Response(serializer.data)
        except Factura.DoesNotExist:
            return Response({'error': 'Factura no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, pk):
        try:
            factura = Factura.objects.get(pk=pk, usuario=request.user)
            serializer = FacturaSerializer(factura, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Factura.DoesNotExist:
            return Response({'error': 'Factura no encontrada.'}, status=status.HTTP_404_NOT_FOUND)


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
    # Filtros de búsqueda
    qs = Factura.objects.filter(usuario=request.user)
    q_ruc = request.GET.get('ruc', '')
    q_proveedor = request.GET.get('proveedor', '')
    q_fecha_desde = request.GET.get('fecha_desde', '')
    q_fecha_hasta = request.GET.get('fecha_hasta', '')
    q_estado = request.GET.get('estado', '')

    if q_ruc:
        qs = qs.filter(ruc__icontains=q_ruc)
    if q_proveedor:
        qs = qs.filter(nombre_proveedor__icontains=q_proveedor)
    if q_fecha_desde:
        qs = qs.filter(fecha_emision__gte=q_fecha_desde)
    if q_fecha_hasta:
        qs = qs.filter(fecha_emision__lte=q_fecha_hasta)
    if q_estado:
        qs = qs.filter(estado=q_estado)

    facturas = qs[:50]

    # Dashboard - totales
    anio_actual = timezone.now().year
    mes_actual = timezone.now().month

    total_anual = Factura.objects.filter(
        usuario=request.user,
        fecha_emision__year=anio_actual
    ).aggregate(total=Sum('importe_total'))['total'] or 0

    total_mes = Factura.objects.filter(
        usuario=request.user,
        fecha_emision__year=anio_actual,
        fecha_emision__month=mes_actual
    ).aggregate(total=Sum('importe_total'))['total'] or 0

    # Totales por mes del año actual
    meses_data = []
    nombres_meses = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
    for m in range(1, 13):
        total_m = Factura.objects.filter(
            usuario=request.user,
            fecha_emision__year=anio_actual,
            fecha_emision__month=m
        ).aggregate(total=Sum('importe_total'))['total'] or 0
        meses_data.append({'mes': nombres_meses[m-1], 'total': float(total_m)})

    context = {
        'facturas': facturas,
        'total_anual': total_anual,
        'total_mes': total_mes,
        'meses_data': meses_data,
        'anio_actual': anio_actual,
        'filtros': {
            'ruc': q_ruc,
            'proveedor': q_proveedor,
            'fecha_desde': q_fecha_desde,
            'fecha_hasta': q_fecha_hasta,
            'estado': q_estado,
        }
    }
    return render(request, 'pwa/home.html', context)


@login_required(login_url='login')
def exportar_excel(request):
    facturas = Factura.objects.filter(usuario=request.user).order_by('-fecha_emision')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Facturas'

    # Estilos
    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='1a73e8', end_color='1a73e8', fill_type='solid')
    header_align = Alignment(horizontal='center')

    # Encabezados
    headers = ['ID', 'Proveedor', 'RUC', 'Timbrado', 'Fecha Emisión', 'Importe Total', 'Tipo', 'Estado', 'Notas', 'Creado']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align

    # Datos
    for row, f in enumerate(facturas, 2):
        ws.cell(row=row, column=1, value=f.id)
        ws.cell(row=row, column=2, value=f.nombre_proveedor)
        ws.cell(row=row, column=3, value=f.ruc)
        ws.cell(row=row, column=4, value=f.timbrado)
        ws.cell(row=row, column=5, value=str(f.fecha_emision) if f.fecha_emision else '')
        ws.cell(row=row, column=6, value=float(f.importe_total) if f.importe_total else 0)
        ws.cell(row=row, column=7, value=f.get_tipo_display())
        ws.cell(row=row, column=8, value=f.get_estado_display())
        ws.cell(row=row, column=9, value=f.notas)
        ws.cell(row=row, column=10, value=str(f.creado.strftime('%d/%m/%Y %H:%M')))

    # Ancho de columnas
    anchos = [8, 30, 15, 15, 15, 18, 20, 15, 25, 18]
    for col, ancho in enumerate(anchos, 1):
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = ancho

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="facturas_{request.user.username}_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    wb.save(response)
    return response