from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from facturas.views import (
    FacturaUploadView,
    FacturaListView,
    FacturaDetailView,
    FacturaConfirmarView,
    login_view,
    logout_view,
    home_view,
    exportar_excel,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_view, name='login'),
    path('home/', home_view, name='home'),
    path('logout/', logout_view, name='logout'),
    path('exportar/excel/', exportar_excel, name='exportar-excel'),
    path('api/facturas/', FacturaListView.as_view(), name='factura-list'),
    path('api/facturas/subir/', FacturaUploadView.as_view(), name='factura-upload'),
    path('api/facturas/confirmar/', FacturaConfirmarView.as_view(), name='factura-confirmar'),
    path('api/facturas/<int:pk>/', FacturaDetailView.as_view(), name='factura-detail'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)