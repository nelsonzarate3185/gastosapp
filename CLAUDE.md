# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GastosApp is a Django 5.2 PWA (Progressive Web App) for personal finance tracking — invoices (facturas) with OCR scanning and income (ingresos) management. Deployed on Render with PostgreSQL; SQLite for local development. UI is Spanish/Paraguay-locale, targeting mobile users.

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

# Create superuser
python manage.py createsuperuser

# Collect static files (needed before first run or after template changes)
python manage.py collectstatic --noinput

# Run tests
python manage.py test
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

On Render (production), `DATABASE_URL` is set automatically. Locally, SQLite is used (configured via `dj-database-url` in `settings.py`).

## Architecture

### Apps and Key Files

There is one Django app (`facturas/`) plus the project config (`gastosapp/`):

- [facturas/models.py](facturas/models.py) — Two models: `Factura` (invoices) and `Ingreso` (income entries). Both have `usuario` FK to Django's built-in User.
- [facturas/views.py](facturas/views.py) — All API endpoints (DRF APIView classes) and HTML views. OCR processing and data extraction live here (`extraer_datos_ocr` function).
- [facturas/serializers.py](facturas/serializers.py) — DRF serializers for both models.
- [facturas/admin.py](facturas/admin.py) — Custom admin with Chart.js dashboard, Excel export via openpyxl, and user filtering.
- [gastosapp/urls.py](gastosapp/urls.py) — Routes for both API and HTML views.
- [gastosapp/settings.py](gastosapp/settings.py) — Config with `python-decouple` for env vars; sets `OCR_API_KEY`, file upload limits (10MB), and CSRF trusted origins.

### Frontend

All UI is in [templates/pwa/](templates/pwa/) — vanilla JavaScript (no framework), inline CSS, mobile-first design (600px max-width, bottom navigation bar). The main frontend logic is embedded in [templates/pwa/home.html](templates/pwa/home.html) (~837 lines mixing HTML/CSS/JS).

Static files are served via WhiteNoise (no separate CDN). No build step — JS/CSS is written directly in templates.

### OCR Pipeline

1. Client compresses the uploaded image via canvas (max 800px wide, 80% quality) before sending.
2. `POST /api/facturas/subir/` sends image to **OCR.space API** (key from `OCR_API_KEY` env var; defaults to `helloworld` free key with rate limits).
3. Regex patterns in `extraer_datos_ocr()` extract: timbrado, RUC, provider name, total amount, date.
4. Extracted data is returned to the client for user review/editing.
5. `POST /api/facturas/confirmar/` saves the final data (with or without the original image).

### Authentication

Session-based Django auth only — no API tokens. HTML views use `@login_required`. API views check `request.user.is_authenticated` manually. Superusers can see all users' data; regular users only see their own.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/facturas/subir/` | OCR scan (returns extracted data, does NOT save) |
| POST | `/api/facturas/confirmar/` | Save invoice to DB |
| GET/PATCH/DELETE | `/api/facturas/<id>/` | Invoice detail |
| GET | `/api/facturas/` | List user's invoices |
| GET/POST | `/api/ingresos/` | List/create income |
| GET/PATCH/DELETE | `/api/ingresos/<id>/` | Income detail |
| GET | `/api/dashboard/` | Monthly summary + last 5 of each type |
| GET | `/api/reporte/` | Monthly breakdown (admin: all users; user: own data) |
| GET | `/api/usuarios/` | Active user list (for admin invoice assignment) |

HTML routes: `/` (login), `/home/` (main app), `/reporte/` (reporting), `/logout/`

Admin extras: `/admin/facturas/factura/dashboard/` and `/admin/facturas/factura/dashboard/excel/`

## Deployment (Render)

[build.sh](build.sh) runs on each deploy: installs requirements, collects static, migrates, and creates superuser from env vars (`DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD`). System dependency `tesseract-ocr` is installed via [aptfile](aptfile). Production uses Gunicorn: `gunicorn gastosapp.wsgi:application`.
