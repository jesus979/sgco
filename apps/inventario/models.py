from django.db import models
from decimal import Decimal
from apps.core.choices import TipoMovimientoMaterialChoices


class Material(models.Model):
    nombre = models.CharField(max_length=150)
    unidad = models.CharField(max_length=30)
    categoria = models.CharField(max_length=80)
    precio_unitario_referencia = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Material'
        verbose_name_plural = 'Materiales'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class InventarioObra(models.Model):
    """Estado actual del inventario de un material en una obra."""
    obra = models.ForeignKey(
        'obras.Obra',
        on_delete=models.PROTECT,
        related_name='inventarios_obra',
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name='inventarios_obra',
    )
    cantidad_actual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Inventario de Obra'
        verbose_name_plural = 'Inventarios de Obra'
        unique_together = [('obra', 'material')]
        ordering = ['id']

    def __str__(self):
        return f'{self.obra_id} - {self.material_id}'


class MovimientoMaterial(models.Model):
    """Historial de movimientos. NO actualiza InventarioObra en save().

    La consistencia con InventarioObra debe mantenerse mediante servicios
    transaccionales explícitos en apps.inventario.services.
    """
    obra = models.ForeignKey(
        'obras.Obra',
        on_delete=models.PROTECT,
        related_name='movimientos_material',
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.PROTECT,
        related_name='movimientos_material',
    )
    usuario = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='movimientos_material',
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoMovimientoMaterialChoices.choices,
    )
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateField()
    referencia = models.CharField(max_length=100, blank=True)
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Movimiento de Material'
        verbose_name_plural = 'Movimientos de Material'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f'{self.obra_id} - {self.material_id} - {self.tipo}'