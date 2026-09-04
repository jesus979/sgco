from django.db import models
from apps.core.choices import TipoGastoChoices, EstadoGastoChoices


class GastoObra(models.Model):
    """Representación financiera central del gasto en una obra.

    Regla: el proveedor NO vive aquí; se obtiene transitando por
    FacturaProveedor o por el documento origen.
    """
    obra = models.ForeignKey(
        'obras.Obra',
        on_delete=models.PROTECT,
        related_name='gastos_obra',
    )
    fecha = models.DateField()
    tipo_gasto = models.CharField(
        max_length=20,
        choices=TipoGastoChoices.choices,
        default=TipoGastoChoices.OTROS,
    )
    descripcion = models.CharField(max_length=200, blank=True)
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    estado = models.CharField(
        max_length=20,
        choices=EstadoGastoChoices.choices,
        default=EstadoGastoChoices.BORRADOR,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Gasto de Obra'
        verbose_name_plural = 'Gastos de Obra'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f'{self.obra_id} - {self.tipo_gasto} - {self.monto}'

    @property
    def afecta_saldo(self) -> bool:
        return self.estado == EstadoGastoChoices.APROBADO


class OtroGasto(models.Model):
    """Documento especializado para gastos sin origen específico en el sistema.

    El monto financiero pertenece a GastoObra.monto.
    Este modelo NO mantiene un monto propio.
    """
    obra = models.ForeignKey(
        'obras.Obra',
        on_delete=models.PROTECT,
        related_name='otros_gastos',
    )
    gasto = models.OneToOneField(
        GastoObra,
        on_delete=models.PROTECT,
        related_name='otro_gasto',
    )
    fecha = models.DateField()
    concepto = models.CharField(max_length=200)
    comprobante = models.CharField(max_length=100, blank=True)
    proveedor = models.ForeignKey(
        'proveedores.Proveedor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='otros_gastos',
    )
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Otro Gasto'
        verbose_name_plural = 'Otros Gastos'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f'{self.obra_id} - {self.concepto}'