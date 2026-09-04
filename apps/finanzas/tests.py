import uuid
from decimal import Decimal
from datetime import date

from django.test import TestCase
from django.contrib.auth.models import User
from apps.obras.models import Obra
from apps.fondos.models import AsignacionFondo
from apps.core.choices import (
    TipoAsignacionFondoChoices,
    TipoGastoChoices,
    EstadoGastoChoices,
    EstadoFacturaChoices,
)
from .models import GastoObra
from .services import (
    total_asignado,
    total_gastado,
    saldo,
    porcentaje_ejecucion,
    crear_gasto_con_factura,
    crear_otro_gasto,
    anular_gasto,
    crear_nomina_con_gasto,
    crear_uso_maquinaria_con_gasto,
)
from apps.proveedores.models import Proveedor
from apps.inventario.models import Material
from apps.personal.models import Empleado
from apps.maquinaria.models import Maquinaria


class FinanzasServicesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='x')
        self.obra = Obra.objects.create(codigo=f'OBR-TEST-{uuid.uuid4().hex[:8]}', nombre='Obra A',
            ubicacion='CDMX',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_estimada=date(2026, 12, 31),
        )
        self.proveedor = Proveedor.objects.create(nombre='Prov 1')
        self.material = Material.objects.create(nombre='Cemento', unidad='saco', categoria='construccion')
        self.empleado = Empleado.objects.create(
            cedula='123', nombres='Juan', apellidos='Pérez',
            cargo='Albañil', salario_diario=Decimal('500.00'),
        )
        self.maquinaria = Maquinaria.objects.create(
            nombre='Excavadora', costo_hora=Decimal('300.00'),
        )

    # --- Creación de obra y asignaciones ---------------------------------
    def test_crear_obra(self):
        self.assertEqual(Obra.objects.count(), 1)

    def test_asignacion_inicial(self):
        AsignacionFondo.objects.create(
            obra=self.obra,
            fecha=date(2026, 1, 1),
            monto=Decimal('100000.00'),
            tipo=TipoAsignacionFondoChoices.INICIAL,
        )
        self.assertEqual(total_asignado(self.obra), Decimal('100000.00'))

    def test_ampliacion(self):
        AsignacionFondo.objects.create(
            obra=self.obra, fecha=date(2026, 1, 1), monto=Decimal('100000'),
            tipo=TipoAsignacionFondoChoices.INICIAL,
        )
        AsignacionFondo.objects.create(
            obra=self.obra, fecha=date(2026, 6, 1), monto=Decimal('50000'),
            tipo=TipoAsignacionFondoChoices.AMPLIACION,
        )
        self.assertEqual(total_asignado(self.obra), Decimal('150000'))

    def test_reduccion(self):
        AsignacionFondo.objects.create(
            obra=self.obra, fecha=date(2026, 1, 1), monto=Decimal('100000'),
            tipo=TipoAsignacionFondoChoices.INICIAL,
        )
        AsignacionFondo.objects.create(
            obra=self.obra, fecha=date(2026, 6, 1), monto=Decimal('30000'),
            tipo=TipoAsignacionFondoChoices.REDUCCION,
        )
        self.assertEqual(total_asignado(self.obra), Decimal('130000'))

    def test_total_asignado_sin_asignaciones(self):
        self.assertEqual(total_asignado(self.obra), Decimal('0.00'))

    # --- Estados del gasto y saldo --------------------------------------
    def test_gasto_borrador_no_afecta_saldo(self):
        AsignacionFondo.objects.create(
            obra=self.obra, fecha=date(2026, 1, 1), monto=Decimal('100000'),
            tipo=TipoAsignacionFondoChoices.INICIAL,
        )
        GastoObra.objects.create(
            obra=self.obra, fecha=date(2026, 2, 1),
            tipo_gasto=TipoGastoChoices.MATERIAL, monto=Decimal('10000'),
            estado=EstadoGastoChoices.BORRADOR,
        )
        self.assertEqual(total_gastado(self.obra), Decimal('0.00'))

    def test_gasto_aprobado_afecta_saldo(self):
        AsignacionFondo.objects.create(
            obra=self.obra, fecha=date(2026, 1, 1), monto=Decimal('100000'),
            tipo=TipoAsignacionFondoChoices.INICIAL,
        )
        GastoObra.objects.create(
            obra=self.obra, fecha=date(2026, 2, 1),
            tipo_gasto=TipoGastoChoices.MATERIAL, monto=Decimal('10000'),
            estado=EstadoGastoChoices.APROBADO,
        )
        self.assertEqual(total_gastado(self.obra), Decimal('10000.00'))

    def test_gasto_anulado_no_afecta_saldo(self):
        AsignacionFondo.objects.create(
            obra=self.obra, fecha=date(2026, 1, 1), monto=Decimal('100000'),
            tipo=TipoAsignacionFondoChoices.INICIAL,
        )
        g = GastoObra.objects.create(
            obra=self.obra, fecha=date(2026, 2, 1),
            tipo_gasto=TipoGastoChoices.MATERIAL, monto=Decimal('10000'),
            estado=EstadoGastoChoices.APROBADO,
        )
        anular_gasto(g)
        self.assertEqual(total_gastado(self.obra), Decimal('0.00'))

    def test_calculo_saldo(self):
        AsignacionFondo.objects.create(
            obra=self.obra, fecha=date(2026, 1, 1), monto=Decimal('100000'),
            tipo=TipoAsignacionFondoChoices.INICIAL,
        )
        GastoObra.objects.create(
            obra=self.obra, fecha=date(2026, 2, 1),
            tipo_gasto=TipoGastoChoices.MATERIAL, monto=Decimal('25000'),
            estado=EstadoGastoChoices.APROBADO,
        )
        self.assertEqual(saldo(self.obra), Decimal('75000.00'))

    def test_porcentaje_ejecucion(self):
        AsignacionFondo.objects.create(
            obra=self.obra, fecha=date(2026, 1, 1), monto=Decimal('100000'),
            tipo=TipoAsignacionFondoChoices.INICIAL,
        )
        GastoObra.objects.create(
            obra=self.obra, fecha=date(2026, 2, 1),
            tipo_gasto=TipoGastoChoices.MATERIAL, monto=Decimal('25000'),
            estado=EstadoGastoChoices.APROBADO,
        )
        self.assertEqual(porcentaje_ejecucion(self.obra), Decimal('25.0000'))

    def test_division_por_cero_en_porcentaje(self):
        # Sin asignaciones, no debe explotar
        self.assertEqual(porcentaje_ejecucion(self.obra), Decimal('0.00'))

    # --- Atomicidad factura + gasto -------------------------------------
    def test_factura_y_gasto_creados_juntos(self):
        g, f = crear_gasto_con_factura(
            obra=self.obra,
            proveedor=self.proveedor,
            folio='F-1',
            fecha_emision=date(2026, 2, 1),
            total=Decimal('5000.00'),
        )
        self.assertEqual(g.estado, EstadoGastoChoices.BORRADOR)
        self.assertEqual(f.gasto_id, g.id)
        self.assertEqual(f.estado, EstadoFacturaChoices.PENDIENTE)

    def test_rollback_factura_y_gasto(self):
        from django.db import transaction
        from apps.proveedores.models import FacturaProveedor

        class _Boom(Exception):
            pass

        with self.assertRaises(_Boom):
            with transaction.atomic():
                crear_gasto_con_factura(
                    obra=self.obra, proveedor=self.proveedor,
                    folio='F-2', fecha_emision=date(2026, 2, 1),
                    total=Decimal('5000'),
                )
                raise _Boom()
        self.assertEqual(GastoObra.objects.count(), 0)
        self.assertEqual(FacturaProveedor.objects.count(), 0)

    # --- Nómina + gasto -------------------------------------------------
    def test_nomina_y_gasto_asociados(self):
        from apps.personal.services import recalcular_total_nomina
        g, n = crear_nomina_con_gasto(
            obra=self.obra, fecha=date(2026, 2, 15),
            periodo_desde=date(2026, 2, 1), periodo_hasta=date(2026, 2, 15),
            detalles=[{'empleado': self.empleado, 'monto': Decimal('7500.00')}],
        )
        self.assertEqual(g.monto, Decimal('7500.00'))
        self.assertEqual(n.gasto_id, g.id)
        recalcular_total_nomina(n)
        self.assertEqual(n.gasto.monto, Decimal('7500.00'))

    # --- Uso maquinaria + gasto -----------------------------------------
    def test_uso_maquinaria_y_gasto_asociados(self):
        g, u = crear_uso_maquinaria_con_gasto(
            obra=self.obra, maquinaria=self.maquinaria,
            fecha=date(2026, 3, 1), horas=Decimal('8'),
        )
        # 8h * 300/h = 2400
        self.assertEqual(g.monto, Decimal('2400.00'))
        self.assertEqual(u.gasto_id, g.id)

    # --- Otro gasto + gasto ---------------------------------------------
    def test_otro_gasto_no_duplica_monto(self):
        g, otro = crear_otro_gasto(
            obra=self.obra, fecha=date(2026, 4, 1),
            concepto='Multa', comprobante='COMP-1',
            monto=Decimal('1500.00'),
        )
        self.assertEqual(g.monto, Decimal('1500.00'))
        self.assertEqual(otro.gasto_id, g.id)
        # OtroGasto NO debe mantener monto propio
        self.assertFalse(hasattr(otro, 'monto') and not callable(getattr(otro, 'monto', None)))


class ConstraintsTests(TestCase):
    def setUp(self):
        self.obra = Obra.objects.create(codigo=f'OBR-TEST-{uuid.uuid4().hex[:8]}', nombre='Obra', ubicacion='X',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_estimada=date(2026, 12, 31),
        )
        self.material = Material.objects.create(nombre='Arena', unidad='m3', categoria='construccion')
        self.proveedor = Proveedor.objects.create(nombre='Prov')

    def test_factura_unica_por_proveedor_y_folio(self):
        from django.db import IntegrityError
        from apps.finanzas.services import crear_gasto_con_factura

        crear_gasto_con_factura(
            obra=self.obra, proveedor=self.proveedor,
            folio='F-100', fecha_emision=date(2026, 2, 1), total=Decimal('100'),
        )
        with self.assertRaises(IntegrityError):
            crear_gasto_con_factura(
                obra=self.obra, proveedor=self.proveedor,
                folio='F-100', fecha_emision=date(2026, 3, 1), total=Decimal('200'),
            )

    def test_inventario_unico_por_obra_y_material(self):
        from django.db import IntegrityError
        from apps.inventario.models import InventarioObra

        InventarioObra.objects.create(obra=self.obra, material=self.material)
        with self.assertRaises(IntegrityError):
            InventarioObra.objects.create(obra=self.obra, material=self.material)


