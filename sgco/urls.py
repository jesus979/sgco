"""URL configuration for sgco project."""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),

    # Auth: login con plantilla personalizada
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # App principal
    path('', include('apps.dashboard.urls')),
    path('obras/', include('apps.obras.urls')),
    path('fondos/', include('apps.fondos.urls')),
    path('finanzas/', include('apps.finanzas.urls')),
    path('proveedores/', include('apps.proveedores.urls')),
    path('inventario/', include('apps.inventario.urls')),
    path('personal/', include('apps.personal.urls')),
    path('maquinaria/', include('apps.maquinaria.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)