"""Smoke tests para los módulos Proveedores / Inventario / Personal / Maquinaria."""
from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from apps.obras.models import Obra
from apps.core.choices import (
    EstadoGastoChoices,
    TipoMovimientoMaterialChoices,
)
from apps.inventario.models import Material, InventarioObra, MovimientoMaterial
from apps.personal.models import Empleado
from apps.maquinaria.models import Maquinaria
from apps.proveedores.models import Proveedor, FacturaProveedor, DetalleFactura
from apps.finanzas.services import crear_gasto_con_factura


class ProveedoresFrontendTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='t', password='x')

    def setUp(self):
        self.client.login(username='t', password='x')
        self.obra = Obra.objects.create(
            nombre='Obra', ubicacion='X',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_estimada=date(2026, 12, 31),
        )
        self.proveedor = Proveedor.objects.create(
            nombre='Prov Test', identificacion='P-001',
        )

    def test_proveedor_list(self):
        r = self.client.get(reverse('proveedores:proveedor_list'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Nuevo proveedor')
        self.assertContains(r, 'Prov Test')

    def test_proveedor_detail(self):
        r = self.client.get(reverse('proveedores:proveedor_detail', args=[self.proveedor.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Facturas')

    def test_factura_list_y_filtro(self):
        m = Material.objects.create(nombre='M', unidad='u', categoria='c')
        _, f = crear_gasto_con_factura(
            obra=self.obra, proveedor=self.proveedor,
            folio='F-1', fecha_emision=date(2026, 2, 1),
            total=Decimal('100'), impuesto=Decimal('16'),
        )
        r = self.client.get(reverse('proveedores:factura_list'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'F-1')

        r = self.client.get(f"{reverse('proveedores:factura_list')}?obra={self.obra.pk}")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'F-1')

    def test_factura_detail_consistencia(self):
        m = Material.objects.create(nombre='M', unidad='u', categoria='c')
        _, f = crear_gasto_con_factura(
            obra=self.obra, proveedor=self.proveedor,
            folio='F-CONS', fecha_emision=date(2026, 2, 1),
            total=Decimal('500'), impuesto=Decimal('80'),
        )
        DetalleFactura.objects.create(
            factura=f, material=m,
            cantidad=Decimal('2'), precio_unitario=Decimal('210'),
        )  # subtotal 420 + 80 = 500
        r = self.client.get(reverse('proveedores:factura_detail', args=[f.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Consistente')

    def test_factura_inconsistente(self):
        m = Material.objects.create(nombre='M', unidad='u', categoria='c')
        _, f = crear_gasto_con_factura(
            obra=self.obra, proveedor=self.proveedor,
            folio='F-INC', fecha_emision=date(2026, 2, 1),
            total=Decimal('999'),
        )
        r = self.client.get(reverse('proveedores:factura_detail', args=[f.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Esperado')

    def test_detalle_list_filtro_factura(self):
        m = Material.objects.create(nombre='M', unidad='u', categoria='c')
        _, f = crear_gasto_con_factura(
            obra=self.obra, proveedor=self.proveedor,
            folio='F-D', fecha_emision=date(2026, 2, 1),
            total=Decimal('100'),
        )
        DetalleFactura.objects.create(
            factura=f, material=m,
            cantidad=Decimal('1'), precio_unitario=Decimal('100'),
        )
        r = self.client.get(f"{reverse('proveedores:detalle_list')}?factura={f.pk}")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'F-D')


class InventarioFrontendTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='t', password='x')

    def setUp(self):
        self.client.login(username='t', password='x')
        self.obra = Obra.objects.create(
            nombre='Obra', ubicacion='X',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_estimada=date(2026, 12, 31),
        )
        self.material = Material.objects.create(
            nombre='Cemento', unidad='saco', categoria='construccion',
        )

    def test_material_list(self):
        r = self.client.get(reverse('inventario:material_list'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Nuevo material')
        self.assertContains(r, 'Cemento')

    def test_material_detail(self):
        InventarioObra.objects.create(
            obra=self.obra, material=self.material,
            cantidad_actual=Decimal('100'),
        )
        r = self.client.get(reverse('inventario:material_detail', args=[self.material.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Stock por obra')

    def test_inventario_list(self):
        InventarioObra.objects.create(
            obra=self.obra, material=self.material,
            cantidad_actual=Decimal('100'),
        )
        r = self.client.get(reverse('inventario:inventario_list'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Cemento')

    def test_movimiento_list(self):
        MovimientoMaterial.objects.create(
            obra=self.obra, material=self.material, usuario=self.user,
            tipo=TipoMovimientoMaterialChoices.ENTRADA,
            cantidad=Decimal('50'), fecha=date(2026, 2, 1),
        )
        r = self.client.get(reverse('inventario:movimiento_list'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Entrada')

    def test_movimiento_list_save_no_actualiza_inventario(self):
        MovimientoMaterial.objects.create(
            obra=self.obra, material=self.material, usuario=self.user,
            tipo=TipoMovimientoMaterialChoices.SALIDA,
            cantidad=Decimal('99'), fecha=date(2026, 2, 1),
        )
        InventarioObra.objects.create(
            obra=self.obra, material=self.material,
            cantidad_actual=Decimal('0'),
        )
        r = self.client.get(f"{reverse('inventario:movimiento_list')}?obra={self.obra.pk}")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Salida')


class PersonalFrontendTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='t', password='x')

    def setUp(self):
        self.client.login(username='t', password='x')
        self.obra = Obra.objects.create(
            nombre='Obra', ubicacion='X',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_estimada=date(2026, 12, 31),
        )
        self.empleado = Empleado.objects.create(
            cedula='123', nombres='A', apellidos='B',
            cargo='Albañil', salario_diario=Decimal('500'),
        )

    def test_empleado_list(self):
        r = self.client.get(reverse('personal:empleado_list'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Nuevo empleado')

    def test_empleado_detail(self):
        r = self.client.get(reverse('personal:empleado_detail', args=[self.empleado.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Historial de nóminas')

    def test_nomina_recalcular(self):
        from apps.finanzas.services import crear_nomina_con_gasto
        g, n = crear_nomina_con_gasto(
            obra=self.obra, fecha=date(2026, 2, 1),
            periodo_desde=date(2026, 2, 1), periodo_hasta=date(2026, 2, 15),
            detalles=[{'empleado': self.empleado, 'monto': Decimal('1000')}],
            estado=EstadoGastoChoices.APROBADO,
        )
        r = self.client.post(reverse('personal:nomina_recalcular', args=[n.pk]))
        self.assertEqual(r.status_code, 302)
        n.gasto.refresh_from_db()
        self.assertEqual(n.gasto.monto, Decimal('1000.00'))

    def test_nomina_anular(self):
        from apps.finanzas.services import crear_nomina_con_gasto
        g, n = crear_nomina_con_gasto(
            obra=self.obra, fecha=date(2026, 2, 1),
            periodo_desde=date(2026, 2, 1), periodo_hasta=date(2026, 2, 15),
            detalles=[{'empleado': self.empleado, 'monto': Decimal('1000')}],
            estado=EstadoGastoChoices.APROBADO,
        )
        r = self.client.post(reverse('personal:nomina_anular', args=[n.pk]))
        self.assertEqual(r.status_code, 302)
        g.refresh_from_db()
        from apps.core.choices import EstadoGastoChoices as EC
        self.assertEqual(g.estado, EC.ANULADO)

    def test_nomina_detalle_list_filtro(self):
        from apps.finanzas.services import crear_nomina_con_gasto
        _, n = crear_nomina_con_gasto(
            obra=self.obra, fecha=date(2026, 2, 1),
            periodo_desde=date(2026, 2, 1), periodo_hasta=date(2026, 2, 15),
            detalles=[{'empleado': self.empleado, 'monto': Decimal('1000')}],
            estado=EstadoGastoChoices.APROBADO,
        )
        r = self.client.get(f"{reverse('personal:nomina_detalle_list')}?nomina={n.pk}")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.empleado.nombre_completo)


class MaquinariaFrontendTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='t', password='x')

    def setUp(self):
        self.client.login(username='t', password='x')
        self.obra = Obra.objects.create(
            nombre='Obra', ubicacion='X',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_estimada=date(2026, 12, 31),
        )
        self.maquinaria = Maquinaria.objects.create(
            nombre='Excavadora', marca='CAT', modelo='320',
            identificacion='EX-1', costo_hora=Decimal('100'),
        )

    def test_maquinaria_list(self):
        r = self.client.get(reverse('maquinaria:maquinaria_list'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Nueva maquinaria')
        self.assertContains(r, 'Excavadora')

    def test_maquinaria_detail(self):
        r = self.client.get(reverse('maquinaria:maquinaria_detail', args=[self.maquinaria.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Costo total')

    def test_uso_list_y_anular(self):
        from apps.finanzas.services import crear_uso_maquinaria_con_gasto
        g, u = crear_uso_maquinaria_con_gasto(
            obra=self.obra, maquinaria=self.maquinaria,
            fecha=date(2026, 2, 1), horas=Decimal('10'),
            estado=EstadoGastoChoices.APROBADO,
        )
        r = self.client.get(reverse('maquinaria:uso_list'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Excavadora')

        r = self.client.post(reverse('maquinaria:uso_anular', args=[u.pk]))
        self.assertEqual(r.status_code, 302)
        g.refresh_from_db()
        from apps.core.choices import EstadoGastoChoices as EC
        self.assertEqual(g.estado, EC.ANULADO)