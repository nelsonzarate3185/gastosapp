from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from facturas.views import FacturaUploadView, FacturaListView, FacturaDetailView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/facturas/', FacturaListView.as_view(), name='factura-list'),
    path('api/facturas/subir/', FacturaUploadView.as_view(), name='factura-upload'),
    path('api/facturas/<int:pk>/', FacturaDetailView.as_view(), name='factura-detail'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)   