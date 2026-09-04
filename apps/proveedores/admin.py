from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import Proveedor, FacturaProveedor, DetalleFactura


@admin.register(Proveedor)
class ProveedorAdmin(ModelAdmin):
    list_display = ('nombre', 'identificacion', 'telefono', 'email', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre', 'identificacion')
    ordering = ('nombre',)
    list_filter_submit = True


@admin.register(FacturaProveedor)
class FacturaProveedorAdmin(ModelAdmin):
    list_display = ('folio', 'obra', 'proveedor', 'fecha_emision',
                    'mostrar_impuesto', 'mostrar_total', 'mostrar_estado')
    list_filter = ('estado', 'fecha_emision', 'proveedor')
    search_fields = ('folio', 'obra__nombre', 'proveedor__nombre')
    autocomplete_fields = ('obra', 'proveedor', 'gasto')
    date_hierarchy = 'fecha_emision'
    readonly_fields = ('created_at', 'updated_at')
    list_filter_submit = True

    @display(description='Impuesto', ordering='impuesto')
    def mostrar_impuesto(self, obj):
        return f'${obj.impuesto:,.2f}'

    @display(description='Total', ordering='total')
    def mostrar_total(self, obj):
        return f'${obj.total:,.2f}'

    @display(description='Estado',
             label={'PENDIENTE': 'danger', 'PARCIAL': 'warning', 'PAGADO': 'success'})
    def mostrar_estado(self, obj):
        return obj.get_estado_display()


@admin.register(DetalleFactura)
class DetalleFacturaAdmin(ModelAdmin):
    list_display = ('factura', 'material', 'cantidad', 'precio_unitario', 'mostrar_subtotal')
    list_filter = ('material',)
    search_fields = ('factura__folio', 'material__nombre')
    autocomplete_fields = ('factura', 'material')
    list_filter_submit = True

    @display(description='Subtotal')
    def mostrar_subtotal(self, obj):
        return f'${obj.subtotal:,.2f}'