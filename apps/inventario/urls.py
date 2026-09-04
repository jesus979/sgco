from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('materiales/', views.MaterialListView.as_view(), name='material_list'),
    path('materiales/nuevo/', views.MaterialCreateView.as_view(), name='material_create'),
    path('materiales/<int:pk>/', views.MaterialDetailView.as_view(), name='material_detail'),
    path('materiales/<int:pk>/editar/', views.MaterialUpdateView.as_view(), name='material_update'),
    path('materiales/<int:pk>/eliminar/', views.MaterialDeleteView.as_view(), name='material_delete'),

    path('inventarios/', views.InventarioListView.as_view(), name='inventario_list'),
    path('inventarios/<int:pk>/editar/', views.InventarioUpdateView.as_view(), name='inventario_update'),

    path('movimientos/', views.MovimientoListView.as_view(), name='movimiento_list'),
    path('movimientos/nuevo/', views.MovimientoCreateView.as_view(), name='movimiento_create'),
]