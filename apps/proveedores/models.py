from decimal import Decimal
from django.db import models
from apps.core.choices import EstadoFacturaChoices


class Proveedor(models.Model):
    nombre = models.CharField(max_length=200)
    identificacion = models.CharField(max_length=30, unique=True, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.CharField(max_length=250, blank=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class FacturaProveedor(models.Model):
    obra = models.ForeignKey(
        'obras.Obra',
        on_delete=models.PROTECT,
        related_name='facturas_proveedores',
    )
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name='facturas_proveedores',
    )
    gasto = models.OneToOneField(
        'finanzas.GastoObra',
        on_delete=models.PROTECT,
        related_name='factura_proveedor',
    )
    folio = models.CharField(max_length=50)
    fecha_emision = models.DateField()
    impuesto = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    total = models.DecimalField(max_digits=14, decimal_places=2)
    estado = models.CharField(
        max_length=20,
        choices=EstadoFacturaChoices.choices,
        default=EstadoFacturaChoices.PENDIENTE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Factura de Proveedor'
        verbose_name_plural = 'Facturas de Proveedores'
        ordering = ['-fecha_emision', '-id']
        unique_together = [('proveedor', 'folio')]

    def __str__(self):
        return f'{self.proveedor_id} - {self.folio}'

    @property
    def subtotal(self) -> Decimal:
        """Suma del subtotal de las líneas de detalle."""
        total = Decimal('0.00')
        for d in self.detalles_factura.all():
            total += (d.subtotal or Decimal('0.00'))
        return total

    def total_calculado(self) -> Decimal:
        """total esperado = subtotal_detalles + impuesto."""
        return (self.subtotal or Decimal('0.00')) + (self.impuesto or Decimal('0.00'))

    def es_consistente(self) -> bool:
        """True si el campo `total` coincide con suma(detalles) + impuesto."""
        return self.total == self.total_calculado()


class DetalleFactura(models.Model):
    """Línea de detalle de la factura.

    Regla de la spec: DetalleFactura referencia OBLIGATORIAMENTE a Material.
    """
    factura = models.ForeignKey(
        FacturaProveedor,
        on_delete=models.CASCADE,
        related_name='detalles_factura',
    )
    material = models.ForeignKey(
        'inventario.Material',
        on_delete=models.PROTECT,
        related_name='detalles_factura',
    )
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = 'Detalle de Factura'
        verbose_name_plural = 'Detalles de Factura'
        ordering = ['id']

    def __str__(self):
        return f'{self.factura_id} - {self.material_id}'

    @property
    def subtotal(self):
        return (self.cantidad or 0) * (self.precio_unitario or 0)