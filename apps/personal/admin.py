from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display
from django.db.models import Sum
from .models import Empleado, Nomina, NominaDetalle


@admin.register(Empleado)
class EmpleadoAdmin(ModelAdmin):
    list_display = ('cedula', 'nombres', 'apellidos', 'cargo',
                    'mostrar_salario', 'activo')
    list_filter = ('activo', 'cargo')
    search_fields = ('cedula', 'nombres', 'apellidos', 'cargo')
    ordering = ('apellidos', 'nombres')
    list_filter_submit = True

    @display(description='Salario diario', ordering='salario_diario')
    def mostrar_salario(self, obj):
        return f'${obj.salario_diario:,.2f}'


@admin.register(Nomina)
class NominaAdmin(ModelAdmin):
    list_display = ('obra', 'fecha', 'periodo_desde', 'periodo_hasta',
                    'mostrar_monto_gasto')
    list_filter = ('obra', 'fecha')
    search_fields = ('obra__nombre',)
    autocomplete_fields = ('obra', 'gasto')
    date_hierarchy = 'fecha'
    list_filter_submit = True

    @display(description='Monto gasto', ordering='gasto__monto')
    def mostrar_monto_gasto(self, obj):
        return f'${obj.gasto.monto:,.2f}'


@admin.register(NominaDetalle)
class NominaDetalleAdmin(ModelAdmin):
    list_display = ('nomina', 'empleado', 'monto')
    list_filter = ('nomina__obra',)
    search_fields = ('empleado__cedula', 'empleado__nombres', 'empleado__apellidos')
    autocomplete_fields = ('nomina', 'empleado')
    list_filter_submit = True