from django.urls import path
from . import views

app_name = 'proveedores'

urlpatterns = [
    path('', views.ProveedorListView.as_view(), name='proveedor_list'),
    path('nuevo/', views.ProveedorCreateView.as_view(), name='proveedor_create'),
    path('<int:pk>/', views.ProveedorDetailView.as_view(), name='proveedor_detail'),
    path('<int:pk>/editar/', views.ProveedorUpdateView.as_view(), name='proveedor_update'),
    path('<int:pk>/eliminar/', views.ProveedorDeleteView.as_view(), name='proveedor_delete'),

    path('facturas/', views.FacturaListView.as_view(), name='factura_list'),
    path('facturas/nueva/', views.FacturaCreateView.as_view(), name='factura_create'),
    path('facturas/<int:pk>/', views.FacturaDetailView.as_view(), name='factura_detail'),
    path('facturas/<int:pk>/editar/', views.FacturaUpdateView.as_view(), name='factura_update'),
    # v1.2: NO existe ruta de borrado para factura (debe anularse el gasto).

    path('facturas/detalles/', views.DetalleFacturaListView.as_view(), name='detalle_list'),
    path('facturas/detalles/nuevo/', views.DetalleFacturaCreateView.as_view(), name='detalle_create'),
    path('facturas/detalles/<int:pk>/editar/', views.DetalleFacturaUpdateView.as_view(), name='detalle_update'),
    path('facturas/detalles/<int:pk>/eliminar/', views.DetalleFacturaDeleteView.as_view(), name='detalle_delete'),
]
