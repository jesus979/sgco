from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import Material, InventarioObra, MovimientoMaterial


@admin.register(Material)
class MaterialAdmin(ModelAdmin):
    list_display = ('nombre', 'unidad', 'categoria', 'mostrar_precio', 'activo')
    list_filter = ('activo', 'unidad', 'categoria')
    search_fields = ('nombre', 'categoria')
    list_filter_submit = True

    @display(description='Precio ref.', ordering='precio_unitario_referencia')
    def mostrar_precio(self, obj):
        return f'${obj.precio_unitario_referencia:,.2f}'


@admin.register(InventarioObra)
class InventarioObraAdmin(ModelAdmin):
    list_display = ('obra', 'material', 'cantidad_actual', 'updated_at')
    list_filter = ('obra', 'material')
    search_fields = ('obra__nombre', 'material__nombre')
    autocomplete_fields = ('obra', 'material')
    readonly_fields = ('updated_at',)


@admin.register(MovimientoMaterial)
class MovimientoMaterialAdmin(ModelAdmin):
    list_display = ('fecha', 'obra', 'material', 'tipo', 'cantidad', 'usuario')
    list_filter = ('tipo', 'fecha', 'obra')
    search_fields = ('material__nombre', 'referencia')
    autocomplete_fields = ('obra', 'material', 'usuario')
    date_hierarchy = 'fecha'
    readonly_fields = ('created_at',)