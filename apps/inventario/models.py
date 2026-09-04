from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
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
    """Estado actual del inventario de un material en una obra.

    Solo se modifica a través de servicios transaccionales explícitos
    (`apps.inventario.services`). NO se modifica en `MovimientoMaterial.save()`.
    """
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
    costo_unitario_promedio = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    costo_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Inventario de Obra'
        verbose_name_plural = 'Inventarios de Obra'
        unique_together = [('obra', 'material')]
        ordering = ['id']
        indexes = [
            models.Index(fields=['obra', 'material']),
        ]

    def __str__(self):
        return f'{self.obra_id} - {self.material_id}'

    def clean(self):
        super().clean()
        if self.cantidad_actual is not None and self.cantidad_actual < Decimal('0'):
            raise ValidationError(
                {'cantidad_actual': 'La cantidad actual no puede ser negativa.'}
            )


class MovimientoMaterial(models.Model):
    """Historial de movimientos. NO actualiza InventarioObra en save().

    Reglas:
    - `obra` representa la obra principal del movimiento (origen para
      transferencias).
    - Para TRANSFERENCIA se deben poblar `obra_origen` y `obra_destino`.
    - `obra_origen == obra` por defecto.
    - La consistencia con InventarioObra se mantiene mediante servicios
      transaccionales en `apps.inventario.services`.
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
    obra_origen = models.ForeignKey(
        'obras.Obra',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='movimientos_origen',
    )
    obra_destino = models.ForeignKey(
        'obras.Obra',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='movimientos_destino',
    )
    referencia = models.CharField(max_length=100, blank=True)
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Movimiento de Material'
        verbose_name_plural = 'Movimientos de Material'
        ordering = ['-fecha', '-id']
        indexes = [
            models.Index(fields=['obra', 'material', '-fecha']),
        ]

    def __str__(self):
        return f'{self.obra_id} - {self.material_id} - {self.tipo}'

    def clean(self):
        super().clean()
        if self.cantidad is not None and self.cantidad <= Decimal('0'):
            raise ValidationError({'cantidad': 'La cantidad debe ser mayor a 0.'})
        if self.tipo == TipoMovimientoMaterialChoices.TRANSFERENCIA:
            if not self.obra_origen_id or not self.obra_destino_id:
                raise ValidationError(
                    {'obra_origen': 'Una transferencia requiere obra_origen y obra_destino.'}
                )
            if self.obra_origen_id == self.obra_destino_id:
                raise ValidationError(
                    {'obra_destino': 'La obra destino no puede ser la misma que la obra origen.'}
                )
        else:
            # Para no-transferencias, obra_origen/obra_destino deben ser null
            # o coherentes con `obra`.
            if self.obra_origen_id and self.obra_origen_id != self.obra_id:
                raise ValidationError(
                    {'obra_origen': 'obra_origen debe coincidir con obra o ser null.'}
                )
            if self.obra_destino_id:
                raise ValidationError(
                    {'obra_destino': 'obra_destino solo aplica a transferencias.'}
                )