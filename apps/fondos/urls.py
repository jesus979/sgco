from django.urls import path
from . import views

app_name = 'fondos'

urlpatterns = [
    path('', views.AsignacionFondoListView.as_view(), name='list'),
    path('nueva/', views.AsignacionFondoCreateView.as_view(), name='create'),
    path('<int:pk>/editar/', views.AsignacionFondoUpdateView.as_view(), name='update'),
    path('<int:pk>/anular/', views.AsignacionFondoAnularView.as_view(), name='anular'),
]