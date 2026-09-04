import uuid
from decimal import Decimal
from datetime import date

from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.obras.models import Obra
from apps.inventario.models import Material
from .models import Proveedor, FacturaProveedor, DetalleFactura
from apps.finanzas.services import crear_gasto_con_factura
from .services import (
    registrar_detalle_factura,
    actualizar_total_desde_detalles,
    verificar_consistencia_factura,
    exigir_consistencia_factura,
)


class FacturaConsistenciaTests(TestCase):
    def setUp(self):
        self.obra = Obra.objects.create(codigo=f'OBR-TEST-{uuid.uuid4().hex[:8]}', nombre='Obra', ubicacion='X',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_estimada=date(2026, 12, 31),
        )
        self.proveedor = Proveedor.objects.create(
            nombre='Prov', identificacion='PROV-001',
        )
        self.material = Material.objects.create(nombre='Cemento', unidad='saco', categoria='construccion')

    def _crear_factura(self, total=Decimal('0.00'), impuesto=Decimal('0.00')):
        from apps.core.choices import EstadoGastoChoices, EstadoFacturaChoices
        _, f = crear_gasto_con_factura(
            obra=self.obra, proveedor=self.proveedor,
            folio='F-CONS', fecha_emision=date(2026, 2, 1),
            total=total, impuesto=impuesto,
        )
        return f

    def test_subtotal_vacio_es_cero(self):
        f = self._crear_factura(total=Decimal('0.00'))
        self.assertEqual(f.subtotal, Decimal('0.00'))

    def test_total_igual_a_subtotal_sin_impuesto(self):
        f = self._crear_factura(total=Decimal('0.00'))
        registrar_detalle_factura(
            factura=f, material=self.material,
            cantidad=Decimal('10'), precio_unitario=Decimal('100'),
        )
        # subtotal = 10*100 = 1000, impuesto = 0, total esperado = 1000
        self.assertEqual(f.subtotal, Decimal('1000'))
        actualizar_total_desde_detalles(f)
        f.refresh_from_db()
        self.assertEqual(f.total, Decimal('1000.00'))
        self.assertTrue(verificar_consistencia_factura(f))

    def test_total_subtotal_mas_impuesto(self):
        f = self._crear_factura(total=Decimal('0.00'), impuesto=Decimal('160.00'))
        registrar_detalle_factura(
            factura=f, material=self.material,
            cantidad=Decimal('10'), precio_unitario=Decimal('100'),
        )
        # subtotal=1000, impuesto=160, total esperado=1160
        actualizar_total_desde_detalles(f)
        f.refresh_from_db()
        self.assertEqual(f.total, Decimal('1160.00'))
        self.assertEqual(f.impuesto, Decimal('160.00'))
        self.assertTrue(verificar_consistencia_factura(f))

    def test_inconsistencia_detectada(self):
        f = self._crear_factura(total=Decimal('9999.00'))
        registrar_detalle_factura(
            factura=f, material=self.material,
            cantidad=Decimal('10'), precio_unitario=Decimal('100'),
        )
        # total=9999 pero subtotal+impuesto=1000 -> inconsistente
        self.assertFalse(verificar_consistencia_factura(f))

    def test_exigir_consistencia_lanza_error(self):
        f = self._crear_factura(total=Decimal('9999.00'))
        registrar_detalle_factura(
            factura=f, material=self.material,
            cantidad=Decimal('10'), precio_unitario=Decimal('100'),
        )
        with self.assertRaises(ValidationError):
            exigir_consistencia_factura(f)

    def test_multiples_detalles(self):
        f = self._crear_factura(total=Decimal('0.00'), impuesto=Decimal('50.00'))
        registrar_detalle_factura(factura=f, material=self.material,
                                   cantidad=Decimal('2'), precio_unitario=Decimal('100'))
        registrar_detalle_factura(factura=f, material=self.material,
                                   cantidad=Decimal('5'), precio_unitario=Decimal('200'))
        # subtotal = 200 + 1000 = 1200 ; +50 imp = 1250
        actualizar_total_desde_detalles(f)
        f.refresh_from_db()
        self.assertEqual(f.subtotal, Decimal('1200'))
        self.assertEqual(f.total, Decimal('1250.00'))
        self.assertTrue(verificar_consistencia_factura(f))


