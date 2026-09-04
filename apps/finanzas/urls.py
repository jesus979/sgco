from django.urls import path
from . import views

app_name = 'finanzas'

urlpatterns = [
    path('gastos/', views.GastoObraListView.as_view(), name='gasto_list'),
    path('gastos/nuevo/', views.GastoObraCreateView.as_view(), name='gasto_create'),
    path('gastos/<int:pk>/', views.GastoObraDetailView.as_view(), name='gasto_detail'),
    path('gastos/<int:pk>/editar/', views.GastoObraUpdateView.as_view(), name='gasto_update'),
    path('gastos/<int:pk>/eliminar/', views.GastoObraDeleteView.as_view(), name='gasto_delete'),
    path('gastos/<int:pk>/anular/', views.GastoObraAnularView.as_view(), name='gasto_anular'),

    path('otros/', views.OtroGastoListView.as_view(), name='otro_list'),
    path('otros/nuevo/', views.OtroGastoCreateView.as_view(), name='otro_create'),
    path('otros/<int:pk>/editar/', views.OtroGastoUpdateView.as_view(), name='otro_update'),
    path('otros/<int:pk>/eliminar/', views.OtroGastoDeleteView.as_view(), name='otro_delete'),
    path('otros/<int:pk>/anular/', views.OtroGastoAnularView.as_view(), name='otro_anular'),
]