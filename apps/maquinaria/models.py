from django.db import models
from decimal import Decimal


class Maquinaria(models.Model):
    nombre = models.CharField(max_length=150)
    marca = models.CharField(max_length=100, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    identificacion = models.CharField(max_length=50, blank=True)
    costo_hora = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Maquinaria'
        verbose_name_plural = 'Maquinarias'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class UsoMaquinaria(models.Model):
    obra = models.ForeignKey(
        'obras.Obra',
        on_delete=models.PROTECT,
        related_name='usos_maquinaria',
    )
    maquinaria = models.ForeignKey(
        Maquinaria,
        on_delete=models.PROTECT,
        related_name='usos_maquinaria',
    )
    gasto = models.OneToOneField(
        'finanzas.GastoObra',
        on_delete=models.PROTECT,
        related_name='uso_maquinaria',
    )
    fecha = models.DateField()
    horas = models.DecimalField(max_digits=8, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Uso de Maquinaria'
        verbose_name_plural = 'Usos de Maquinaria'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f'{self.obra_id} - {self.maquinaria_id} - {self.fecha}'