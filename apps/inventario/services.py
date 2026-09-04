"""Servicios transaccionales para movimientos de inventario.

Reglas de la spec:
- MovimientoMaterial es HISTORIAL.
- InventarioObra es ESTADO ACTUAL.
- La consistencia se mantiene mediante operaciones EXPLÍCITAS y atómicas.
- NO hay lógica dentro de save() de MovimientoMaterial.
- NO se permite stock negativo.

Reglas de costo (MVP):
- `costo_unitario_promedio` se calcula con promedio ponderado simple
  en cada ENTRADA / DEVOLUCION / TRANSFERENCIA-in.
- `costo_total = cantidad_actual × costo_unitario_promedio`.
- En SALIDA / TRANSFERENCIA-out / AJUSTE el costo unitario se mantiene.
- En AJUSTE a una cantidad fija, `costo_unitario_promedio` se preserva.
"""
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError

from apps.core.choices import TipoMovimientoMaterialChoices
from .models import Material, InventarioObra, MovimientoMaterial


class StockInsuficienteError(ValidationError):
    """Salida solicitada excede el stock actual de la obra."""


def _get_or_create_inventario(obra, material):
    inv, _ = InventarioObra.objects.get_or_create(
        obra=obra,
        material=material,
        defaults={
            'cantidad_actual': Decimal('0.00'),
            'costo_unitario_promedio': Decimal('0.00'),
            'costo_total': Decimal('0.00'),
        },
    )
    return inv


def _validar_cantidad_positiva(cantidad):
    if cantidad is None or cantidad <= Decimal('0'):
        raise ValidationError({'cantidad': 'La cantidad debe ser mayor a 0.'})


def _validar_stock_suficiente(inventario, cantidad_a_restar):
    """Lanza StockInsuficienteError si no hay stock suficiente."""
    if inventario.cantidad_actual < cantidad_a_restar:
        raise StockInsuficienteError(
            f'Stock insuficiente en obra {inventario.obra_id} '
            f'para material {inventario.material_id}: '
            f'disponible {inventario.cantidad_actual}, solicitado {cantidad_a_restar}.'
        )


def _actualizar_costo_promedio(inventario, cantidad_entrada, costo_unitario_entrada):
    """Recalcula costo_unitario_promedio con promedio ponderado.

    Si costo_unitario_entrada es 0 o None, se preserva el promedio anterior.
    NOTA: este helper debe llamarse ANTES de incrementar
    `inventario.cantidad_actual`, para que use la cantidad anterior
    al recalcular el promedio.
    """
    cantidad_actual = inventario.cantidad_actual or Decimal('0.00')
    promedio_actual = inventario.costo_unitario_promedio or Decimal('0.00')

    if costo_unitario_entrada is None or costo_unitario_entrada <= Decimal('0'):
        # Sin info de costo, no recalculamos promedio
        return

    nueva_cantidad = cantidad_actual + cantidad_entrada
    if nueva_cantidad > 0:
        nuevo_promedio = (
            (cantidad_actual * promedio_actual) + (cantidad_entrada * costo_unitario_entrada)
        ) / nueva_cantidad
        inventario.costo_unitario_promedio = nuevo_promedio
    # Si la nueva cantidad es 0, mantenemos el promedio anterior


def _recalcular_costo_total(inventario):
    inventario.costo_total = (
        (inventario.cantidad_actual or Decimal('0.00'))
        * (inventario.costo_unitario_promedio or Decimal('0.00'))
    )


def _guardar_inventario(inventario):
    _recalcular_costo_total(inventario)
    inventario.save()


def _aplicar_entrada(inv, cantidad, costo_unitario):
    """Aplica una entrada al inventario recalculando el promedio.

    IMPORTANTE: el promedio se calcula ANTES de modificar la cantidad
    para que use el stock previo.
    """
    _actualizar_costo_promedio(inv, cantidad, costo_unitario)
    inv.cantidad_actual = (inv.cantidad_actual or Decimal('0.00')) + cantidad
    _guardar_inventario(inv)


@transaction.atomic
def registrar_entrada_material(*, obra, material, cantidad, usuario,
                                fecha, referencia='', observaciones='',
                                costo_unitario=None):
    """Registra una entrada y actualiza el inventario."""
    _validar_cantidad_positiva(cantidad)
    inv = _get_or_create_inventario(obra, material)
    _aplicar_entrada(inv, cantidad, costo_unitario)
    return MovimientoMaterial.objects.create(
        obra=obra,
        material=material,
        usuario=usuario,
        tipo=TipoMovimientoMaterialChoices.ENTRADA,
        cantidad=cantidad,
        fecha=fecha,
        obra_origen=obra,
        referencia=referencia,
        observaciones=observaciones,
    )


@transaction.atomic
def registrar_salida_material(*, obra, material, cantidad, usuario,
                               fecha, referencia='', observaciones=''):
    """Registra una salida. Falla si el stock es insuficiente.

    Atomicidad garantizada: si la validación falla, NO se crea el
    MovimientoMaterial NI se modifica el stock.
    """
    _validar_cantidad_positiva(cantidad)
    inv = _get_or_create_inventario(obra, material)
    _validar_stock_suficiente(inv, cantidad)
    inv.cantidad_actual = (inv.cantidad_actual or Decimal('0.00')) - cantidad
    _guardar_inventario(inv)
    return MovimientoMaterial.objects.create(
        obra=obra,
        material=material,
        usuario=usuario,
        tipo=TipoMovimientoMaterialChoices.SALIDA,
        cantidad=cantidad,
        fecha=fecha,
        obra_origen=obra,
        referencia=referencia,
        observaciones=observaciones,
    )


@transaction.atomic
def registrar_devolucion_material(*, obra, material, cantidad, usuario,
                                   fecha, referencia='', observaciones='',
                                   costo_unitario=None):
    _validar_cantidad_positiva(cantidad)
    inv = _get_or_create_inventario(obra, material)
    _aplicar_entrada(inv, cantidad, costo_unitario)
    return MovimientoMaterial.objects.create(
        obra=obra,
        material=material,
        usuario=usuario,
        tipo=TipoMovimientoMaterialChoices.DEVOLUCION,
        cantidad=cantidad,
        fecha=fecha,
        obra_origen=obra,
        referencia=referencia,
        observaciones=observaciones,
    )


@transaction.atomic
def registrar_transferencia_material(*, obra_origen, obra_destino, material,
                                      cantidad, usuario, fecha,
                                      referencia='', observaciones='',
                                      costo_unitario=None):
    """Mueve material entre dos obras. Totalmente atómica.

    Valida stock en obra_origen. Si falla, ROLLBACK completo.
    Genera 2 MovimientoMaterial: uno SALIDA en origen, uno ENTRADA en destino.
    """
    if obra_origen.pk == obra_destino.pk:
        raise ValidationError(
            'obra_origen y obra_destino no pueden ser la misma obra.'
        )
    _validar_cantidad_positiva(cantidad)

    inv_origen = _get_or_create_inventario(obra_origen, material)
    _validar_stock_suficiente(inv_origen, cantidad)
    inv_destino = _get_or_create_inventario(obra_destino, material)

    # Salida en origen (no recalcula promedio, mantiene el costo)
    inv_origen.cantidad_actual = (inv_origen.cantidad_actual or Decimal('0.00')) - cantidad
    _guardar_inventario(inv_origen)

    # Entrada en destino
    _aplicar_entrada(inv_destino, cantidad, costo_unitario)

    # Generar los 2 movimientos con obra_origen y obra_destino explícitos
    MovimientoMaterial.objects.create(
        obra=obra_origen,
        material=material,
        usuario=usuario,
        tipo=TipoMovimientoMaterialChoices.TRANSFERENCIA,
        cantidad=cantidad,
        fecha=fecha,
        obra_origen=obra_origen,
        obra_destino=obra_destino,
        referencia=referencia,
        observaciones=f'TRANSFERENCIA SALIDA -> {obra_destino.id}. {observaciones}',
    )
    return MovimientoMaterial.objects.create(
        obra=obra_destino,
        material=material,
        usuario=usuario,
        tipo=TipoMovimientoMaterialChoices.TRANSFERENCIA,
        cantidad=cantidad,
        fecha=fecha,
        obra_origen=obra_origen,
        obra_destino=obra_destino,
        referencia=referencia,
        observaciones=f'TRANSFERENCIA ENTRADA <- {obra_origen.id}. {observaciones}',
    )


@transaction.atomic
def ajustar_inventario(*, obra, material, cantidad_final, usuario,
                        fecha, referencia='', observaciones='',
                        costo_unitario_promedio=None):
    """Ajusta la cantidad_actual al valor `cantidad_final`.

    Si la cantidad_final es negativa, falla.
    El `costo_unitario_promedio` se preserva por defecto, salvo que se
    pase explícitamente.
    """
    if cantidad_final is None or cantidad_final < Decimal('0'):
        raise ValidationError(
            {'cantidad_final': 'La cantidad final no puede ser negativa.'}
        )
    inv = _get_or_create_inventario(obra, material)
    inv.cantidad_actual = cantidad_final
    if costo_unitario_promedio is not None:
        inv.costo_unitario_promedio = costo_unitario_promedio
    _guardar_inventario(inv)
    return MovimientoMaterial.objects.create(
        obra=obra,
        material=material,
        usuario=usuario,
        tipo=TipoMovimientoMaterialChoices.AJUSTE,
        cantidad=cantidad_final,
        fecha=fecha,
        obra_origen=obra,
        referencia=referencia,
        observaciones=observaciones,
    )