from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.core.choices import (
    TipoGastoChoices,
    EstadoGastoChoices,
    MonedaChoices,
)


class TipoDocumentoOrigenChoices(models.TextChoices):
    """Tipo de documento que origina el gasto.

    Permite identificar el documento asociado al GastoObra sin
    necesitar una FK redundante. La trazabilidad real se hace vía
    `related_name` del documento (factura_proveedor, nomina, etc.).
    """
    MANUAL = 'MANUAL', 'Manual'
    FACTURA = 'FACTURA', 'Factura de proveedor'
    NOMINA = 'NOMINA', 'Nómina'
    USO_MAQUINARIA = 'USO_MAQUINARIA', 'Uso de maquinaria'
    OTRO = 'OTRO', 'Otro'


class GastoObra(models.Model):
    """Representación financiera central del gasto en una obra.

    Regla: el proveedor NO vive aquí; se obtiene transitando por
    FacturaProveedor o por el documento origen.

    Invariantes:
    - estado ∈ {BORRADOR, APROBADO, ANULADO}
    - monto > 0
    - Solo APROBADO afecta el saldo
    - No se borra físicamente; se anula
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
    concepto = models.CharField(max_length=200, blank=True)
    descripcion = models.CharField(max_length=200, blank=True)
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    moneda = models.CharField(
        max_length=3,
        choices=MonedaChoices.choices,
        default=MonedaChoices.MXN,
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoGastoChoices.choices,
        default=EstadoGastoChoices.BORRADOR,
    )
    tipo_documento_origen = models.CharField(
        max_length=20,
        choices=TipoDocumentoOrigenChoices.choices,
        default=TipoDocumentoOrigenChoices.MANUAL,
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='gastos_creados',
    )
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Gasto de Obra'
        verbose_name_plural = 'Gastos de Obra'
        ordering = ['-fecha', '-id']
        indexes = [
            models.Index(fields=['obra', 'estado']),
            models.Index(fields=['estado']),
        ]

    def __str__(self):
        return f'{self.obra_id} - {self.tipo_gasto} - {self.monto}'

    def clean(self):
        super().clean()
        if self.monto is not None and self.monto <= Decimal('0'):
            raise ValidationError({'monto': 'El monto debe ser mayor a 0.'})
        if not self.usuario_id:
            raise ValidationError(
                {'usuario': 'El usuario responsable es obligatorio.'}
            )

    def save(self, *args, **kwargs):
        """Valida inmutabilidad de campos financieros en estados terminales.

        - BORRADOR: editable (todos los campos).
        - APROBADO: solo campos no financieros (concepto, descripcion,
          observaciones). obra/monto/tipo_gasto NO se pueden modificar.
        - ANULADO: inmutable. No se puede modificar nada.

        La operación correcta para corregir un gasto aprobado o
        anulado es: ANULAR + crear nuevo gasto.
        """
        if self.pk is not None:
            try:
                original = GastoObra.objects.get(pk=self.pk)
            except GastoObra.DoesNotExist:
                original = None
            if original is not None:
                if original.estado == EstadoGastoChoices.ANULADO:
                    raise ValidationError(
                        {'__all__': 'Un gasto ANULADO no se puede modificar.'}
                    )
                if original.estado == EstadoGastoChoices.APROBADO:
                    errors = {}
                    if self.obra_id != original.obra_id:
                        errors['obra'] = (
                            'No se puede cambiar la obra de un gasto APROBADO. '
                            'Anule el gasto y cree uno nuevo.'
                        )
                    if self.monto != original.monto:
                        errors['monto'] = (
                            'No se puede cambiar el monto de un gasto APROBADO. '
                            'Anule el gasto y cree uno nuevo.'
                        )
                    if self.tipo_gasto != original.tipo_gasto:
                        errors['tipo_gasto'] = (
                            'No se puede cambiar el tipo de un gasto APROBADO. '
                            'Anule el gasto y cree uno nuevo.'
                        )
                    if errors:
                        raise ValidationError(errors)
        super().save(*args, **kwargs)

    @property
    def es_borrador(self) -> bool:
        return self.estado == EstadoGastoChoices.BORRADOR

    @property
    def es_aprobado(self) -> bool:
        return self.estado == EstadoGastoChoices.APROBADO

    @property
    def es_anulado(self) -> bool:
        return self.estado == EstadoGastoChoices.ANULADO

    @property
    def es_editable_completo(self) -> bool:
        """En BORRADOR se puede editar todo."""
        return self.es_borrador

    @property
    def es_editable_solo_descriptivo(self) -> bool:
        """En APROBADO solo se pueden modificar campos descriptivos."""
        return self.es_aprobado

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

    def clean(self):
        super().clean()
        if self.gasto_id and self.obra_id and self.gasto.obra_id != self.obra_id:
            raise ValidationError(
                {'gasto': 'El GastoObra asociado debe pertenecer a la misma obra.'}
            )