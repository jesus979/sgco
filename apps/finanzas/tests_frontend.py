"""Smoke tests para los flujos de frontend: Obras, Fondos, Gastos, Otros gastos.

Verifica:
- Los listados responden 200 con el botón "Nuevo".
- El detalle responde 200.
- El filtro por obra funciona.
- La acción "Anular" cambia el estado.
"""
from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from apps.obras.models import Obra
from apps.fondos.models import AsignacionFondo
from apps.core.choices import (
    TipoAsignacionFondoChoices,
    TipoGastoChoices,
    EstadoGastoChoices,
)
from apps.finanzas.models import GastoObra, OtroGasto


class SmokeFrontendTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='tester', password='x')

    def setUp(self):
        self.client.login(username='tester', password='x')
        self.obra = Obra.objects.create(
            nombre='Obra Smoke',
            ubicacion='CDMX',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_estimada=date(2026, 12, 31),
        )
        self.asig = AsignacionFondo.objects.create(
            obra=self.obra,
            fecha=date(2026, 1, 1),
            monto=Decimal('100000'),
            tipo=TipoAsignacionFondoChoices.INICIAL,
        )
        self.gasto = GastoObra.objects.create(
            obra=self.obra,
            fecha=date(2026, 2, 1),
            tipo_gasto=TipoGastoChoices.MATERIAL,
            monto=Decimal('5000'),
            estado=EstadoGastoChoices.APROBADO,
        )

    # --------------------------- OBRAS ---------------------------
    def test_obras_list(self):
        r = self.client.get(reverse('obras:list'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Nueva obra')
        self.assertContains(r, self.obra.nombre)

    def test_obras_detail(self):
        r = self.client.get(reverse('obras:detail', args=[self.obra.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Asignaciones de fondo')

    # --------------------------- FONDOS ---------------------------
    def test_fondos_list(self):
        r = self.client.get(reverse('fondos:list'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Nueva asignación')
        self.assertContains(r, 'Vigente')

    def test_fondos_list_filtro_obra(self):
        # Crear otra obra y asignación para distinguir
        otra = Obra.objects.create(
            nombre='Otra Obra', ubicacion='Y',
            fecha_inicio=date(2026, 3, 1),
            fecha_fin_estimada=date(2026, 6, 30),
        )
        AsignacionFondo.objects.create(
            obra=otra, fecha=date(2026, 3, 1),
            monto=Decimal('50000'), tipo=TipoAsignacionFondoChoices.INICIAL,
        )
        r = self.client.get(f"{reverse('fondos:list')}?obra={self.obra.pk}")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.obra.nombre)
        self.assertNotContains(r, otra.nombre)

    def test_fondos_anular(self):
        r = self.client.post(reverse('fondos:anular', args=[self.asig.pk]))
        self.assertEqual(r.status_code, 302)
        self.asig.refresh_from_db()
        self.assertTrue(self.asig.anulada)

    # --------------------------- GASTOS ---------------------------
    def test_gastos_list(self):
        r = self.client.get(reverse('finanzas:gasto_list'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Nuevo gasto')

    def test_gastos_list_filtro_obra(self):
        r = self.client.get(f"{reverse('finanzas:gasto_list')}?obra={self.obra.pk}")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.obra.nombre)

    def test_gastos_list_filtro_estado(self):
        r = self.client.get(f"{reverse('finanzas:gasto_list')}?estado=APROBADO")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Aprobado')

    def test_gastos_detail(self):
        r = self.client.get(reverse('finanzas:gasto_detail', args=[self.gasto.pk]))
        self.assertEqual(r.status_code, 200)
        # Gasto sin documento origen (creado directo)
        self.assertContains(r, 'Documento origen')
        self.assertContains(r, 'gasto no tiene un documento origen')

    def test_gastos_anular(self):
        r = self.client.post(reverse('finanzas:gasto_anular', args=[self.gasto.pk]))
        self.assertEqual(r.status_code, 302)
        self.gasto.refresh_from_db()
        self.assertEqual(self.gasto.estado, EstadoGastoChoices.ANULADO)

    # --------------------------- OTROS GASTOS ---------------------------
    def test_otro_gasto_crear_y_anular(self):
        # Crear OtroGasto con GastoObra previo
        gasto = GastoObra.objects.create(
            obra=self.obra, fecha=date(2026, 3, 1),
            tipo_gasto=TipoGastoChoices.OTROS,
            monto=Decimal('1000'), estado=EstadoGastoChoices.APROBADO,
        )
        otro = OtroGasto.objects.create(
            obra=self.obra, gasto=gasto, fecha=date(2026, 3, 1),
            concepto='Multa', comprobante='COMP-1',
        )
        # Anular
        r = self.client.post(reverse('finanzas:otro_anular', args=[otro.pk]))
        self.assertEqual(r.status_code, 302)
        gasto.refresh_from_db()
        self.assertEqual(gasto.estado, EstadoGastoChoices.ANULADO)

    def test_otro_gasto_list(self):
        gasto = GastoObra.objects.create(
            obra=self.obra, fecha=date(2026, 3, 1),
            tipo_gasto=TipoGastoChoices.OTROS,
            monto=Decimal('1000'), estado=EstadoGastoChoices.APROBADO,
        )
        OtroGasto.objects.create(
            obra=self.obra, gasto=gasto, fecha=date(2026, 3, 1),
            concepto='Multa', comprobante='COMP-1',
        )
        r = self.client.get(reverse('finanzas:otro_list'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Nuevo otro gasto')
        self.assertContains(r, 'Multa')

    # --------------------------- LOGIN REQUERIDO ---------------------------
    def test_login_requerido(self):
        self.client.logout()
        for url in ['/obras/', '/fondos/', '/finanzas/gastos/', '/finanzas/otros/']:
            r = self.client.get(url)
            self.assertIn(r.status_code, (302, 301), f'{url} debería redirigir a login')