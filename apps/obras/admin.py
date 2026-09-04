from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import Obra
from apps.finanzas.services import total_asignado, total_gastado, saldo, porcentaje_ejecucion


@admin.register(Obra)
class ObraAdmin(ModelAdmin):
    list_display = ('nombre', 'ubicacion', 'estado', 'fecha_inicio',
                    'fecha_fin_estimada', 'mostrar_saldo')
    list_filter = ('estado', 'fecha_inicio', 'fecha_fin_estimada')
    search_fields = ('nombre', 'ubicacion')
    ordering = ('-fecha_inicio',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'fecha_inicio'
    list_display_links = ('nombre',)

    fieldsets = (
        ('Información general', {
            'fields': ('nombre', 'ubicacion')
        }),
        ('Fechas', {
            'fields': ('fecha_inicio', 'fecha_fin_estimada')
        }),
        ('Estado', {
            'fields': ('estado',)
        }),
        ('Auditoría', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )

    @display(description='Saldo', ordering='fecha_inicio')
    def mostrar_saldo(self, obj):
        return f'${saldo(obj):,.2f}'