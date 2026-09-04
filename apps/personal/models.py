from django.db import models
from decimal import Decimal


class Empleado(models.Model):
    """Datos mínimos según especificación.

    No incluir aún: tipo_empleado, contrato, prestaciones, vacaciones,
    deducciones, etc.
    """
    cedula = models.CharField(max_length=20, unique=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    cargo = models.CharField(max_length=100)
    salario_diario = models.DecimalField(max_digits=10, decimal_places=2)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'
        ordering = ['apellidos', 'nombres']

    def __str__(self):
        return f'{self.nombres} {self.apellidos}'.strip()

    @property
    def nombre_completo(self) -> str:
        return self.__str__()


class Nomina(models.Model):
    obra = models.ForeignKey(
        'obras.Obra',
        on_delete=models.PROTECT,
        related_name='nominas',
    )
    gasto = models.OneToOneField(
        'finanzas.GastoObra',
        on_delete=models.PROTECT,
        related_name='nomina',
    )
    fecha = models.DateField()
    periodo_desde = models.DateField()
    periodo_hasta = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Nómina'
        verbose_name_plural = 'Nóminas'
        ordering = ['-periodo_desde', '-id']
        unique_together = [('obra', 'periodo_desde', 'periodo_hasta')]

    def __str__(self):
        return f'{self.obra_id} - {self.periodo_desde} / {self.periodo_hasta}'


class NominaDetalle(models.Model):
    """Línea de detalle de la nómina por empleado.

    Sin lógica en save(): el total se calcula mediante servicio explícito.
    """
    nomina = models.ForeignKey(
        Nomina,
        on_delete=models.CASCADE,
        related_name='nominas_detalle',
    )
    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.PROTECT,
        related_name='nominas_detalle',
    )
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Detalle de Nómina'
        verbose_name_plural = 'Detalles de Nómina'
        unique_together = [('nomina', 'empleado')]
        ordering = ['id']

    def __str__(self):
        return f'{self.nomina_id} - {self.empleado_id}'