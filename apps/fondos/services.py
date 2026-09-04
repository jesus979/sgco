"""Servicios transaccionales para AsignacionFondo.

Regla de la spec: no borrar físicamente operaciones financieras.
"""
from django.db import transaction


@transaction.atomic
def anular_asignacion(asignacion):
    """Marca la asignación como anulada (sin borrado físico)."""
    if asignacion.anulada:
        return asignacion
    asignacion.anulada = True
    asignacion.save(update_fields=['anulada', 'updated_at'])
    return asignacion