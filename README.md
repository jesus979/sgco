# SGCO — Sistema de Gestión de Construcción y Obras

> MVP empresarial para la gestión y control de obras: **OBRA → FONDOS ASIGNADOS → GASTOS → SALDO → TRAZABILIDAD**.

SGCO permite llevar el control financiero de proyectos de construcción con foco en:

- Asignaciones de fondo por obra
- Gastos con estados (BORRADOR, APROBADO, ANULADO)
- Saldo en tiempo real = Asignado − Gastos Aprobados
- Trazabilidad: cada gasto se origina de un documento (Factura, Nómina, Uso de Maquinaria u Otro Gasto)
- Consistencia de facturas (subtotal + impuesto = total)
- Servicios transaccionales explícitos para movimientos de inventario

---

## Stack

- **Python** 3.12+
- **Django** 5.2
- **SQLite** (desarrollo) / PostgreSQL (producción)
- **django-unfold** — admin moderno
- **Tailwind CSS** + iconos **Tabler** (vía CDN)
- **Chart.js** (vía CDN) para gráficos en el dashboard
- **ReportLab** para reportes PDF

---

## Requisitos

- Python 3.12 o superior
- pip
- Git (opcional)

---

## Instalación

```bash
# 1. Clonar o descargar el repositorio
cd sgco

# 2. Crear entorno virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env si es necesario (en dev los valores por defecto funcionan)

# 5. Aplicar migraciones
python manage.py migrate

# 6. Cargar datos demo (5 obras, 7 proveedores, 8 materiales, 6 empleados, 4 máquinas, ~10 facturas/gastos/nóminas)
python manage.py seed_demo

# 7. Crear superusuario (opcional; el seed ya crea uno)
python manage.py createsuperuser
```

---

## Arranque

```bash
python manage.py runserver
```

Abrir en el navegador: **http://127.0.0.1:8000/**

**Credenciales demo:**

| Campo | Valor |
|---|---|
| Usuario | `admin` |
| Contraseña | `admin123` |

---

## Estructura del proyecto

```
sgco/
├── manage.py
├── requirements.txt
├── .env.example
├── docs/
│   └── database.md
├── sgco/                # Configuración Django (settings, urls, wsgi)
└── apps/
    ├── core/            # Choices compartidas, utilidades, datos demo
    ├── dashboard/       # Vista principal con KPIs
    ├── obras/           # Obra
    ├── fondos/          # AsignacionFondo
    ├── finanzas/        # GastoObra, OtroGasto (servicios de dominio)
    ├── proveedores/     # Proveedor, FacturaProveedor, DetalleFactura
    ├── inventario/      # Material, InventarioObra, MovimientoMaterial
    ├── personal/        # Empleado, Nomina, NominaDetalle
    └── maquinaria/      # Maquinaria, UsoMaquinaria
```

---

## Reglas financieras (resumen)

```
TOTAL_ASIGNADO = SUM(AsignacionFondo.monto WHERE anulada=False)
TOTAL_GASTADO  = SUM(GastoObra.monto WHERE estado=APROBADO)
SALDO          = TOTAL_ASIGNADO − TOTAL_GASTADO
% EJECUCIÓN    = TOTAL_GASTADO / TOTAL_ASIGNADO × 100
```

- Solo los gastos **APROBADOS** afectan el saldo.
- Las asignaciones anuladas (campo `anulada=True`) no cuentan para el asignado.
- Los estados de gasto (`BORRADOR/APROBADO/ANULADO`) son independientes del estado de pago de la factura (`PENDIENTE/PARCIAL/PAGADO`).

---

## Servicios transaccionales clave

| Servicio | Ubicación | Función |
|---|---|---|
| `total_asignado(obra)` | `apps.finanzas.services` | Suma de asignaciones vigentes |
| `total_gastado(obra)` | `apps.finanzas.services` | Suma de gastos aprobados |
| `saldo(obra)` | `apps.finanzas.services` | Asignado − Gastado |
| `porcentaje_ejecucion(obra)` | `apps.finanzas.services` | % de ejecución (sin dividir por cero) |
| `anular_gasto(gasto)` | `apps.finanzas.services` | Cambia estado a ANULADO |
| `crear_gasto_con_factura(...)` | `apps.finanzas.services` | Crea GastoObra + Factura atómicamente |
| `crear_nomina_con_gasto(...)` | `apps.finanzas.services` | Crea GastoObra + Nomina + detalles atómicamente |
| `crear_uso_maquinaria_con_gasto(...)` | `apps.finanzas.services` | Crea GastoObra + UsoMaquinaria atómicamente |
| `recalcular_total_nomina(nomina)` | `apps.personal.services` | Recalcula GastoObra.monto desde detalles |
| `registrar_entrada/salida/devolucion/transferencia/ajuste` | `apps.inventario.services` | Actualizan stock de forma atómica |
| `verificar_consistencia_factura` | `apps.proveedores.services` | `total == subtotal + impuesto` |
| `actualizar_total_desde_detalles` | `apps.proveedores.services` | Recalcula total desde líneas |
| `anular_asignacion` | `apps.fondos.services` | Marca asignación como anulada |

> **Regla importante**: `MovimientoMaterial.save()` **NO** actualiza stock. Se hace exclusivamente a través de los servicios transaccionales.

---

## Comandos útiles

```bash
# Servidor de desarrollo
python manage.py runserver

# Migraciones
python manage.py makemigrations
python manage.py migrate

# Tests
python manage.py test apps           # todos los tests
python manage.py test apps.finanzas  # solo finanzas
python manage.py test apps -v 2      # verbose

# Carga de datos demo
python manage.py seed_demo

# Admin de Django (también con Unfold)
# http://127.0.0.1:8000/admin/

# Crear superusuario
python manage.py createsuperuser

# Consola de Python con el entorno Django cargado
python manage.py shell
```

---

## URLs principales

| URL | Descripción |
|---|---|
| `/` | Dashboard con KPIs globales |
| `/obras/` | Listado de obras con balance financiero |
| `/obras/<id>/` | Detalle de obra (drill-down completo) |
| `/obras/<id>/reporte/` | Reporte PDF descargable |
| `/fondos/?obra=<id>` | Asignaciones de fondo (filtrable) |
| `/finanzas/gastos/?obra=<id>` | Gastos (filtrable por obra y estado) |
| `/finanzas/otros/?obra=<id>` | Otros gastos |
| `/proveedores/` | Catálogo de proveedores |
| `/proveedores/facturas/?obra=<id>` | Facturas (filtrable) |
| `/inventario/materiales/` | Catálogo de materiales |
| `/inventario/inventarios/?obra=<id>` | Stock por obra |
| `/personal/` | Empleados |
| `/personal/nominas/?obra=<id>` | Nóminas (filtrable) |
| `/maquinaria/` | Catálogo de maquinaria |
| `/maquinaria/usos/?obra=<id>` | Usos de maquinaria |
| `/admin/` | Admin con django-unfold |

---

## Documentación

- **`docs/database.md`** — Modelo de datos: entidades, campos, FK, cardinalidades, reglas financieras, decisiones de diseño, supuestos y pendientes.
- **`docs/flow.md`** — Diagramas de flujo de los procesos clave en ASCII art.
- **`docs/user-guide.md`** — Manual de usuario final: cómo operar el sistema, paso a paso, con ejemplos y FAQ.

---

## Pendientes / fuera de alcance MVP

- **Contabilidad completa** (libro mayor, balances, cuentas)
- **Bancos y cuentas por cobrar**
- **CRM / ventas / producción**
- **Costos comprometidos / devengado / flujo de caja avanzado**
- **Importar XML de facturas (CFDI)**
- **Reportes descargables distintos al PDF de obra**
- **Permisos por rol** (hoy todos los autenticados tienen acceso completo)
- **Auditoría** (quién modificó qué)

---

## Licencia

Uso interno. Pendiente de definir.
