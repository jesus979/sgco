"""Servicios transaccionales para Proveedores y Facturas.

Reglas:
- DetalleFactura NO tiene save() con efectos secundarios.
- La consistencia FacturaProveedor.total = suma(subtotal_detalle) + impuesto
  se valida explícitamente mediante los servicios de este módulo.
"""
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError


@transaction.atomic
def registrar_detalle_factura(*, factura, material, cantidad, precio_unitario):
    """Agrega un DetalleFactura y devuelve el subtotal de la línea.

    No modifica FacturaProveedor.total automáticamente. La consistencia
    se verifica al invocar `verificar_consistencia_factura`.
    """
    from .models import DetalleFactura

    return DetalleFactura.objects.create(
        factura=factura,
        material=material,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
    )


@transaction.atomic
def actualizar_total_desde_detalles(factura):
    """Recalcula FacturaProveedor.total a partir de los detalles + impuesto.

    Útil tras agregar / modificar líneas de detalle.
    """
    factura.total = factura.subtotal + (factura.impuesto or Decimal('0.00'))
    factura.save(update_fields=['total', 'updated_at'])
    return factura.total


def verificar_consistencia_factura(factura) -> bool:
    """True si total == suma(subtotal_detalle) + impuesto."""
    return factura.total == factura.total_calculado()


def exigir_consistencia_factura(factura):
    """Lanza ValidationError si la factura no es consistente."""
    if not verificar_consistencia_factura(factura):
        raise ValidationError(
            f'Factura {factura.folio} inconsistente: '
            f'total={factura.total} vs calculado={factura.total_calculado()}'
        )