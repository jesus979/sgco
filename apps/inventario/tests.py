import uuid
from decimal import Decimal
from datetime import date

from django.test import TestCase
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError
from apps.obras.models import Obra
from apps.core.choices import TipoMovimientoMaterialChoices
from .models import Material, InventarioObra, MovimientoMaterial
from .services import (
    registrar_entrada_material,
    registrar_salida_material,
    registrar_devolucion_material,
    registrar_transferencia_material,
    ajustar_inventario,
)


class InventarioServicesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='op', password='x',
is_staff=True,)
        self.obra = Obra.objects.create(codigo=f'OBR-TEST-{uuid.uuid4().hex[:8]}', nombre='Obra', ubicacion='X',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_estimada=date(2026, 12, 31),
        )
        self.obra_b = Obra.objects.create(codigo=f'OBR-TEST-{uuid.uuid4().hex[:8]}', nombre='Obra B', ubicacion='Y',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_estimada=date(2026, 12, 31),
        )
        self.material = Material.objects.create(nombre='Cemento', unidad='saco', categoria='construccion')

    def test_entrada_actualiza_inventario(self):
        registrar_entrada_material(
            obra=self.obra, material=self.material, cantidad=Decimal('50'),
            usuario=self.user, fecha=date(2026, 2, 1),
        )
        inv = InventarioObra.objects.get(obra=self.obra, material=self.material)
        self.assertEqual(inv.cantidad_actual, Decimal('50'))

    def test_salida_descuenta_inventario(self):
        registrar_entrada_material(
            obra=self.obra, material=self.material, cantidad=Decimal('50'),
            usuario=self.user, fecha=date(2026, 2, 1),
        )
        registrar_salida_material(
            obra=self.obra, material=self.material, cantidad=Decimal('20'),
            usuario=self.user, fecha=date(2026, 2, 2),
        )
        inv = InventarioObra.objects.get(obra=self.obra, material=self.material)
        self.assertEqual(inv.cantidad_actual, Decimal('30'))

    def test_devolucion_suma(self):
        registrar_entrada_material(
            obra=self.obra, material=self.material, cantidad=Decimal('50'),
            usuario=self.user, fecha=date(2026, 2, 1),
        )
        registrar_salida_material(
            obra=self.obra, material=self.material, cantidad=Decimal('20'),
            usuario=self.user, fecha=date(2026, 2, 2),
        )
        registrar_devolucion_material(
            obra=self.obra, material=self.material, cantidad=Decimal('5'),
            usuario=self.user, fecha=date(2026, 2, 3),
        )
        inv = InventarioObra.objects.get(obra=self.obra, material=self.material)
        self.assertEqual(inv.cantidad_actual, Decimal('35'))

    def test_transferencia_entre_obras(self):
        registrar_entrada_material(
            obra=self.obra, material=self.material, cantidad=Decimal('100'),
            usuario=self.user, fecha=date(2026, 2, 1),
        )
        registrar_transferencia_material(
            obra_origen=self.obra, obra_destino=self.obra_b,
            material=self.material, cantidad=Decimal('30'),
            usuario=self.user, fecha=date(2026, 2, 2),
        )
        self.assertEqual(InventarioObra.objects.get(obra=self.obra, material=self.material).cantidad_actual, Decimal('70'))
        self.assertEqual(InventarioObra.objects.get(obra=self.obra_b, material=self.material).cantidad_actual, Decimal('30'))

    def test_ajuste_reemplaza_cantidad(self):
        registrar_entrada_material(
            obra=self.obra, material=self.material, cantidad=Decimal('50'),
            usuario=self.user, fecha=date(2026, 2, 1),
        )
        ajustar_inventario(
            obra=self.obra, material=self.material, cantidad_final=Decimal('20'),
            usuario=self.user, fecha=date(2026, 2, 2),
        )
        self.assertEqual(InventarioObra.objects.get(obra=self.obra, material=self.material).cantidad_actual, Decimal('20'))

    def test_save_no_aplica_efectos_secundarios(self):
        """Regla clave de la spec: guardar un MovimientoMaterial NO debe
        duplicar el efecto en InventarioObra."""
        inv = InventarioObra.objects.create(obra=self.obra, material=self.material)
        inv.cantidad_actual = Decimal('10')
        inv.save()

        # Crear movimiento directo (sin servicio) NO debe cambiar el inventario
        MovimientoMaterial.objects.create(
            obra=self.obra, material=self.material, usuario=self.user,
            tipo=TipoMovimientoMaterialChoices.SALIDA, cantidad=Decimal('99'),
            fecha=date(2026, 2, 1),
        )
        inv.refresh_from_db()
        self.assertEqual(inv.cantidad_actual, Decimal('10'))


