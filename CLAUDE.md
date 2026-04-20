# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GastosApp is a Django 5.2 PWA for personal finance tracking — invoices (facturas) with OCR scanning, income (ingresos) management, and financial reporting. Deployed on Render with PostgreSQL; SQLite for local development. UI is in Spanish (Paraguay locale), targeting mobile users.

## Development Commands

```bash
# Activate virtualenv (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start dev server
python manage.py runserver

# Collect static files (required before first run or after changes)
python manage.py collectstatic --noinput

# Run tests
python manage.py test

# Run a single test
python manage.py test facturas.tests.TestClassName.test_method_name
```

## Environment Setup

Create a `.env` file in the project root:
```
SECRET_KEY=any-local-secret
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
OCR_API_KEY=helloworld
```

`DATABASE_URL` is set automatically on Render (PostgreSQL). Locally, SQLite is used via `dj-database-url`. `OCR_API_KEY` defaults to `helloworld` (free OCR.space tier with rate limits).

## Architecture

### Apps and Key Files

One Django app (`facturas/`) plus project config (`gastosapp/`):

- [facturas/models.py](facturas/models.py) — `Factura` (invoices with fields: tipo, estado, timbrado, numero_factura, ruc, nombre_proveedor, importe_total, importe_impuesto, carga_manual) and `Ingreso` (income with categoria: sueldo/freelance/venta/alquiler/transferencia/otro). Both have `usuario` FK to Django's User.
- [facturas/views.py](facturas/views.py) — All API endpoints (DRF `APIView` subclasses) and HTML views. OCR processing (`ocr_con_api`), regex-based data extraction (`extraer_datos_ocr`), CSV import (`FacturaImportCSVView`), and Excel export (`FacturaExportExcelView`) all live here.
- [facturas/serializers.py](facturas/serializers.py) — DRF serializers for both models plus `UsuarioSerializer`.
- [facturas/admin.py](facturas/admin.py) — Custom admin with Chart.js dashboard, Excel export action, and multi-user filtering.
- [gastosapp/urls.py](gastosapp/urls.py) — All URL routes (API + HTML).
- [gastosapp/settings.py](gastosapp/settings.py) — Config via `python-decouple`; 10MB file upload limit; `es-ar` locale; `America/Argentina/Buenos_Aires` timezone; WhiteNoise for static files.

### Frontend

All UI in [templates/pwa/](templates/pwa/) — vanilla JS, inline CSS, mobile-first (600px max-width, bottom tab navigation). No build step.

- [home.html](templates/pwa/home.html) — Main app (~837 lines): two tabs (Facturas + Ingresos), OCR scan flow, manual entry, CSV import, edit/delete modals.
- [reporte.html](templates/pwa/reporte.html) — Reporting (~609 lines): two tabs (financial overview with Chart.js bar chart + paginated Gastos list with Excel export and superuser user-filter).

### OCR Pipeline

1. Client compresses uploaded image via canvas (max 800px, 80% quality) before sending.
2. `POST /api/facturas/subir/` calls **OCR.space API** — returns extracted data without saving.
3. `extraer_datos_ocr()` uses regex to parse: timbrado, RUC, provider name, total amount, date.
4. Client shows extracted data for review/editing.
5. `POST /api/facturas/confirmar/` saves the final invoice.

Note: `pytesseract` is installed as a dependency but is not used — only the OCR.space HTTP API is called.

### CSV Import

`POST /api/facturas/importar-csv/` accepts flexible column name aliases, multiple encodings (utf-8, latin-1, cp1252), and smart amount parsing (removes currency symbols, handles commas/dots). Returns per-row import results.

### Authentication

Session-based Django auth only — no API tokens. HTML views use `@login_required`. API views check `request.user.is_authenticated` manually. Superusers see all users' data; regular users see only their own.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/facturas/subir/` | OCR scan (returns extracted data, does NOT save) |
| POST | `/api/facturas/confirmar/` | Save invoice to DB |
| GET | `/api/facturas/` | List user's invoices |
| GET/PATCH/DELETE | `/api/facturas/<id>/` | Invoice detail |
| POST | `/api/facturas/importar-csv/` | Bulk CSV import |
| GET | `/api/facturas/reporte-gastos/` | Paginated filtered invoice list (50/page) |
| GET | `/api/facturas/exportar-excel/` | Excel export of filtered invoices |
| GET/POST | `/api/ingresos/` | List/create income |
| GET/PATCH/DELETE | `/api/ingresos/<id>/` | Income detail |
| GET | `/api/dashboard/` | Monthly summary + last 5 of each type |
| GET | `/api/reporte/` | Monthly breakdown (admin: all users; user: own data) |
| GET | `/api/usuarios/` | Active user list (for admin invoice assignment) |

HTML routes: `/` (login), `/home/` (main app), `/reporte/` (reporting), `/logout/`

Admin extras: `/admin/facturas/factura/dashboard/` and `/admin/facturas/factura/dashboard/excel/`

## Deployment (Render)

[build.sh](build.sh) runs on each deploy: installs requirements, collects static, migrates, creates superuser from env vars (`DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD`). System dependency `tesseract-ocr` declared in [aptfile](aptfile). Production server: `gunicorn gastosapp.wsgi:application`.
