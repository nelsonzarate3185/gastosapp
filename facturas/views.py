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

    lineas = texto.upper().split('\n')
    texto_upper = texto.upper()

    # Buscar Timbrado (6 a 8 dígitos después de "TIMBRADO")
    timbrado = re.search(r'TIMBRADO\s*N[°º]?\s*(\d{6,8})', texto_upper)
    if timbrado:
        datos['timbrado'] = timbrado.group(1)
    else:
        # Buscar número de 8 dígitos solo
        timbrado2 = re.search(r'\b(\d{8})\b', texto)
        if timbrado2:
            datos['timbrado'] = timbrado2.group(1)

    # Buscar RUC (formato: 12345678-9)
    ruc = re.search(r'RUC[:\s]*(\d{5,8}-\d{1})', texto_upper)
    if ruc:
        datos['ruc'] = ruc.group(1)
    else:
        ruc2 = re.search(r'\b(\d{5,8}-\d{1})\b', texto)
        if ruc2:
            datos['ruc'] = ruc2.group(1)

    # Buscar nombre proveedor (línea que contiene el nombre del negocio)
    for i, linea in enumerate(lineas):
        if any(palabra in linea for palabra in ['CASA', 'EMPRESA', 'S.A', 'S.R.L', 'CONSORCIO', 'COMERCIAL']):
            # Tomar la línea siguiente si parece ser el nombre
            if i + 1 < len(lineas) and len(lineas[i+1].strip()) > 3:
                datos['nombre_proveedor'] = lineas[i+1].strip().title()
            else:
                datos['nombre_proveedor'] = linea.strip().title()
            break

    # Si no encontró proveedor buscar después de "RAZÓN SOCIAL"
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
        # Buscar cualquier número grande como total
        montos = re.findall(r'\b(\d{3,3}\.\d{3})\b', texto)
        if montos:
            monto_str = montos[-1].replace('.', '')
            try:
                datos['importe_total'] = float(monto_str)
            except ValueError:
                pass

    # Buscar fecha (DD/MM/YYYY o escrita)
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