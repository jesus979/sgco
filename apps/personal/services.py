"""Servicios para el dominio de personal/nómina.

Regla: NO usar lógica en save() de NominaDetalle.
El total se calcula explícitamente con recalcular_total_nomina().
"""
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum


@transaction.atomic
def recalcular_total_nomina(nomina):
    """Recalcula el total de la nómina a partir de la suma de sus detalles.

    No aplica efectos secundarios sobre otros modelos.
    """
    total = nomina.nominas_detalle.aggregate(s=Sum('monto'))['s'] or Decimal('0.00')
    nomina.gasto.monto = total
    nomina.gasto.save(update_fields=['monto', 'updated_at'])
    return total