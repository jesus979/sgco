from django.urls import path
from . import views

app_name = 'maquinaria'

urlpatterns = [
    path('', views.MaquinariaListView.as_view(), name='maquinaria_list'),
    path('nueva/', views.MaquinariaCreateView.as_view(), name='maquinaria_create'),
    path('<int:pk>/', views.MaquinariaDetailView.as_view(), name='maquinaria_detail'),
    path('<int:pk>/editar/', views.MaquinariaUpdateView.as_view(), name='maquinaria_update'),
    path('<int:pk>/eliminar/', views.MaquinariaDeleteView.as_view(), name='maquinaria_delete'),

    path('usos/', views.UsoListView.as_view(), name='uso_list'),
    path('usos/nuevo/', views.UsoCreateView.as_view(), name='uso_create'),
    path('usos/<int:pk>/editar/', views.UsoUpdateView.as_view(), name='uso_update'),
    path('usos/<int:pk>/anular/', views.UsoAnularView.as_view(), name='uso_anular'),
]