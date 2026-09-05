from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from apps.core.choices import TipoAsignacionFondoChoices


class AsignacionFondo(models.Model):
    """Asignación de fondo para una obra.

    Reglas de inmutabilidad (spec v1.2):
    Una vez registrada la asignación, NO se permite modificar
    silenciosamente los campos con impacto financiero:
    - obra
    - monto
    - tipo

    Para corregir una asignación, se debe:
    1) ANULAR la asignación (campo anulada=True)
    2) Crear una nueva asignación con los valores correctos

    Solo se permite editar:
    - referencia
    - observaciones
    """
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
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='asignaciones_creadas',
    )
    anulada = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Asignación de Fondo'
        verbose_name_plural = 'Asignaciones de Fondo'
        ordering = ['-fecha', '-id']
        indexes = [
            models.Index(fields=['obra', 'anulada']),
        ]

    def __str__(self):
        return f'{self.obra_id} - {self.tipo} - {self.monto}'

    def clean(self):
        super().clean()
        if self.monto is not None and self.monto <= 0:
            raise ValidationError({'monto': 'El monto debe ser mayor a 0.'})

    def save(self, *args, **kwargs):
        """Valida inmutabilidad de campos financieros al actualizar.

        Si el registro ya existe en BD y se intenta cambiar `obra`,
        `monto` o `tipo`, se lanza ValidationError para forzar al
        usuario a ANULAR + crear nueva asignación.
        """
        if self.pk is not None:
            try:
                original = AsignacionFondo.objects.get(pk=self.pk)
            except AsignacionFondo.DoesNotExist:
                original = None
            if original is not None:
                errors = {}
                if self.obra_id != original.obra_id:
                    errors['obra'] = (
                        'No se puede cambiar la obra de una asignación registrada. '
                        'Anule esta asignación y cree una nueva.'
                    )
                if self.monto != original.monto:
                    errors['monto'] = (
                        'No se puede modificar el monto de una asignación registrada. '
                        'Anule esta asignación y cree una nueva.'
                    )
                if self.tipo != original.tipo:
                    errors['tipo'] = (
                        'No se puede modificar el tipo de una asignación registrada. '
                        'Anule esta asignación y cree una nueva.'
                    )
                if errors:
                    raise ValidationError(errors)
        super().save(*args, **kwargs)

    @property
    def afecta_saldo(self) -> bool:
        return not self.anulada
