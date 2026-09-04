from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import AsignacionFondo


@admin.register(AsignacionFondo)
class AsignacionFondoAdmin(ModelAdmin):
    list_display = ('obra', 'fecha', 'tipo', 'mostrar_monto', 'referencia', 'anulada')
    list_filter = ('tipo', 'fecha', 'obra', 'anulada')
    search_fields = ('obra__nombre', 'referencia')
    autocomplete_fields = ('obra',)
    date_hierarchy = 'fecha'
    readonly_fields = ('created_at', 'updated_at')
    list_filter_submit = True

    @display(description='Monto', ordering='monto')
    def mostrar_monto(self, obj):
        return f'${obj.monto:,.2f}'