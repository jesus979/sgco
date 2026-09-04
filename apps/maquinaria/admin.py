from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import Maquinaria, UsoMaquinaria


@admin.register(Maquinaria)
class MaquinariaAdmin(ModelAdmin):
    list_display = ('nombre', 'marca', 'modelo', 'identificacion',
                    'mostrar_costo_hora', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre', 'identificacion', 'marca', 'modelo')
    list_filter_submit = True

    @display(description='Costo/hora', ordering='costo_hora')
    def mostrar_costo_hora(self, obj):
        return f'${obj.costo_hora:,.2f}'


@admin.register(UsoMaquinaria)
class UsoMaquinariaAdmin(ModelAdmin):
    list_display = ('obra', 'maquinaria', 'fecha', 'horas', 'mostrar_monto')
    list_filter = ('obra', 'maquinaria', 'fecha')
    search_fields = ('obra__nombre', 'maquinaria__nombre')
    autocomplete_fields = ('obra', 'maquinaria', 'gasto')
    date_hierarchy = 'fecha'
    list_filter_submit = True

    @display(description='Costo total', ordering='gasto__monto')
    def mostrar_monto(self, obj):
        return f'${obj.gasto.monto:,.2f}'