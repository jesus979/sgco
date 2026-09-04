"""Management command para poblar la base con datos demo realistas.

Uso:
    python manage.py seed_demo
"""
from decimal import Decimal
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User

from apps.obras.models import Obra
from apps.fondos.models import AsignacionFondo
from apps.core.choices import (
    EstadoObraChoices,
    TipoAsignacionFondoChoices,
    TipoGastoChoices,
    EstadoGastoChoices,
    EstadoFacturaChoices,
    TipoMovimientoMaterialChoices,
)
from apps.finanzas.models import GastoObra, OtroGasto
from apps.proveedores.models import (
    Proveedor,
    FacturaProveedor,
    DetalleFactura,
)
from apps.inventario.models import (
    Material,
    InventarioObra,
    MovimientoMaterial,
)
from apps.inventario.services import (
    registrar_entrada_material,
    registrar_salida_material,
)
from apps.personal.models import Empleado
from apps.maquinaria.models import Maquinaria, UsoMaquinaria
from apps.finanzas.services import (
    crear_gasto_con_factura,
    crear_otro_gasto,
    crear_nomina_con_gasto,
    crear_uso_maquinaria_con_gasto,
)
from apps.personal.services import recalcular_total_nomina


class Command(BaseCommand):
    help = 'Pobla la base con datos demo realistas.'

    def handle(self, *args, **opts):
        self.stdout.write('Limpiando datos demo...')
        self._clean()

        self.stdout.write('Creando datos demo...')
        with transaction.atomic():
            user = User.objects.first() or User.objects.create_user('admin', 'admin@sgco.local', 'admin123')
            obras = self._obras()
            asignaciones = self._asignaciones(obras)
            proveedores = self._proveedores()
            materiales = self._materiales()
            empleados = self._empleados()
            maquinas = self._maquinas()

            # Gastos y facturas para varias obras
            self._gastos_y_facturas(obras, proveedores, materiales)
            self._otros_gastos(obras, proveedores)
            self._inventarios(obras, materiales, user)
            self._nominas(obras, empleados)
            self._uso_maquinaria(obras, maquinas)

        self.stdout.write(self.style.SUCCESS('Datos demo creados.'))

    def _clean(self):
        MovimientoMaterial.objects.all().delete()
        InventarioObra.objects.all().delete()
        DetalleFactura.objects.all().delete()
        FacturaProveedor.objects.all().delete()
        from apps.personal.models import Nomina, NominaDetalle
        NominaDetalle.objects.all().delete()
        Nomina.objects.all().delete()
        UsoMaquinaria.objects.all().delete()
        OtroGasto.objects.all().delete()
        GastoObra.objects.all().delete()
        AsignacionFondo.objects.all().delete()
        Maquinaria.objects.all().delete()
        Empleado.objects.all().delete()
        Material.objects.all().delete()
        Proveedor.objects.all().delete()
        Obra.objects.all().delete()

    def _obras(self):
        return [
            Obra.objects.create(
                nombre='Edificio Residencial Las Palmas',
                ubicacion='Caracas, Distrito Capital',
                fecha_inicio=date(2026, 1, 15),
                fecha_fin_estimada=date(2026, 12, 20),
                estado=EstadoObraChoices.EN_EJECUCION,
            ),
            Obra.objects.create(
                nombre='Puente Vial Av. Bolívar',
                ubicacion='Maracaibo, Zulia',
                fecha_inicio=date(2026, 3, 1),
                fecha_fin_estimada=date(2027, 2, 28),
                estado=EstadoObraChoices.EN_EJECUCION,
            ),
            Obra.objects.create(
                nombre='Centro Comercial Plaza Norte',
                ubicacion='Valencia, Carabobo',
                fecha_inicio=date(2025, 11, 10),
                fecha_fin_estimada=date(2026, 8, 30),
                estado=EstadoObraChoices.PAUSADA,
            ),
            Obra.objects.create(
                nombre='Rehabilitación Escuela Simón Bolívar',
                ubicacion='Barquisimeto, Lara',
                fecha_inicio=date(2026, 5, 5),
                fecha_fin_estimada=date(2026, 11, 30),
                estado=EstadoObraChoices.PLANIFICACION,
            ),
            Obra.objects.create(
                nombre='Planta de Tratamiento Aguas Residuales',
                ubicacion='Maracay, Aragua',
                fecha_inicio=date(2025, 8, 1),
                fecha_fin_estimada=date(2026, 4, 30),
                estado=EstadoObraChoices.CULMINADA,
            ),
        ]

    def _asignaciones(self, obras):
        asignaciones = []
        planes = [
            (Decimal('500000.00'), Decimal('150000.00'), Decimal('80000.00')),
            (Decimal('1200000.00'), Decimal('400000.00'), None),
            (Decimal('850000.00'), Decimal('250000.00'), None),
            (Decimal('320000.00'), None, None),
            (Decimal('450000.00'), Decimal('120000.00'), None),
        ]
        for obra, (inicial, ampliacion, _) in zip(obras, planes):
            asignaciones.append(AsignacionFondo.objects.create(
                obra=obra,
                fecha=obra.fecha_inicio,
                monto=inicial,
                tipo=TipoAsignacionFondoChoices.INICIAL,
                referencia=f'Asignación inicial {obra.id}',
            ))
            if ampliacion:
                asignaciones.append(AsignacionFondo.objects.create(
                    obra=obra,
                    fecha=obra.fecha_inicio + timedelta(days=60),
                    monto=ampliacion,
                    tipo=TipoAsignacionFondoChoices.AMPLIACION,
                    referencia=f'Ampliación presupuestaria #{obra.id}',
                ))
        return asignaciones

    def _proveedores(self):
        data = [
            ('Cementos del Caribe C.A.', 'J-12345678-1'),
            ('Aceros Industriales S.A.', 'J-23456789-2'),
            ('Construcciones El Vigía C.A.', 'J-34567890-3'),
            ('Distribuidora La Paloma', 'V-9876543-2'),
            ('Servicios Eléctricos Andinos', 'J-45678901-4'),
            ('Transportes Río Orinoco', 'J-56789012-5'),
            ('Materiales del Centro C.A.', 'J-67890123-6'),
        ]
        return [
            Proveedor.objects.create(
                nombre=n, identificacion=ident,
                telefono=f'0212-{5550000 + i:07d}',
                email=f'contacto{i}@proveedor{i}.com',
                direccion=f'Av. Principal, Edif. {chr(65+i)}, Caracas',
                activo=True,
            )
            for i, (n, ident) in enumerate(data)
        ]

    def _materiales(self):
        data = [
            ('Cemento Portland Tipo I', 'saco', 'Construcción', '500.00'),
            ('Arena lavada', 'm3', 'Construcción', '320.00'),
            ('Piedra picada', 'm3', 'Construcción', '280.00'),
            ('Cabilla 1/2"', 'kg', 'Acero', '12.50'),
            ('Cabilla 3/8"', 'kg', 'Acero', '10.80'),
            ('Bloque de concreto 15cm', 'pieza', 'Mampostería', '15.00'),
            ('Láminas de zinc', 'pieza', 'Techos', '180.00'),
            ('Tubería PVC 4"', 'm', 'Plomería', '95.00'),
        ]
        return [
            Material.objects.create(
                nombre=n, unidad=u, categoria=c,
                precio_unitario_referencia=Decimal(p),
                activo=True,
            )
            for n, u, c, p in data
        ]

    def _empleados(self):
        data = [
            ('1234567', 'Juan Carlos', 'Rodríguez Pérez', 'Maestro de obra', '1200.00'),
            ('2345678', 'María Fernanda', 'González López', 'Ingeniera residente', '1800.00'),
            ('3456789', 'Pedro Antonio', 'Hernández Silva', 'Albañil', '650.00'),
            ('4567890', 'Luis Eduardo', 'Martínez Castro', 'Electricista', '850.00'),
            ('5678901', 'Ana Lucía', 'Sánchez Mendoza', 'Topógrafa', '1100.00'),
            ('6789012', 'Carlos Ramón', 'Torres Briceño', 'Operador de maquinaria', '950.00'),
        ]
        return [
            Empleado.objects.create(
                cedula=c, nombres=n, apellidos=a,
                cargo=cargo, salario_diario=Decimal(s),
                activo=True,
            )
            for c, n, a, cargo, s in data
        ]

    def _maquinas(self):
        data = [
            ('Excavadora CAT 320D', 'Caterpillar', '320D', 'EXC-001', '850.00'),
            ('Retroexcavadora JCB 3CX', 'JCB', '3CX', 'RET-002', '620.00'),
            ('Vibrocompactador Bomag BW211', 'Bomag', 'BW211', 'VIB-003', '450.00'),
            ('Mezcladora de concreto 9pc', 'Truper', '9PC', 'MEZ-004', '95.00'),
        ]
        return [
            Maquinaria.objects.create(
                nombre=n, marca=ma, modelo=mo,
                identificacion=ident, costo_hora=Decimal(p),
                activo=True,
            )
            for n, ma, mo, ident, p in data
        ]

    def _gastos_y_facturas(self, obras, proveedores, materiales):
        # Obra 0: varios gastos con factura
        obra = obras[0]
        g, f = crear_gasto_con_factura(
            obra=obra, proveedor=proveedores[0],
            folio='FAC-1001', fecha_emision=date(2026, 1, 25),
            total=Decimal('85000.00'), impuesto=Decimal('13000.00'),
            tipo_gasto=TipoGastoChoices.MATERIAL,
            estado=EstadoGastoChoices.APROBADO,
            estado_factura=EstadoFacturaChoices.PAGADO,
        )
        DetalleFactura.objects.create(
            factura=f, material=materiales[0],
            cantidad=Decimal('170'), precio_unitario=Decimal('500.00'),
        )
        g, f = crear_gasto_con_factura(
            obra=obra, proveedor=proveedores[1],
            folio='FAC-1002', fecha_emision=date(2026, 2, 10),
            total=Decimal('32000.00'), impuesto=Decimal('4900.00'),
            tipo_gasto=TipoGastoChoices.MATERIAL,
            estado=EstadoGastoChoices.APROBADO,
            estado_factura=EstadoFacturaChoices.PENDIENTE,
        )
        DetalleFactura.objects.create(
            factura=f, material=materiales[3],
            cantidad=Decimal('2500'), precio_unitario=Decimal('12.50'),
        )

        # Obra 1
        obra = obras[1]
        g, f = crear_gasto_con_factura(
            obra=obra, proveedor=proveedores[0],
            folio='FAC-2001', fecha_emision=date(2026, 3, 20),
            total=Decimal('180000.00'), impuesto=Decimal('27000.00'),
            tipo_gasto=TipoGastoChoices.MATERIAL,
            estado=EstadoGastoChoices.APROBADO,
            estado_factura=EstadoFacturaChoices.PARCIAL,
        )
        DetalleFactura.objects.create(
            factura=f, material=materiales[0],
            cantidad=Decimal('360'), precio_unitario=Decimal('500.00'),
        )
        # Gasto en BORRADOR (no afecta saldo)
        g, f = crear_gasto_con_factura(
            obra=obra, proveedor=proveedores[4],
            folio='FAC-2002', fecha_emision=date(2026, 4, 5),
            total=Decimal('45000.00'), impuesto=Decimal('6800.00'),
            tipo_gasto=TipoGastoChoices.SERVICIO,
            estado=EstadoGastoChoices.BORRADOR,
        )

        # Obra 2
        obra = obras[2]
        g, f = crear_gasto_con_factura(
            obra=obra, proveedor=proveedores[6],
            folio='FAC-3001', fecha_emision=date(2026, 1, 5),
            total=Decimal('62000.00'), impuesto=Decimal('9400.00'),
            tipo_gasto=TipoGastoChoices.MATERIAL,
            estado=EstadoGastoChoices.APROBADO,
            estado_factura=EstadoFacturaChoices.PAGADO,
        )
        DetalleFactura.objects.create(
            factura=f, material=materiales[5],
            cantidad=Decimal('4000'), precio_unitario=Decimal('15.00'),
        )

    def _otros_gastos(self, obras, proveedores):
        crear_otro_gasto(
            obra=obras[0], fecha=date(2026, 2, 20),
            concepto='Permisos municipales',
            comprobante='PM-2026-001',
            proveedor=proveedores[2],
            monto=Decimal('15000.00'),
            estado=EstadoGastoChoices.APROBADO,
        )
        crear_otro_gasto(
            obra=obras[1], fecha=date(2026, 3, 10),
            concepto='Estudio de impacto ambiental',
            comprobante='EIA-002',
            monto=Decimal('28000.00'),
            estado=EstadoGastoChoices.APROBADO,
        )

    def _inventarios(self, obras, materiales, user):
        # Asignar algunas entradas y salidas para obra 0
        obra = obras[0]
        registrar_entrada_material(
            obra=obra, material=materiales[0], cantidad=Decimal('400'),
            usuario=user, fecha=date(2026, 1, 26),
            referencia='Entrada inicial cemento',
        )
        registrar_salida_material(
            obra=obra, material=materiales[0], cantidad=Decimal('180'),
            usuario=user, fecha=date(2026, 2, 1),
            referencia='Consumo semana 1',
        )
        registrar_entrada_material(
            obra=obra, material=materiales[3], cantidad=Decimal('2500'),
            usuario=user, fecha=date(2026, 2, 12),
            referencia='Entrada cabillas',
        )

        obra = obras[1]
        registrar_entrada_material(
            obra=obra, material=materiales[0], cantidad=Decimal('600'),
            usuario=user, fecha=date(2026, 3, 22),
            referencia='Entrada cemento puente',
        )

    def _nominas(self, obras, empleados):
        # Nómina quincenal obra 0
        crear_nomina_con_gasto(
            obra=obras[0], fecha=date(2026, 1, 31),
            periodo_desde=date(2026, 1, 16), periodo_hasta=date(2026, 1, 31),
            detalles=[
                {'empleado': empleados[0], 'monto': Decimal('18000.00')},
                {'empleado': empleados[2], 'monto': Decimal('9750.00')},
                {'empleado': empleados[3], 'monto': Decimal('12750.00')},
            ],
            estado=EstadoGastoChoices.APROBADO,
        )

        crear_nomina_con_gasto(
            obra=obras[1], fecha=date(2026, 3, 31),
            periodo_desde=date(2026, 3, 16), periodo_hasta=date(2026, 3, 31),
            detalles=[
                {'empleado': empleados[1], 'monto': Decimal('27000.00')},
                {'empleado': empleados[4], 'monto': Decimal('16500.00')},
                {'empleado': empleados[5], 'monto': Decimal('14250.00')},
            ],
            estado=EstadoGastoChoices.APROBADO,
        )

    def _uso_maquinaria(self, obras, maquinas):
        crear_uso_maquinaria_con_gasto(
            obra=obras[1], maquinaria=maquinas[0],
            fecha=date(2026, 3, 18), horas=Decimal('40'),
            estado=EstadoGastoChoices.APROBADO,
        )
        crear_uso_maquinaria_con_gasto(
            obra=obras[0], maquinaria=maquinas[3],
            fecha=date(2026, 2, 5), horas=Decimal('20'),
            estado=EstadoGastoChoices.APROBADO,
        )