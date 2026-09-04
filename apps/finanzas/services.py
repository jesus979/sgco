"""Servicios transaccionales para el dominio financiero.

Reglas:
- GastoObra es la representación financiera central (fuente de verdad del monto).
- FacturaProveedor, Nomina, UsoMaquinaria y OtroGasto generan un GastoObra
  en una sola transacción atómica.
- No usar borrado físico indiscriminado en operaciones financieras.
"""
from decimal import Decimal
from django.db import transaction
from apps.core.choices import (
    TipoGastoChoices,
    EstadoGastoChoices,
    EstadoFacturaChoices,
)
from apps.obras.models import Obra
from apps.proveedores.models import Proveedor, FacturaProveedor
from .models import GastoObra, OtroGasto


# ---------------------------------------------------------------------------
# Reglas financieras (SALDO = ASIGNADO - GASTADO_APROBADO)
# ---------------------------------------------------------------------------
def total_asignado(obra: Obra) -> Decimal:
    from django.db.models import Sum
    from apps.fondos.models import AsignacionFondo
    total = (
        AsignacionFondo.objects
        .filter(obra=obra, anulada=False)
        .aggregate(s=Sum('monto'))['s']
    )
    return total or Decimal('0.00')


def total_gastado(obra: Obra) -> Decimal:
    """Solo los gastos en estado APROBADO afectan el saldo."""
    from django.db.models import Sum
    total = (
        GastoObra.objects
        .filter(obra=obra, estado=EstadoGastoChoices.APROBADO)
        .aggregate(s=Sum('monto'))['s']
    )
    return total or Decimal('0.00')


def saldo(obra: Obra) -> Decimal:
    return total_asignado(obra) - total_gastado(obra)


def porcentaje_ejecucion(obra: Obra) -> Decimal:
    """Porcentaje de ejecución. Maneja división entre cero."""
    asignado = total_asignado(obra)
    if asignado == 0:
        return Decimal('0.00')
    return (total_gastado(obra) / asignado) * Decimal('100')


# ---------------------------------------------------------------------------
# Creaciones atómicas
# ---------------------------------------------------------------------------
@transaction.atomic
def crear_gasto_con_factura(*, obra, proveedor, folio, fecha_emision,
                              total, impuesto=Decimal('0.00'),
                              descripcion='', tipo_gasto=TipoGastoChoices.MATERIAL,
                              estado=EstadoGastoChoices.BORRADOR,
                              estado_factura=EstadoFacturaChoices.PENDIENTE,
                              fecha_gasto=None):
    """Crea GastoObra + FacturaProveedor en una sola transacción.

    Si algo falla, ROLLBACK.

    El `total` de la FacturaProveedor debe ser consistente con
    suma(subtotal de DetalleFactura) + impuesto. Esta validación se
    realiza al registrar los detalles vía `apps.proveedores.services`.
    """
    if fecha_gasto is None:
        fecha_gasto = fecha_emision
    gasto = GastoObra.objects.create(
        obra=obra,
        fecha=fecha_gasto,
        tipo_gasto=tipo_gasto,
        descripcion=descripcion,
        monto=total,
        estado=estado,
    )
    factura = FacturaProveedor.objects.create(
        obra=obra,
        proveedor=proveedor,
        gasto=gasto,
        folio=folio,
        fecha_emision=fecha_emision,
        impuesto=impuesto,
        total=total,
        estado=estado_factura,
    )
    return gasto, factura


@transaction.atomic
def crear_otro_gasto(*, obra, fecha, concepto, comprobante='', proveedor=None,
                       observaciones='', tipo_gasto=TipoGastoChoices.OTROS,
                       monto=Decimal('0.00'),
                       estado=EstadoGastoChoices.BORRADOR):
    """Crea GastoObra + OtroGasto atómicamente.

    El monto vive en GastoObra. OtroGasto NO mantiene monto propio.
    """
    gasto = GastoObra.objects.create(
        obra=obra,
        fecha=fecha,
        tipo_gasto=tipo_gasto,
        descripcion=concepto,
        monto=monto,
        estado=estado,
    )
    otro = OtroGasto.objects.create(
        obra=obra,
        gasto=gasto,
        fecha=fecha,
        concepto=concepto,
        comprobante=comprobante,
        proveedor=proveedor,
        observaciones=observaciones,
    )
    return gasto, otro


@transaction.atomic
def crear_nomina_con_gasto(*, obra, fecha, periodo_desde, periodo_hasta,
                              detalles, tipo_gasto=TipoGastoChoices.PERSONAL,
                              estado=EstadoGastoChoices.BORRADOR):
    """Crea Nomina + GastoObra + NominaDetalle atómicamente.

    detalles: lista de dicts {empleado, monto}
    """
    from apps.personal.models import Nomina, NominaDetalle

    total = sum((d['monto'] for d in detalles), Decimal('0.00'))
    gasto = GastoObra.objects.create(
        obra=obra,
        fecha=fecha,
        tipo_gasto=tipo_gasto,
        descripcion=f'Nómina {periodo_desde} - {periodo_hasta}',
        monto=total,
        estado=estado,
    )
    nomina = Nomina.objects.create(
        obra=obra,
        gasto=gasto,
        fecha=fecha,
        periodo_desde=periodo_desde,
        periodo_hasta=periodo_hasta,
    )
    for d in detalles:
        NominaDetalle.objects.create(
            nomina=nomina,
            empleado=d['empleado'],
            monto=d['monto'],
        )
    return gasto, nomina


@transaction.atomic
def crear_uso_maquinaria_con_gasto(*, obra, maquinaria, fecha, horas,
                                     tipo_gasto=TipoGastoChoices.MAQUINARIA,
                                     estado=EstadoGastoChoices.BORRADOR):
    """Crea UsoMaquinaria + GastoObra atómicamente.

    El monto se calcula como horas * costo_hora de la maquinaria.
    """
    from apps.maquinaria.models import UsoMaquinaria

    monto = (horas or Decimal('0.00')) * (maquinaria.costo_hora or Decimal('0.00'))
    gasto = GastoObra.objects.create(
        obra=obra,
        fecha=fecha,
        tipo_gasto=tipo_gasto,
        descripcion=f'Uso de {maquinaria.nombre} ({horas} h)',
        monto=monto,
        estado=estado,
    )
    uso = UsoMaquinaria.objects.create(
        obra=obra,
        maquinaria=maquinaria,
        gasto=gasto,
        fecha=fecha,
        horas=horas,
    )
    return gasto, uso


# ---------------------------------------------------------------------------
# Cambio de estado seguro
# ---------------------------------------------------------------------------
@transaction.atomic
def anular_gasto(gasto: GastoObra):
    """Anula un gasto sin borrarlo (regla: no borrar físicamente)."""
    if gasto.estado == EstadoGastoChoices.ANULADO:
        return gasto
    gasto.estado = EstadoGastoChoices.ANULADO
    gasto.save(update_fields=['estado', 'updated_at'])
    return gasto


# ---------------------------------------------------------------------------
# Cálculo masivo (evita N+1 en dashboards y listados)
# ---------------------------------------------------------------------------
def resumen_financiero_obras(obras_qs=None):
    """Devuelve un dict {obra_id: {'asignado': D, 'gastado': D, 'saldo': D, 'porcentaje': D}}
    para el queryset de obras dado (o todas si es None).

    Usa agregaciones en SQL (1 query por total) en vez de N queries.
    """
    from django.db.models import Sum, F, DecimalField
    from django.db.models.functions import Coalesce
    from apps.fondos.models import AsignacionFondo

    if obras_qs is None:
        from apps.obras.models import Obra
        obras_qs = Obra.objects.all()

    obra_ids = list(obras_qs.values_list('id', flat=True))

    asignado_qs = (
        AsignacionFondo.objects
        .filter(obra_id__in=obra_ids, anulada=False)
        .values('obra_id')
        .annotate(total=Coalesce(Sum('monto'), Decimal('0.00'), output_field=DecimalField()))
    )
    gastado_qs = (
        GastoObra.objects
        .filter(obra_id__in=obra_ids, estado=EstadoGastoChoices.APROBADO)
        .values('obra_id')
        .annotate(total=Coalesce(Sum('monto'), Decimal('0.00'), output_field=DecimalField()))
    )

    resultado = {oid: {
        'asignado': Decimal('0.00'),
        'gastado': Decimal('0.00'),
        'saldo': Decimal('0.00'),
        'porcentaje': Decimal('0.00'),
    } for oid in obra_ids}

    for row in asignado_qs:
        resultado[row['obra_id']]['asignado'] = row['total']
    for row in gastado_qs:
        resultado[row['obra_id']]['gastado'] = row['total']

    for oid in obra_ids:
        a = resultado[oid]['asignado']
        g = resultado[oid]['gastado']
        resultado[oid]['saldo'] = a - g
        resultado[oid]['porcentaje'] = (
            (g / a * Decimal('100')) if a > 0 else Decimal('0.00')
        )

    return resultado