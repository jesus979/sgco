"""Choices (catálogos) centralizadas.

Regla del proyecto: no crear tablas de catálogo en esta fase.
Usar TextChoices / choices en cada modelo.
"""
from django.db import models


class EstadoObraChoices(models.TextChoices):
    PLANIFICACION = 'PLANIFICACION', 'Planificación'
    EN_EJECUCION = 'EN_EJECUCION', 'En ejecución'
    PAUSADA = 'PAUSADA', 'Pausada'
    CULMINADA = 'CULMINADA', 'Culminada'


class TipoAsignacionFondoChoices(models.TextChoices):
    INICIAL = 'INICIAL', 'Inicial'
    AMPLIACION = 'AMPLIACION', 'Ampliación'
    REDUCCION = 'REDUCCION', 'Reducción'
    AJUSTE = 'AJUSTE', 'Ajuste'


class TipoGastoChoices(models.TextChoices):
    MATERIAL = 'MATERIAL', 'Material'
    PERSONAL = 'PERSONAL', 'Personal'
    MAQUINARIA = 'MAQUINARIA', 'Maquinaria'
    COMBUSTIBLE = 'COMBUSTIBLE', 'Combustible'
    SERVICIO = 'SERVICIO', 'Servicio'
    TRANSPORTE = 'TRANSPORTE', 'Transporte'
    OTROS = 'OTROS', 'Otros'


class EstadoGastoChoices(models.TextChoices):
    BORRADOR = 'BORRADOR', 'Borrador'
    APROBADO = 'APROBADO', 'Aprobado'
    ANULADO = 'ANULADO', 'Anulado'


class EstadoFacturaChoices(models.TextChoices):
    PENDIENTE = 'PENDIENTE', 'Pendiente'
    PARCIAL = 'PARCIAL', 'Parcial'
    PAGADO = 'PAGADO', 'Pagado'


class TipoMovimientoMaterialChoices(models.TextChoices):
    ENTRADA = 'ENTRADA', 'Entrada'
    SALIDA = 'SALIDA', 'Salida'
    TRANSFERENCIA = 'TRANSFERENCIA', 'Transferencia'
    DEVOLUCION = 'DEVOLUCION', 'Devolución'
    AJUSTE = 'AJUSTE', 'Ajuste'