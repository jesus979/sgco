import uuid
from decimal import Decimal
from datetime import date

from django.test import TestCase
from django.db import IntegrityError
from apps.obras.models import Obra
from apps.finanzas.services import crear_nomina_con_gasto
from apps.personal.models import Empleado
from .services import recalcular_total_nomina


class NominaTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user('tester', password='x',
is_staff=True,)
        self.obra = Obra.objects.create(codigo=f'OBR-TEST-{uuid.uuid4().hex[:8]}', nombre='Obra', ubicacion='X',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_estimada=date(2026, 12, 31),
        )
        self.e1 = Empleado.objects.create(
            cedula='1', nombres='A', apellidos='B', cargo='X',
            salario_diario=Decimal('100'),
        )
        self.e2 = Empleado.objects.create(
            cedula='2', nombres='C', apellidos='D', cargo='Y',
            salario_diario=Decimal('150'),
        )

    def test_recalcular_total_nomina(self):
        _, nomina = crear_nomina_con_gasto(
            obra=self.obra, fecha=date(2026, 2, 1),
            periodo_desde=date(2026, 2, 1), periodo_hasta=date(2026, 2, 15),
            detalles=[
                {'empleado': self.e1, 'monto': Decimal('1500')},
                {'empleado': self.e2, 'monto': Decimal('2250')},
            ],
            usuario=self.user,)
        # 1500 + 2250 = 3750
        total = recalcular_total_nomina(nomina)
        self.assertEqual(total, Decimal('3750.00'))
        self.assertEqual(nomina.gasto.monto, Decimal('3750.00'))

    def test_periodo_unico_por_obra(self):
        crear_nomina_con_gasto(
            obra=self.obra, fecha=date(2026, 2, 1),
            periodo_desde=date(2026, 2, 1), periodo_hasta=date(2026, 2, 15),
            detalles=[{'empleado': self.e1, 'monto': Decimal('100')}],
            usuario=self.user,)
        with self.assertRaises(IntegrityError):
            crear_nomina_con_gasto(
                obra=self.obra, fecha=date(2026, 2, 1),
                periodo_desde=date(2026, 2, 1), periodo_hasta=date(2026, 2, 15),
                detalles=[{'empleado': self.e2, 'monto': Decimal('200')}],
                usuario=self.user,)

    def test_save_nomina_detalle_no_recalcula(self):
        """Regla: NominaDetalle.save() NO debe recalcular totales."""
        _, nomina = crear_nomina_con_gasto(
            obra=self.obra, fecha=date(2026, 2, 1),
            periodo_desde=date(2026, 2, 1), periodo_hasta=date(2026, 2, 15),
            detalles=[{'empleado': self.e1, 'monto': Decimal('1500')}],
            usuario=self.user,)
        # Forzar valor conocido del gasto
        nomina.gasto.monto = Decimal('9999')
        nomina.gasto.save()

        # Editar un detalle directamente NO debe mover el total
        from .models import NominaDetalle
        d = nomina.nominas_detalle.first()
        d.monto = Decimal('1')
        d.save()

        nomina.gasto.refresh_from_db()
        self.assertEqual(nomina.gasto.monto, Decimal('9999'))


