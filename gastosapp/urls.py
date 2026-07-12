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
    FacturaReporteGastosView,
    FacturaExportExcelView,
    FacturaExportCSVView,
    IngresoExportCSVView,
    # Ingresos
    IngresoListCreateView,
    IngresoDetailView,
    # Dashboard
    DashboardView,
    # Usuarios
    UsuarioListView,
    # Vistas HTML
    login_view,
    logout_view,
    home_view,
    ReporteDashboardView,
    reporte_view,
    consulta_view,
    # Google Sheets
    sheets_debug,
    sheets_conectar,
    sheets_callback,
    sheets_desconectar,
    SheetsConfigView,
    SheetsSincronizarView,
    # Contador
    ContadorUsuariosListCreateView,
    ContadorUsuariosDetailView,
    ContadorUsuariosBloquearView,
    ContadorFacturasCreateView,
    ContadorIngresosCreateView,
    ContadorTransaccionesListView,
    ContadorDashboardView,
    contador_dashboard_view,
)

urlpatterns = [
    # ── Admin ────────────────────────────────────────────
    path('admin/', admin.site.urls),

    # ── Vistas HTML / PWA ────────────────────────────────
    path('', login_view, name='login'),
    path('home/', home_view, name='home'),
    path('consulta/', consulta_view, name='consulta'),
    path('logout/', logout_view, name='logout'),

    # ── API Facturas ─────────────────────────────────────
    path('api/facturas/', FacturaListView.as_view(), name='factura-list'),
    path('api/facturas/subir/', FacturaUploadView.as_view(), name='factura-upload'),
    path('api/facturas/confirmar/', FacturaConfirmarView.as_view(), name='factura-confirmar'),
    path('api/facturas/importar-csv/', FacturaImportCSVView.as_view(), name='factura-importar-csv'),
    path('api/facturas/reporte-gastos/', FacturaReporteGastosView.as_view(), name='factura-reporte-gastos'),
    path('api/facturas/exportar-excel/', FacturaExportExcelView.as_view(), name='factura-exportar-excel'),
    path('api/facturas/exportar-csv/', FacturaExportCSVView.as_view(), name='factura-exportar-csv'),
    path('api/ingresos/exportar-csv/', IngresoExportCSVView.as_view(), name='ingreso-exportar-csv'),
    path('api/facturas/<int:pk>/', FacturaDetailView.as_view(), name='factura-detail'),

    # ── API Ingresos ✅ NUEVO ─────────────────────────────
    path('api/ingresos/', IngresoListCreateView.as_view(), name='ingreso-list'),
    path('api/ingresos/<int:pk>/', IngresoDetailView.as_view(), name='ingreso-detail'),

    # ── API Dashboard ✅ NUEVO ────────────────────────────
    path('api/dashboard/', DashboardView.as_view(), name='dashboard'),

    # ── API Usuarios ✅ NUEVO ─────────────────────────────
    path('api/usuarios/', UsuarioListView.as_view(), name='usuario-list'),

    path('reporte/', reporte_view, name='reporte'),
    path('api/reporte/', ReporteDashboardView.as_view(), name='api-reporte'),

    # ── Google Sheets ─────────────────────────────────────────────
    path('sheets/debug/',        sheets_debug,       name='sheets-debug'),
    path('sheets/conectar/',     sheets_conectar,    name='sheets-conectar'),
    path('sheets/callback/',     sheets_callback,    name='sheets-callback'),
    path('sheets/desconectar/',  sheets_desconectar, name='sheets-desconectar'),
    path('api/sheets/config/',   SheetsConfigView.as_view(),       name='sheets-config'),
    path('api/sheets/sincronizar/', SheetsSincronizarView.as_view(), name='sheets-sincronizar'),

    # ── Contador — Frontend ───────────────────────────────
    path('contador-dashboard/', contador_dashboard_view, name='contador-dashboard'),

    # ── Contador — API ────────────────────────────────────
    path('api/contador/usuarios/', ContadorUsuariosListCreateView.as_view(), name='contador-usuarios'),
    path('api/contador/usuarios/<int:pk>/', ContadorUsuariosDetailView.as_view(), name='contador-usuario-detail'),
    path('api/contador/usuarios/<int:pk>/bloquear/', ContadorUsuariosBloquearView.as_view(), name='contador-usuario-bloquear'),
    path('api/contador/facturas/', ContadorFacturasCreateView.as_view(), name='contador-facturas'),
    path('api/contador/ingresos/', ContadorIngresosCreateView.as_view(), name='contador-ingresos'),
    path('api/contador/transacciones/', ContadorTransaccionesListView.as_view(), name='contador-transacciones'),
    path('api/contador/dashboard/', ContadorDashboardView.as_view(), name='contador-dashboard-api'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)