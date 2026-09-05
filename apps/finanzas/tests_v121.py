"""Tests de regresión del hardening v1.2.1.

Cubre los 8 objetivos de la fase v1.2.1:
1. GastoObra.usuario NOT NULL
2. AsignacionFondo.usuario NOT NULL
3. Sin FacturaDeleteView / sin URL de delete de factura
4. AsignacionFondo inmutable (obra/monto/tipo bloqueados)
5. Factura: el servicio asigna usuario, la vista NO lo duplica
6. Permisos: usuario no-staff recibe 403 en acciones sensibles
7. Documentación coherente (cubierto por inspección de código)
8. Tests de regresión específicos
"""
import uuid
from decimal import Decimal
from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.http import Http404

from apps.obras.models import Obra
from apps.fondos.models import AsignacionFondo
from apps.finanzas.models import GastoObra
from apps.finanzas.services import crear_gasto_con_factura
from apps.proveedores.models import Proveedor, FacturaProveedor, DetalleFactura
from apps.inventario.models import Material


def make_user(**kw):
    kw.setdefault('is_staff', True)
    return User.objects.create_user(**kw)


def make_obra(codigo=None):
    return Obra.objects.create(
        codigo=codigo or f'OBR-{uuid.uuid4().hex[:8]}',
        nombre='Obra', ubicacion='X',
        fecha_inicio=date(2026, 1, 1),
        fecha_fin_estimada=date(2026, 12, 31),
    )


# ---------------------------------------------------------------------------
# 1. GastoObra.usuario NOT NULL
# ---------------------------------------------------------------------------
class GastoObraUsuarioObligatorioTests(TestCase):
    def setUp(self):
        self.user = make_user(username='u', password='x')
        self.obra = make_obra()

    def test_modelo_usuario_es_not_null(self):
        """GastoObra.usuario NO permite null=True."""
        field = GastoObra._meta.get_field('usuario')
        self.assertFalse(field.null)

    def test_crear_gasto_sin_usuario_falla(self):
        """Crear un GastoObra sin usuario debe fallar en clean()."""
        g = GastoObra(
            obra=self.obra, fecha=date(2026, 2, 1),
            tipo_gasto='MATERIAL', monto=Decimal('100'),
        )
        with self.assertRaises(ValidationError) as ctx:
            g.full_clean()
        self.assertIn('usuario', ctx.exception.message_dict)


# ---------------------------------------------------------------------------
# 2. AsignacionFondo.usuario NOT NULL
# ---------------------------------------------------------------------------
class AsignacionFondoUsuarioObligatorioTests(TestCase):
    def setUp(self):
        self.user = make_user(username='u', password='x')
        self.obra = make_obra()

    def test_modelo_usuario_es_not_null(self):
        field = AsignacionFondo._meta.get_field('usuario')
        self.assertFalse(field.null)

    def test_crear_asignacion_sin_usuario_falla(self):
        a = AsignacionFondo(
            obra=self.obra, fecha=date(2026, 1, 1),
            monto=Decimal('1000'), tipo='INICIAL',
        )
        with self.assertRaises(ValidationError) as ctx:
            a.full_clean()
        self.assertIn('usuario', ctx.exception.message_dict)


# ---------------------------------------------------------------------------
# 3. Sin FacturaDeleteView / sin URL de delete
# ---------------------------------------------------------------------------
class SinFacturaDeleteTests(TestCase):
    def setUp(self):
        self.user = make_user(username='u', password='x')
        self.client.login(username='u', password='x')

    def test_no_existe_url_factura_delete(self):
        """No debe existir la URL proveedores:factura_delete."""
        from django.urls import reverse, NoReverseMatch
        with self.assertRaises(NoReverseMatch):
            reverse('proveedores:factura_delete', args=[1])

    def test_no_existe_clase_factura_delete_view(self):
        """No debe existir la clase FacturaDeleteView en apps.proveedores.views."""
        from apps.proveedores import views
        self.assertFalse(hasattr(views, 'FacturaDeleteView'))

    def test_views_no_referencian_factura_delete(self):
        """El módulo views no debe definir la clase FacturaDeleteView
        ni usarla en un import o llamada. (Los comentarios que la mencionan
        están permitidos porque documentan la decisión.)"""
        from apps.proveedores import views
        # Verificar que la clase no está definida en el módulo
        self.assertFalse(hasattr(views, 'FacturaDeleteView'))
        # Verificar que no hay `class FacturaDeleteView` en el código
        src = open(views.__file__, 'r', encoding='utf-8').read()
        self.assertNotIn('class FacturaDeleteView', src)
        self.assertNotIn('FacturaDeleteView.as_view', src)


# ---------------------------------------------------------------------------
# 4. AsignacionFondo inmutable
# ---------------------------------------------------------------------------
class AsignacionFondoInmutableTests(TestCase):
    def setUp(self):
        self.user = make_user(username='u', password='x')
        self.obra_a = make_obra(codigo='OBR-AA')
        self.obra_b = make_obra(codigo='OBR-BB')

    def test_cambiar_obra_bloqueado(self):
        a = AsignacionFondo.objects.create(
            obra=self.obra_a, fecha=date(2026, 1, 1),
            monto=Decimal('1000'), tipo='INICIAL',
            usuario=self.user,
        )
        a.obra = self.obra_b
        with self.assertRaises(ValidationError) as ctx:
            a.save()
        self.assertIn('obra', ctx.exception.message_dict)

    def test_cambiar_monto_bloqueado(self):
        a = AsignacionFondo.objects.create(
            obra=self.obra_a, fecha=date(2026, 1, 1),
            monto=Decimal('1000'), tipo='INICIAL',
            usuario=self.user,
        )
        a.monto = Decimal('2000')
        with self.assertRaises(ValidationError) as ctx:
            a.save()
        self.assertIn('monto', ctx.exception.message_dict)

    def test_cambiar_tipo_bloqueado(self):
        a = AsignacionFondo.objects.create(
            obra=self.obra_a, fecha=date(2026, 1, 1),
            monto=Decimal('1000'), tipo='INICIAL',
            usuario=self.user,
        )
        a.tipo = 'AMPLIACION'
        with self.assertRaises(ValidationError) as ctx:
            a.save()
        self.assertIn('tipo', ctx.exception.message_dict)

    def test_referencia_editable(self):
        """referencia debe poder editarse sin error de inmutabilidad."""
        a = AsignacionFondo.objects.create(
            obra=self.obra_a, fecha=date(2026, 1, 1),
            monto=Decimal('1000'), tipo='INICIAL',
            referencia='original',
            usuario=self.user,
        )
        a.referencia = 'modificada'
        a.save()
        a.refresh_from_db()
        self.assertEqual(a.referencia, 'modificada')

    def test_observaciones_editable(self):
        a = AsignacionFondo.objects.create(
            obra=self.obra_a, fecha=date(2026, 1, 1),
            monto=Decimal('1000'), tipo='INICIAL',
            observaciones='original',
            usuario=self.user,
        )
        a.observaciones = 'modificado'
        a.save()
        a.refresh_from_db()
        self.assertEqual(a.observaciones, 'modificado')

    def test_formulario_update_view_solo_campos_seguros(self):
        """La UpdateView solo expone referencia y observaciones."""
        from apps.fondos.views import AsignacionFondoUpdateView
        self.assertEqual(
            list(AsignacionFondoUpdateView.fields),
            ['referencia', 'observaciones'],
        )

    def test_patron_correcto_500_a_600(self):
        """Convertir 500000 → 600000 NO debe hacerse editando.
        Lo correcto: anular 500000 + crear nueva de 600000."""
        a500 = AsignacionFondo.objects.create(
            obra=self.obra_a, fecha=date(2026, 1, 1),
            monto=Decimal('500000'), tipo='INICIAL',
            usuario=self.user,
        )
        a500.anulada = True
        a500.save()
        a600 = AsignacionFondo.objects.create(
            obra=self.obra_a, fecha=date(2026, 1, 1),
            monto=Decimal('600000'), tipo='INICIAL',
            usuario=self.user,
        )
        from apps.finanzas.services import total_asignado
        self.assertEqual(total_asignado(self.obra_a), Decimal('600000'))


# ---------------------------------------------------------------------------
# 5. Factura: el servicio asigna usuario, sin doble asignación
# ---------------------------------------------------------------------------
class FacturaUsuarioUnicoTests(TestCase):
    def setUp(self):
        self.user = make_user(username='u', password='x')
        self.obra = make_obra()
        self.proveedor = Proveedor.objects.create(
            nombre='Prov', identificacion=f'P-{uuid.uuid4().hex[:6]}',
        )

    def test_servicio_asigna_usuario(self):
        """crear_gasto_con_factura asigna usuario al GastoObra."""
        _gasto, factura = crear_gasto_con_factura(
            obra=self.obra, proveedor=self.proveedor,
            folio='F-001', fecha_emision=date(2026, 2, 1),
            total=Decimal('1000'), usuario=self.user,
        )
        self.assertEqual(_gasto.usuario, self.user)
        self.assertEqual(factura.gasto.usuario, self.user)

    def test_view_asigna_usuario_correcto(self):
        """FacturaCreateView debe asignar request.user al GastoObra
        vía el servicio, sin doble asignación posterior."""
        from django.test import Client
        client = Client()
        client.login(username='u', password='x')
        r = client.post('/proveedores/facturas/nueva/', {
            'obra': self.obra.pk,
            'proveedor': self.proveedor.pk,
            'folio': 'F-002',
            'fecha_emision': '2026-03-01',
            'impuesto': '0',
            'total': '500',
            'estado': 'PENDIENTE',
        })
        self.assertIn(r.status_code, (200, 302))
        # La factura debe haberse creado con su gasto asociado
        from apps.proveedores.models import FacturaProveedor
        factura = FacturaProveedor.objects.get(folio='F-002')
        # El usuario del GastoObra debe ser el autenticado
        self.assertEqual(factura.gasto.usuario, self.user)


# ---------------------------------------------------------------------------
# 6. Permisos: usuario no-staff recibe 403
# ---------------------------------------------------------------------------
class PermisosAccionesSensiblesTests(TestCase):
    def setUp(self):
        # crear una asignación de prueba con un usuario staff
        self.staff = make_user(username='staff', password='x', is_staff=True)
        self.no_staff = User.objects.create_user(
            username='normal', password='x', is_staff=False,
        )
        self.obra = make_obra()
        self.asignacion = AsignacionFondo.objects.create(
            obra=self.obra, fecha=date(2026, 1, 1),
            monto=Decimal('1000'), tipo='INICIAL',
            usuario=self.staff,
        )

    def test_no_staff_no_puede_anular_asignacion(self):
        from django.test import Client
        client = Client()
        client.login(username='normal', password='x')
        r = client.post(reverse('fondos:anular', args=[self.asignacion.pk]))
        self.assertEqual(r.status_code, 403)

    def test_staff_puede_anular_asignacion(self):
        from django.test import Client
        client = Client()
        client.login(username='staff', password='x')
        r = client.post(reverse('fondos:anular', args=[self.asignacion.pk]))
        self.assertEqual(r.status_code, 302)
        self.asignacion.refresh_from_db()
        self.assertTrue(self.asignacion.anulada)

    def test_superusuario_puede_anular(self):
        superuser = User.objects.create_superuser(
            username='admin', password='x', email='a@a.com',
        )
        from django.test import Client
        client = Client()
        client.login(username='admin', password='x')
        r = client.post(reverse('fondos:anular', args=[self.asignacion.pk]))
        self.assertEqual(r.status_code, 302)