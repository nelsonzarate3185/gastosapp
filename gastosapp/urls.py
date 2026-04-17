# gastosapp/urls.py

from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from facturas.views import (
    # Facturas
    FacturaUploadView,
    FacturaListView,
    FacturaDetailView,
    FacturaConfirmarView,
    FacturaImportCSVView,
    # Ingresos ✅ NUEVO
    IngresoListCreateView,
    IngresoDetailView,
    # Dashboard ✅ NUEVO
    DashboardView,
    # Usuarios ✅ NUEVO
    UsuarioListView,
    # Vistas HTML
    login_view,
    logout_view,
    home_view,
    ReporteDashboardView,   # ✅ NUEVO
    reporte_view,           # ✅ NUEVO
)

urlpatterns = [
    # ── Admin ────────────────────────────────────────────
    path('admin/', admin.site.urls),

    # ── Vistas HTML / PWA ────────────────────────────────
    path('', login_view, name='login'),
    path('home/', home_view, name='home'),
    path('logout/', logout_view, name='logout'),

    # ── API Facturas ─────────────────────────────────────
    path('api/facturas/', FacturaListView.as_view(), name='factura-list'),
    path('api/facturas/subir/', FacturaUploadView.as_view(), name='factura-upload'),
    path('api/facturas/confirmar/', FacturaConfirmarView.as_view(), name='factura-confirmar'),
    path('api/facturas/importar-csv/', FacturaImportCSVView.as_view(), name='factura-importar-csv'),
    path('api/facturas/<int:pk>/', FacturaDetailView.as_view(), name='factura-detail'),

    # ── API Ingresos ✅ NUEVO ─────────────────────────────
    path('api/ingresos/', IngresoListCreateView.as_view(), name='ingreso-list'),
    path('api/ingresos/<int:pk>/', IngresoDetailView.as_view(), name='ingreso-detail'),

    # ── API Dashboard ✅ NUEVO ────────────────────────────
    path('api/dashboard/', DashboardView.as_view(), name='dashboard'),

    # ── API Usuarios ✅ NUEVO ─────────────────────────────
    path('api/usuarios/', UsuarioListView.as_view(), name='usuario-list'),

      path('reporte/', reporte_view, name='reporte'),                          # ✅ NUEVO
    path('api/reporte/', ReporteDashboardView.as_view(), name='api-reporte'), # ✅ NUEVO

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)