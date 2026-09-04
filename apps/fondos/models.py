from django.db import models
from apps.core.choices import TipoAsignacionFondoChoices


class AsignacionFondo(models.Model):
    obra = models.ForeignKey(
        'obras.Obra',
        on_delete=models.PROTECT,
        related_name='asignaciones_fondo',
    )
    fecha = models.DateField()
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    tipo = models.CharField(
        max_length=20,
        choices=TipoAsignacionFondoChoices.choices,
        default=TipoAsignacionFondoChoices.INICIAL,
    )
    referencia = models.CharField(max_length=100, blank=True)
    observaciones = models.TextField(blank=True)
    anulada = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Asignación de Fondo'
        verbose_name_plural = 'Asignaciones de Fondo'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f'{self.obra_id} - {self.tipo} - {self.monto}'

    @property
    def afecta_saldo(self) -> bool:
        return not self.anulada