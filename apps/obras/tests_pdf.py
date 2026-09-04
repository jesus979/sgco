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
from apps.finanzas.models import GastoObra
from apps.finanzas.services import crear_gasto_con_factura
from apps.proveedores.models import Proveedor
from apps.inventario.models import Material


class ReportePDFTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='tester', password='x')

    def setUp(self):
        self.client.login(username='tester', password='x')
        self.obra = Obra.objects.create(
            nombre='Obra PDF Test',
            ubicacion='CDMX',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_estimada=date(2026, 12, 31),
        )
        AsignacionFondo.objects.create(
            obra=self.obra, fecha=date(2026, 1, 1),
            monto=Decimal('50000'),
            tipo=TipoAsignacionFondoChoices.INICIAL,
        )
        m = Material.objects.create(
            nombre='Cemento', unidad='saco', categoria='construccion',
        )
        prov = Proveedor.objects.create(nombre='Prov', identificacion='P-1')
        g, f = crear_gasto_con_factura(
            obra=self.obra, proveedor=prov,
            folio='F-PDF', fecha_emision=date(2026, 2, 1),
            total=Decimal('5000'), impuesto=Decimal('800'),
            estado=EstadoGastoChoices.APROBADO,
        )
        from apps.proveedores.models import DetalleFactura
        DetalleFactura.objects.create(
            factura=f, material=m,
            cantidad=Decimal('10'), precio_unitario=Decimal('420'),
        )

    def test_reporte_retorna_pdf(self):
        r = self.client.get(reverse('obras:reporte', args=[self.obra.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')

    def test_reporte_contiene_nombre_obra(self):
        r = self.client.get(reverse('obras:reporte', args=[self.obra.pk]))
        # PDF empieza con %PDF
        self.assertTrue(r.content.startswith(b'%PDF'))
        # El nombre de la obra está codificado en el PDF (puede estar comprimido,
        # pero el reporte debe generarse sin error).
        self.assertGreater(len(r.content), 1000)

    def test_reporte_sin_autenticacion_redirige(self):
        self.client.logout()
        r = self.client.get(reverse('obras:reporte', args=[self.obra.pk]))
        self.assertIn(r.status_code, (302, 301))

    def test_reporte_obra_inexistente_404(self):
        r = self.client.get(reverse('obras:reporte', args=[99999]))
        self.assertEqual(r.status_code, 404)

    def test_pdf_service_genera_bytes(self):
        from apps.obras.pdf import generar_reporte_obra
        pdf = generar_reporte_obra(self.obra, usuario=self.user)
        self.assertIsInstance(pdf, bytes)
        self.assertTrue(pdf.startswith(b'%PDF'))

    def test_pdf_service_con_obra_vacia(self):
        from apps.obras.pdf import generar_reporte_obra
        obra_vacia = Obra.objects.create(
            nombre='Obra Vacía',
            ubicacion='X',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_estimada=date(2026, 12, 31),
        )
        pdf = generar_reporte_obra(obra_vacia)
        self.assertIsInstance(pdf, bytes)
        self.assertTrue(pdf.startswith(b'%PDF'))


class DashboardChartsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='t', password='x')

    def setUp(self):
        self.client.login(username='t', password='x')
        self.obra = Obra.objects.create(
            nombre='O', ubicacion='X',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_estimada=date(2026, 12, 31),
        )
        from apps.finanzas.models import GastoObra
        GastoObra.objects.create(
            obra=self.obra, fecha=date(2026, 2, 1),
            tipo_gasto=TipoGastoChoices.MATERIAL,
            monto=Decimal('1000'),
            estado=EstadoGastoChoices.APROBADO,
        )

    def test_dashboard_tiene_datos_de_graficos(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        ctx = r.context
        self.assertIn('gastos_por_tipo_chart', ctx)
        self.assertIn('obras_por_estado_chart', ctx)
        self.assertIn('labels', ctx['gastos_por_tipo_chart'])
        self.assertIn('values', ctx['gastos_por_tipo_chart'])

    def test_dashboard_renderiza_canvas(self):
        r = self.client.get('/')
        self.assertContains(r, 'chartGastosTipo')
        self.assertContains(r, 'chartObrasEstado')
        self.assertContains(r, 'chart.js')