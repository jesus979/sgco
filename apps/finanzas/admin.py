from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import GastoObra, OtroGasto
from apps.core.choices import EstadoGastoChoices
from .services import anular_gasto


@admin.register(GastoObra)
class GastoObraAdmin(ModelAdmin):
    list_display = ('fecha', 'obra', 'tipo_gasto', 'descripcion',
                    'mostrar_monto', 'mostrar_estado')
    list_filter = ('estado', 'tipo_gasto', 'fecha', 'obra')
    search_fields = ('obra__nombre', 'descripcion')
    autocomplete_fields = ('obra',)
    date_hierarchy = 'fecha'
    readonly_fields = ('created_at', 'updated_at')
    list_filter_submit = True

    actions = ['anular_gasto_action']

    @display(description='Monto', ordering='monto')
    def mostrar_monto(self, obj):
        return f'${obj.monto:,.2f}'

    @display(description='Estado',
             label={'BORRADOR': 'warning', 'APROBADO': 'success', 'ANULADO': 'danger'})
    def mostrar_estado(self, obj):
        return obj.get_estado_display()

    @admin.action(description='Anular gastos seleccionados')
    def anular_gasto_action(self, request, queryset):
        qs = queryset.exclude(estado=EstadoGastoChoices.ANULADO)
        for g in qs:
            anular_gasto(g)
        self.message_user(request, f'{qs.count()} gastos anulados.')


@admin.register(OtroGasto)
class OtroGastoAdmin(ModelAdmin):
    list_display = ('fecha', 'obra', 'concepto', 'comprobante', 'proveedor', 'gasto')
    list_filter = ('fecha', 'obra')
    search_fields = ('concepto', 'comprobante', 'obra__nombre')
    autocomplete_fields = ('obra', 'gasto', 'proveedor')
    date_hierarchy = 'fecha'
    readonly_fields = ('created_at', 'updated_at')