from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from apps.core.choices import EstadoObraChoices, MonedaChoices


class Obra(models.Model):
    """Obra / proyecto de construcción.

    Campos derivados (NO editables):
    - total_asignado
    - total_gastado
    - saldo
    - porcentaje_ejecucion
    Se calculan en `apps.finanzas.services`.
    """
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    ubicacion = models.CharField(max_length=200)
    fecha_inicio = models.DateField()
    fecha_fin_estimada = models.DateField()
    estado = models.CharField(
        max_length=20,
        choices=EstadoObraChoices.choices,
        default=EstadoObraChoices.PLANIFICACION,
    )
    moneda = models.CharField(
        max_length=3,
        choices=MonedaChoices.choices,
        default=MonedaChoices.MXN,
    )
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Obra'
        verbose_name_plural = 'Obras'
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'

    def clean(self):
        super().clean()
        if self.fecha_fin_estimada and self.fecha_inicio:
            if self.fecha_fin_estimada < self.fecha_inicio:
                raise ValidationError(
                    {'fecha_fin_estimada': 'La fecha de fin estimada no puede ser anterior al inicio.'}
                )