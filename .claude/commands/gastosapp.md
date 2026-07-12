---
name: gastosapp
description: Use when developing, testing, deploying, or troubleshooting GastosApp — a Django 5.2 PWA for personal finance tracking with OCR invoice scanning. Covers dev server, migrations, tests, git workflow, and Render deployment.
---

# GastosApp Dev Skill

## Overview

GastosApp es un PWA Django 5.2 para finanzas personales (Paraguay). UI en español, mobile-first, con OCR para facturas vía OCR.space API. SQLite local, PostgreSQL en Render.

## Comandos esenciales

```powershell
# Activar entorno virtual (Windows)
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Migraciones
python manage.py makemigrations
python manage.py migrate

# Servidor de desarrollo
python manage.py runserver

# Estáticos (obligatorio antes del primer run o tras cambios CSS/JS)
python manage.py collectstatic --noinput

# Tests
python manage.py test
python manage.py test facturas.tests.TestClassName.test_method_name
```

## Flujo OCR de facturas

1. Cliente comprime imagen (canvas, max 800px, 80% calidad)
2. `POST /api/facturas/subir/` → OCR.space API → extrae datos (no guarda)
3. `extraer_datos_ocr()` parsea con regex: timbrado, RUC, proveedor, total, fecha
4. Usuario revisa/edita datos extraídos
5. `POST /api/facturas/confirmar/` → guarda en BD

**Nota:** `pytesseract` instalado pero NO se usa — solo OCR.space HTTP API.

## Arquitectura rápida

| Archivo | Rol |
|---|---|
| `facturas/models.py` | `Factura` + `Ingreso` con FK a User |
| `facturas/views.py` | Todos los endpoints (DRF APIView) + OCR + CSV + Excel |
| `facturas/serializers.py` | Serializadores DRF |
| `gastosapp/urls.py` | Todas las rutas |
| `gastosapp/settings.py` | Config via python-decouple |
| `templates/pwa/home.html` | App principal (~837 líneas, vanilla JS) |
| `templates/pwa/reporte.html` | Reportes + Chart.js (~609 líneas) |

## Variables de entorno (.env local)

```env
SECRET_KEY=any-local-secret
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
OCR_API_KEY=helloworld
```

`DATABASE_URL` lo setea Render automáticamente (PostgreSQL). Local usa SQLite.

## Autenticación

Session-based Django auth. Sin API tokens. HTML views con `@login_required`. API views verifican `request.user.is_authenticated`. Superusers ven todos los datos; usuarios regulares solo los suyos.

## Flujo Git

```powershell
# Ver estado
git status

# Pull última versión
git pull origin master

# Commit y push
git add <archivos>
git commit -m "descripción del cambio"
git push origin master
```

Repositorio: `https://github.com/nelsonzarate3185/gastosapp.git`

## Deploy en Render

- `build.sh` ejecuta: install deps → collectstatic → migrate → crea superuser
- Superuser via env vars: `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD`
- Servidor: `gunicorn gastosapp.wsgi:application`
- Tesseract declarado en `aptfile`

## Endpoints API clave

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/facturas/subir/` | OCR scan (NO guarda) |
| POST | `/api/facturas/confirmar/` | Guardar factura |
| GET | `/api/facturas/` | Listar facturas del usuario |
| GET/PATCH/DELETE | `/api/facturas/<id>/` | Detalle factura |
| POST | `/api/facturas/importar-csv/` | Importar CSV masivo |
| GET | `/api/ingresos/` | Listar ingresos |
| POST | `/api/ingresos/` | Crear ingreso |
| GET | `/api/dashboard/` | Resumen mensual + últimos 5 de cada tipo |
| GET | `/api/reporte/` | Desglose mensual |

## Errores comunes

| Error | Solución |
|---|---|
| `ModuleNotFoundError` | `pip install -r requirements.txt` con venv activado |
| Estáticos no cargan | `python manage.py collectstatic --noinput` |
| Error de migración | `python manage.py showmigrations facturas` para ver estado |
| OCR no responde | Verificar `OCR_API_KEY` en `.env` (default: `helloworld`) |
| DB error en Render | Verificar `DATABASE_URL` en variables de entorno de Render |
