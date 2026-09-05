from django.urls import path
from . import views

app_name = 'personal'

urlpatterns = [
    path('', views.EmpleadoListView.as_view(), name='empleado_list'),
    path('nuevo/', views.EmpleadoCreateView.as_view(), name='empleado_create'),
    path('<int:pk>/', views.EmpleadoDetailView.as_view(), name='empleado_detail'),
    path('<int:pk>/editar/', views.EmpleadoUpdateView.as_view(), name='empleado_update'),
    path('<int:pk>/eliminar/', views.EmpleadoDeleteView.as_view(), name='empleado_delete'),

    path('nominas/', views.NominaListView.as_view(), name='nomina_list'),
    path('nominas/nueva/', views.NominaCreateView.as_view(), name='nomina_create'),
    path('nominas/<int:pk>/', views.NominaDetailView.as_view(), name='nomina_detail'),
    path('nominas/<int:pk>/editar/', views.NominaUpdateView.as_view(), name='nomina_update'),
    path('nominas/<int:pk>/recalcular/', views.NominaRecalcularView.as_view(), name='nomina_recalcular'),
    path('nominas/<int:pk>/anular/', views.NominaAnularView.as_view(), name='nomina_anular'),
    # v1.2: NO existe ruta de borrado para nómina.
    # Para cancelar, usar 'anular' que marca el gasto como ANULADO.

    path('nominas/detalles/', views.NominaDetalleListView.as_view(), name='nomina_detalle_list'),
    path('nominas/detalles/nuevo/', views.NominaDetalleCreateView.as_view(), name='nomina_detalle_create'),
    path('nominas/detalles/<int:pk>/editar/', views.NominaDetalleUpdateView.as_view(), name='nomina_detalle_update'),
    path('nominas/detalles/<int:pk>/eliminar/', views.NominaDetalleDeleteView.as_view(), name='nomina_detalle_delete'),
]
