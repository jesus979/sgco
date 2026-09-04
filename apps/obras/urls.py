from django.urls import path
from . import views

app_name = 'obras'

urlpatterns = [
    path('', views.ObraListView.as_view(), name='list'),
    path('nueva/', views.ObraCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ObraDetailView.as_view(), name='detail'),
    path('<int:pk>/editar/', views.ObraUpdateView.as_view(), name='update'),
    path('<int:pk>/eliminar/', views.ObraDeleteView.as_view(), name='delete'),
    path('<int:pk>/reporte/', views.ObraReportePDFView.as_view(), name='reporte'),
]