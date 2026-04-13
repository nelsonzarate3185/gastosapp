from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import Factura
from .serializers import FacturaSerializer
import requests
import re


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

    # Buscar Timbrado
    timbrado = re.search(r'TIMBRADO\s*N[°º]?\s*(\d{6,8})', texto_upper)
    if timbrado:
        datos['timbrado'] = timbrado.group(1)
    else:
        timbrado2 = re.search(r'\b(\d{8})\b', texto)
        if timbrado2:
            datos['timbrado'] = timbrado2.group(1)

    # Buscar RUC
    ruc = re.search(r'RUC[:\s]*(\d{5,8}-\d{1})', texto_upper)
    if ruc:
        datos['ruc'] = ruc.group(1)
    else:
        ruc2 = re.search(r'\b(\d{5,8}-\d{1})\b', texto)
        if ruc2:
            datos['ruc'] = ruc2.group(1)

    # Buscar nombre proveedor
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

    # Buscar importe total
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

    # Buscar fecha DD/MM/YYYY
    fecha = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', texto)
    if fecha:
        from datetime import datetime
        try:
            datos['fecha_emision'] = datetime.strptime(
                fecha.group(), '%d/%m/%Y'
            ).date()
        except ValueError:
            pass
    else:
        # Fecha escrita como "31 de Diciembre 2025"
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


class FacturaUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        imagen = request.FILES.get('imagen')
        tipo = request.data.get('tipo', 'no_electronica')

        if not imagen:
            return Response(
                {'error': 'No se recibió ninguna imagen.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            texto = ocr_con_api(imagen)
            datos = extraer_datos_ocr(texto)

            # TEMPORAL: devolver texto crudo para debug
            return Response({
                'texto_ocr': texto,
                'datos_extraidos': datos
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class FacturaListView(APIView):
    def get(self, request):
        facturas = Factura.objects.all()
        serializer = FacturaSerializer(facturas, many=True)
        return Response(serializer.data)


class FacturaDetailView(APIView):
    def get(self, request, pk):
        try:
            factura = Factura.objects.get(pk=pk)
            serializer = FacturaSerializer(factura)
            return Response(serializer.data)
        except Factura.DoesNotExist:
            return Response(
                {'error': 'Factura no encontrada.'},
                status=status.HTTP_404_NOT_FOUND
            )

    def patch(self, request, pk):
        try:
            factura = Factura.objects.get(pk=pk)
            serializer = FacturaSerializer(
                factura, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        except Factura.DoesNotExist:
            return Response(
                {'error': 'Factura no encontrada.'},
                status=status.HTTP_404_NOT_FOUND
            )

class FacturaConfirmarView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = FacturaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        
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
    facturas = Factura.objects.all()[:20]
    return render(request, 'pwa/home.html', {'facturas': facturas})