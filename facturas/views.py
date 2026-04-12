from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from .models import Factura
from .serializers import FacturaSerializer
import pytesseract
from PIL import Image
import re

pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


def extraer_datos_ocr(texto):
    """
    Extrae datos clave del texto OCR de una factura paraguaya.
    """
    datos = {
        'texto_ocr': texto,
        'nombre_proveedor': '',
        'timbrado': '',
        'ruc': '',
        'importe_total': None,
        'fecha_emision': None,
    }

    # Buscar Timbrado (número de 8 dígitos)
    timbrado = re.search(r'[Tt]imbrado[:\s]*(\d{8})', texto)
    if timbrado:
        datos['timbrado'] = timbrado.group(1)

    # Buscar RUC (formato: 12345678-9)
    ruc = re.search(r'\b\d{6,8}-\d{1}\b', texto)
    if ruc:
        datos['ruc'] = ruc.group()

    # Buscar importe total
    importe = re.search(
        r'[Tt]otal[:\s]*[\$Gs\.]*\s*([\d.,]+)',
        texto
    )
    if importe:
        monto_str = importe.group(1).replace('.', '').replace(',', '.').strip()
        try:
            datos['importe_total'] = float(monto_str)
        except ValueError:
            pass

    # Buscar fecha (formato DD/MM/YYYY)
    fecha = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', texto)
    if fecha:
        from datetime import datetime
        try:
            datos['fecha_emision'] = datetime.strptime(
                fecha.group(), '%d/%m/%Y'
            ).date()
        except ValueError:
            pass

    return datos


class FacturaUploadView(APIView):
    """
    Recibe la imagen de la factura, aplica OCR y guarda los datos.
    """
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
            img = Image.open(imagen)
            texto = pytesseract.image_to_string(img, lang='spa')
            datos = extraer_datos_ocr(texto)

            imagen.seek(0)
            factura = Factura.objects.create(
                imagen=imagen,
                tipo=tipo,
                texto_ocr=datos['texto_ocr'],
                nombre_proveedor=datos['nombre_proveedor'],
                timbrado=datos['timbrado'],
                ruc=datos['ruc'],
                importe_total=datos['importe_total'],
                fecha_emision=datos['fecha_emision'],
            )

            serializer = FacturaSerializer(factura)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FacturaListView(APIView):
    """
    Lista todas las facturas.
    """
    def get(self, request):
        facturas = Factura.objects.all()
        serializer = FacturaSerializer(facturas, many=True)
        return Response(serializer.data)


class FacturaDetailView(APIView):
    """
    Ver o editar una factura específica.
    """
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
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

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