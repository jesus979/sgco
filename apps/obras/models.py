from django.db import models
from apps.core.choices import EstadoObraChoices


class Obra(models.Model):
    nombre = models.CharField(max_length=150)
    ubicacion = models.CharField(max_length=200)
    fecha_inicio = models.DateField()
    fecha_fin_estimada = models.DateField()
    estado = models.CharField(
        max_length=20,
        choices=EstadoObraChoices.choices,
        default=EstadoObraChoices.PLANIFICACION,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Obra'
        verbose_name_plural = 'Obras'
        ordering = ['-fecha_inicio']

    def __str__(self):
        return self.nombre