"""Servicios transaccionales para movimientos de inventario.

Regla de la spec:
- MovimientoMaterial es HISTORIAL.
- InventarioObra es ESTADO ACTUAL.
- La consistencia debe mantenerse mediante operaciones EXPLÍCITAS y atómicas.

NO hay lógica dentro de save() de MovimientoMaterial.
"""
from decimal import Decimal
from django.db import transaction
from apps.core.choices import TipoMovimientoMaterialChoices
from .models import Material, InventarioObra, MovimientoMaterial


def _get_or_create_inventario(obra, material):
    inv, _ = InventarioObra.objects.get_or_create(
        obra=obra,
        material=material,
        defaults={'cantidad_actual': Decimal('0.00')},
    )
    return inv


def _aplicar_a_inventario(inv, tipo: str, cantidad: Decimal):
    if tipo == TipoMovimientoMaterialChoices.ENTRADA:
        inv.cantidad_actual = (inv.cantidad_actual or Decimal('0.00')) + cantidad
    elif tipo == TipoMovimientoMaterialChoices.SALIDA:
        inv.cantidad_actual = (inv.cantidad_actual or Decimal('0.00')) - cantidad
    elif tipo == TipoMovimientoMaterialChoices.DEVOLUCION:
        inv.cantidad_actual = (inv.cantidad_actual or Decimal('0.00')) + cantidad
    elif tipo == TipoMovimientoMaterialChoices.TRANSFERENCIA:
        inv.cantidad_actual = (inv.cantidad_actual or Decimal('0.00')) - cantidad
    elif tipo == TipoMovimientoMaterialChoices.AJUSTE:
        inv.cantidad_actual = cantidad
    inv.save()


@transaction.atomic
def registrar_entrada_material(*, obra, material, cantidad, usuario,
                                fecha, referencia='', observaciones=''):
    """Registra una entrada y actualiza el inventario."""
    inv = _get_or_create_inventario(obra, material)
    _aplicar_a_inventario(inv, TipoMovimientoMaterialChoices.ENTRADA, cantidad)
    return MovimientoMaterial.objects.create(
        obra=obra,
        material=material,
        usuario=usuario,
        tipo=TipoMovimientoMaterialChoices.ENTRADA,
        cantidad=cantidad,
        fecha=fecha,
        referencia=referencia,
        observaciones=observaciones,
    )


@transaction.atomic
def registrar_salida_material(*, obra, material, cantidad, usuario,
                               fecha, referencia='', observaciones=''):
    inv = _get_or_create_inventario(obra, material)
    _aplicar_a_inventario(inv, TipoMovimientoMaterialChoices.SALIDA, cantidad)
    return MovimientoMaterial.objects.create(
        obra=obra,
        material=material,
        usuario=usuario,
        tipo=TipoMovimientoMaterialChoices.SALIDA,
        cantidad=cantidad,
        fecha=fecha,
        referencia=referencia,
        observaciones=observaciones,
    )


@transaction.atomic
def registrar_devolucion_material(*, obra, material, cantidad, usuario,
                                   fecha, referencia='', observaciones=''):
    inv = _get_or_create_inventario(obra, material)
    _aplicar_a_inventario(inv, TipoMovimientoMaterialChoices.DEVOLUCION, cantidad)
    return MovimientoMaterial.objects.create(
        obra=obra,
        material=material,
        usuario=usuario,
        tipo=TipoMovimientoMaterialChoices.DEVOLUCION,
        cantidad=cantidad,
        fecha=fecha,
        referencia=referencia,
        observaciones=observaciones,
    )


@transaction.atomic
def registrar_transferencia_material(*, obra_origen, obra_destino, material,
                                      cantidad, usuario, fecha,
                                      referencia='', observaciones=''):
    """Mueve material entre dos obras."""
    inv_origen = _get_or_create_inventario(obra_origen, material)
    inv_destino = _get_or_create_inventario(obra_destino, material)
    _aplicar_a_inventario(inv_origen, TipoMovimientoMaterialChoices.SALIDA, cantidad)
    _aplicar_a_inventario(inv_destino, TipoMovimientoMaterialChoices.ENTRADA, cantidad)
    MovimientoMaterial.objects.create(
        obra=obra_origen,
        material=material,
        usuario=usuario,
        tipo=TipoMovimientoMaterialChoices.TRANSFERENCIA,
        cantidad=cantidad,
        fecha=fecha,
        referencia=referencia,
        observaciones=f'TRANSFERENCIA SALIDA -> {obra_destino_id_or_nombre(obra_destino)}. {observaciones}',
    )
    return MovimientoMaterial.objects.create(
        obra=obra_destino,
        material=material,
        usuario=usuario,
        tipo=TipoMovimientoMaterialChoices.TRANSFERENCIA,
        cantidad=cantidad,
        fecha=fecha,
        referencia=referencia,
        observaciones=f'TRANSFERENCIA ENTRADA <- {obra_origen_id_or_nombre(obra_origen)}. {observaciones}',
    )


def obra_destino_id_or_nombre(obra):
    return str(obra.id)


def obra_origen_id_or_nombre(obra):
    return str(obra.id)


@transaction.atomic
def ajustar_inventario(*, obra, material, cantidad_final, usuario,
                        fecha, referencia='', observaciones=''):
    inv = _get_or_create_inventario(obra, material)
    _aplicar_a_inventario(inv, TipoMovimientoMaterialChoices.AJUSTE, cantidad_final)
    return MovimientoMaterial.objects.create(
        obra=obra,
        material=material,
        usuario=usuario,
        tipo=TipoMovimientoMaterialChoices.AJUSTE,
        cantidad=cantidad_final,
        fecha=fecha,
        referencia=referencia,
        observaciones=observaciones,
    )