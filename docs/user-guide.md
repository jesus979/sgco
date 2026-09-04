# SGCO — Manual de Usuario

> Sistema de Gestión y Control de Obras.
> Versión 1.0 · MVP
> Este manual está dirigido a los **operadores** del sistema: personal
> de la constructora que registra obras, asigna fondos, carga gastos y
> hace seguimiento de la ejecución.

---

## Tabla de contenidos

1. [Bienvenida](#1-bienvenida)
2. [Conceptos clave](#2-conceptos-clave)
3. [Primeros pasos](#3-primeros-pasos)
4. [Tour por el menú lateral](#4-tour-por-el-menú-lateral)
5. [Trabajando con obras](#5-trabajando-con-obras)
6. [Asignando fondos](#6-asignando-fondos)
7. [Registrando gastos](#7-registrando-gastos)
8. [Proveedores y facturas](#8-proveedores-y-facturas)
9. [Inventario y materiales](#9-inventario-y-materiales)
10. [Personal y nóminas](#10-personal-y-nóminas)
11. [Maquinaria](#11-maquinaria)
12. [Otros gastos](#12-otros-gastos)
13. [Reportes](#13-reportes)
14. [Preguntas frecuentes](#14-preguntas-frecuentes)
15. [Buenas prácticas](#15-buenas-prácticas)
16. [Glosario](#16-glosario)
17. [Pendientes con el cliente](#17-pendientes-con-el-cliente)

---

## 1. Bienvenida

**SGCO** (Sistema de Gestión y Control de Obras) es una aplicación
web para llevar el control financiero de proyectos de construcción.

Su objetivo principal es responder en tiempo real a una pregunta:

> **¿Cuánto dinero le queda disponible a esta obra?**

Para responderla, el sistema registra cuánto se asignó a cada obra,
cuánto se gastó (y en qué) y calcula el saldo.

### ¿Para quién es este manual?

Este manual está pensado para:

- **Personal de operaciones** que registra obras, fondos y gastos.
- **Gerencia de proyecto** que consulta saldos, reportes y KPIs.
- **Personal administrativo** que carga facturas y nóminas.

**No es un manual técnico** ni de instalación. Para eso ver
`README.md` y `docs/database.md`.

---

## 2. Conceptos clave

Antes de operar el sistema, familiarízate con estos términos.

### La cadena fundamental

```
ASIGNACIONES DE FONDO  →  GASTOS  →  SALDO DISPONIBLE
        +                     -              =
```

- **Asignación de fondo**: dinero que la empresa pone a disposición de una obra.
- **Gasto**: egreso que se carga contra una obra, siempre con un documento origen.
- **Saldo**: lo que queda disponible. Fórmula: `SALDO = Asignado − Gastos aprobados`.

### Documentos origen

Cada gasto de la obra proviene de uno de estos documentos:

| Documento | Cuándo se usa | Módulo |
|---|---|---|
| **Factura de proveedor** | Compra de materiales, servicios externos | Proveedores |
| **Nómina** | Pago de personal (quincenal, mensual) | Personal |
| **Uso de maquinaria** | Horas de equipo usadas en la obra | Maquinaria |
| **Otro gasto** | Multas, permisos, gastos sin factura formal | Finanzas |

Esto garantiza la **trazabilidad**: todo gasto tiene un origen auditable.

### Estados de un gasto

Todo gasto pasa por tres estados:

| Estado | Significado | ¿Afecta saldo? |
|---|---|---|
| **BORRADOR** | Recién creado, pendiente de revisión | **No** |
| **APROBADO** | Validado, se ejecuta contra el saldo | **Sí** |
| **ANULADO** | Cancelado, no se ejecutó | **No** |

> **Regla de oro**: solo los gastos **APROBADOS** afectan el saldo.

### Estados de una obra

Una obra recorre estos estados:

```
PLANIFICACIÓN  →  EN EJECUCIÓN  →  (PAUSADA)  →  CULMINADA
```

- **PLANIFICACIÓN**: se está preparando. Aún no se ejecuta.
- **EN EJECUCIÓN**: ya se están cargando gastos.
- **PAUSADA**: detenida temporalmente (clima, falta de pago, etc.).
- **CULMINADA**: obra terminada.

### El saldo siempre se recalcula

El saldo **no se guarda** en la base de datos. Se calcula en tiempo
real cada vez que alguien lo consulta:

```
SALDO = SUM(Asignaciones WHERE anulada=False)
      − SUM(Gastos WHERE estado='APROBADO')
```

Esto significa que **anular un gasto aprobado aumenta el saldo** de
forma inmediata, sin acciones adicionales.

---

## 3. Primeros pasos

### 3.1 Abrir el sistema

1. Abre tu navegador (Chrome, Firefox, Edge).
2. Ve a `http://127.0.0.1:8000/` (o la URL que te haya indicado el
   administrador del sistema).
3. Verás la pantalla de login.

### 3.2 Iniciar sesión

| Campo | Valor |
|---|---|
| Usuario | `admin` |
| Contraseña | `admin123` |

> ⚠ **Importante**: cambia la contraseña después del primer ingreso.
> (Funcionalidad pendiente en próximas versiones.)

### 3.3 Cargar datos demo (opcional, solo en desarrollo)

Si el sistema está recién instalado y quieres explorar con datos de
ejemplo, abre una terminal y ejecuta:

```bash
python manage.py seed_demo
```

Esto crea:

- 5 obras en distintos estados
- 7 proveedores
- 8 materiales
- 6 empleados
- 4 maquinarias
- ~10 facturas, gastos, nóminas y movimientos

### 3.4 Conocer el dashboard

Al ingresar, verás el **Dashboard** con:

- 4 tarjetas KPI superiores (obras activas, asignado, gastado, % ejecución)
- Tabla de obras con saldo y % de ejecución
- Gráfico de barras: gastos aprobados por tipo
- Gráfico de dona: obras por estado
- Tabla de últimos gastos

> 💡 Pasa el cursor sobre los gráficos para ver detalles.

---

## 4. Tour por el menú lateral

A la izquierda de todas las páginas verás un **menú lateral (sidebar)**
con la siguiente estructura:

```
SGCO
├─ ⌂ Dashboard                     [siempre visible arriba]
├─ ▼ OBRAS
│   ├─ Listado
│   └─ Nueva obra
├─ ▼ OPERACIÓN
│   ├─ Asignaciones de fondo
│   ├─ Gastos
│   ├─ Otros gastos
│   ├─ Facturas
│   └─ Detalles de factura
├─ ▼ INVENTARIO
│   ├─ Materiales
│   ├─ Stock por obra
│   └─ Movimientos
├─ ▼ PERSONAL
│   ├─ Empleados
│   ├─ Nóminas
│   └─ Detalles de nómina
└─ ▼ MAQUINARIA
    ├─ Catálogo
    └─ Usos
```

### Cómo se usa

- **Click en un grupo** (Obras, Operación, etc.) → se expande o
  colapsa mostrando sus opciones.
- **Click en un enlace** dentro del grupo → navegas a esa pantalla.
- **La sección actual se resalta** en color azul.
- El **Dashboard** está fijo arriba y nunca se colapsa.

### En pantallas pequeñas (móvil)

- El menú se oculta automáticamente.
- Aparece un **botón de hamburguesa** en la cabecera superior.
- Click en él → se abre el menú como panel deslizable.
- Click fuera del panel o tecla `Esc` → se cierra.

---

## 5. Trabajando con obras

Una **obra** es el proyecto de construcción. Toda la información
financiera gira alrededor de una obra.

### 5.1 Crear una obra nueva

1. En el menú lateral, expande **Obras** y click en **Nueva obra**.
2. Llena los campos:

| Campo | Obligatorio | Ejemplo |
|---|---|---|
| Nombre | Sí | Edificio Residencial Las Palmas |
| Ubicación | Sí | Caracas, Distrito Capital |
| Fecha de inicio | Sí | 15/01/2026 |
| Fecha fin estimada | Sí | 20/12/2026 |
| Estado | No (default: PLANIFICACIÓN) | — |

3. Click en **Crear**.
4. Serás redirigido al listado. Click en la obra recién creada.

> 💡 Una obra recién creada tiene **saldo = 0** y **% de ejecución = 0%**.
> Antes de poder gastar, hay que asignar fondos (ver sección 6).

### 5.2 Ver el detalle de una obra

La pantalla de detalle es la más importante del sistema. Muestra:

#### Header
- Nombre + estado + ubicación + fechas
- Botones: **Reporte PDF**, **Editar**, **← Volver**

#### KPIs financieros
4 tarjetas grandes con los totales:
- **Total asignado**: suma de todas las asignaciones vigentes
- **Total gastado**: solo gastos APROBADOS
- **Saldo disponible**: asignado − gastado
- **% de ejecución**: gastado / asignado × 100

#### Resumen
- Distribución de gastos aprobados por tipo (gráfico de barras)
- Estado de gastos: cuántos aprobados, borrador, anulados

#### Secciones (anclas en la página)
- **Fondos**: asignaciones de la obra
- **Gastos**: listado de gastos
- **Facturas**: facturas de proveedores
- **Inventario**: stock actual y últimos movimientos
- **Personal**: nóminas pagadas
- **Maquinaria**: usos registrados

### 5.3 Cambiar el estado de una obra

1. En el detalle, click en **Editar**.
2. Cambia el campo **Estado** al nuevo valor.
3. Guarda.

Las transiciones habituales son:

- PLANIFICACIÓN → EN EJECUCIÓN (cuando comienza la obra)
- EN EJECUCIÓN → PAUSADA (si se detiene temporalmente)
- PAUSADA → EN EJECUCIÓN (al reanudar)
- EN EJECUCIÓN → CULMINADA (al terminar)

> ⚠ **No hay validación** que impida transiciones "raras" (por ejemplo,
> PAUSADA → CULMINADA). Operar con criterio.

### 5.4 Generar el reporte PDF

1. En el detalle de la obra, click en **Reporte PDF**.
2. Se abre el PDF en una nueva pestaña del navegador.
3. El PDF contiene:
 - Header con datos de la obra
 - KPIs financieros
 - Listado de asignaciones, gastos y facturas
 - Pie de página con fecha y usuario que lo generó
4. Para guardarlo, usa **Archivo → Guardar como** en tu navegador.

> 💡 **Úsalo para**: cierres mensuales, presentaciones a gerencia,
> respaldo documental al culminar una obra.

### 5.5 Culminar una obra

1. Verifica que el **saldo sea 0** o positivo (si es negativo, hay
   gastos por encima del asignado — revisar).
2. Confirma que **todas las facturas** estén en estado PAGADO o
   canceladas.
3. Verifica que **no haya movimientos de inventario pendientes**.
4. Cambia el estado a **CULMINADA** desde Editar.
5. Genera el **Reporte PDF** como constancia de cierre.

---

## 6. Asignando fondos

Antes de registrar cualquier gasto, la obra debe tener **fondos
asignados**. Sin fondos, el saldo es 0 y no se puede aprobar ningún
gasto.

### 6.1 Cuándo usar cada tipo

| Tipo | Cuándo se usa |
|---|---|
| **INICIAL** | Al arrancar la obra. Es la primera carga presupuestaria. |
| **AMPLIACION** | Cuando se necesita más dinero a mitad de obra. Suma al saldo. |
| **REDUCCION** | Cuando se retira dinero de la obra. Resta del saldo. |
| **AJUSTE** | Corrección manual del asignado (conciliaciones). |

### 6.2 Crear una asignación

1. Abre el detalle de la obra.
2. En la sección **Fondos**, click en **+ Nueva asignación**.
3. Llena:
 - **Fecha**: cuándo se asigna
 - **Tipo**: INICIAL, AMPLIACION, REDUCCION o AJUSTE
 - **Monto**: importe (positivo)
 - **Referencia**: número de transferencia, oficio, etc.
4. Guarda.

> 📌 El campo "Obra" viene preseleccionado si entraste desde el
> detalle de la obra. Si entraste desde el menú lateral, elige la
> obra manualmente.

### 6.3 Cómo se reflejan en el saldo

| Tipo | Efecto en el saldo |
|---|---|
| INICIAL | Suma al asignado |
| AMPLIACION | Suma al asignado |
| REDUCCION | Resta del asignado |
| AJUSTE | Suma o resta según el monto (puede ser negativo) |

Solo cuentan las asignaciones **NO anuladas** (campo `anulada=False`).

### 6.4 Anular una asignación mal creada

Si te equivocaste al crear una asignación:

1. Ve al **Listado de Asignaciones** (Operación → Asignaciones de fondo).
2. Encuentra la asignación incorrecta.
3. Click en el botón 🚫 **Anular**.
4. Confirma.

> ⚠ **No se puede borrar físicamente** una asignación, solo anular.
> Esto preserva la trazabilidad: queda registro de que existió.

### 6.5 Ejemplo: presupuesto inicial + ampliación

```
1. Obra "Edificio Las Palmas" creada el 15/01/2026.
2. Asignación INICIAL: $500,000 (presupuesto original).
3. Saldo: $500,000.
4. Mayo: se requiere más material. Asignación AMPLIACION: $150,000.
5. Nuevo saldo: $650,000.
6. Si te equivocaste en la ampliación, click en 🚫 → saldo vuelve a $500,000.
```

---

## 7. Registrando gastos

Los gastos se registran desde el **menú lateral → Operación** o
directamente desde el **detalle de la obra**.

### 7.1 Antes de gastar: las 3 reglas

1. **Debe haber saldo disponible** en la obra.
2. **Cada gasto tiene un documento origen** (factura, nómina, uso de
   maquinaria u otro).
3. **Solo APROBADO afecta el saldo.** Crea el gasto en BORRADOR,
   revísalo, luego apruébalo.

### 7.2 Compra con factura (caso más común)

Una factura de proveedor es la forma más habitual de cargar un gasto.
Ejemplo: compramos 200 sacos de cemento por $5,000.

**Paso 1 — Crear la factura**

1. Menú → Operación → Facturas → **+ Nueva factura**.
2. Llena:
 - **Obra**: la obra destino
 - **Proveedor**: selecciónalo del catálogo
 - **Gasto**: (déjalo en blanco por ahora)
 - **Folio**: número de factura del proveedor (ej: FAC-1234)
 - **Fecha de emisión**
 - **Impuesto**: monto del IVA
 - **Total**: total de la factura (subtotal + impuesto)
 - **Estado de pago**: PENDIENTE
3. Guarda.

> 📌 El sistema crea automáticamente un GastoObra vinculado.

**Paso 2 — Agregar las líneas de detalle**

1. En el detalle de la factura, click en **+ Agregar línea**.
2. Llena:
 - **Material**: del catálogo
 - **Cantidad**: 200
 - **Precio unitario**: 25.00
3. Guarda.

**Paso 3 — Verificar consistencia**

La factura debe cumplir: `SUM(cantidad × precio_unitario) + impuesto = total`.

- ✅ Consistente: badge verde "Consistente".
- ❌ Inconsistente: badge ámbar "Esperado: $X". Edita el total o las
  líneas hasta que coincidan.

**Paso 4 — Aprobar el gasto**

1. Ve a Operación → Gastos.
2. Encuentra el gasto recién creado (estado BORRADOR).
3. Click en **Editar** → cambia estado a **APROBADO** → guarda.

¡Listo! El saldo de la obra se reduce automáticamente.

### 7.3 Pago de nómina

Una nómina es el pago al personal asignado a la obra durante un
período (quincenal, mensual, etc.).

**Paso 1 — Crear la cabecera de la nómina**

1. Menú → Personal → Nóminas → **+ Nueva nómina**.
2. Llena:
 - **Obra**: la obra
 - **Gasto**: (déjalo en blanco; se calcula)
 - **Fecha**: día del pago
 - **Periodo desde / hasta**: rango cubierto
3. Guarda.

**Paso 2 — Agregar empleados**

1. En el detalle de la nómina, click en **+ Agregar empleado**.
2. Llena: empleado + monto a pagar.
3. Repite para cada empleado.

**Paso 3 — Recalcular total**

1. En el detalle de la nómina, click en **🔄 Recalcular total desde detalles**.
2. El sistema suma todas las líneas y actualiza el GastoObra.

**Paso 4 — Aprobar**

Editar → cambiar estado a APROBADO.

### 7.4 Uso de maquinaria

Cuando una máquina (excavadora, mezcladora, etc.) se usa en una obra:

1. Menú → Maquinaria → Usos → **+ Nuevo uso**.
2. Llena:
 - **Obra**: la obra
 - **Maquinaria**: del catálogo
 - **Gasto**: (déjalo en blanco)
 - **Fecha**: día del uso
 - **Horas**: horas trabajadas
3. Guarda.

> 📌 El monto se calcula automáticamente: `horas × costo_hora`.
> Ej: 8 horas × $100/h = $800.

### 7.5 Otros gastos (multas, permisos, etc.)

Para gastos que no tienen factura, nómina ni maquinaria asociada:

1. Menú → Operación → Otros gastos → **+ Nuevo otro gasto**.
2. Llena:
 - **Obra**: la obra
 - **Gasto**: del catálogo de GastoObra (déjalo en blanco si el sistema debe crearlo)
 - **Fecha**, **Concepto**, **Comprobante**, **Proveedor** (opcional)
3. Guarda.

### 7.6 Aprobar un gasto (cambiar de BORRADOR a APROBADO)

1. Menú → Operación → Gastos.
2. Filtra por estado: `?estado=BORRADOR`.
3. Para cada gasto a aprobar:
 - Click en **✏ Editar**.
 - Cambia **Estado** a APROBADO.
 - Guarda.

> 💡 **Buena práctica**: revisa los gastos en BORRADOR al final del día
> y apruébalos en lote.

### 7.7 Corregir un error (anular + crear nuevo)

**Nunca borres un gasto financiero.** Si te equivocaste:

1. Encuentra el gasto incorrecto.
2. Click en 🚫 **Anular** → confirma.
3. Crea un nuevo gasto con los datos correctos.

La asignación queda registrada con estado ANULADO, lo que preserva la
trazabilidad.

### 7.8 Cuándo se actualiza el saldo

**Inmediatamente.** El saldo no se guarda en la base de datos, se
calcula cada vez que alguien lo consulta.

| Acción | Efecto inmediato en el saldo |
|---|---|
| Crear asignación INICIAL | +monto al asignado |
| Crear gasto APROBADO | -monto al gastado |
| Anular gasto APROBADO | +monto al gastado (vuelve al saldo) |
| Anular asignación | -monto del asignado (reduce saldo) |
| Crear gasto BORRADOR | **Ningún efecto** (no aprobado) |

---

## 8. Proveedores y facturas

### 8.1 Alta de proveedor

1. Menú → Operación → Proveedores → **+ Nuevo proveedor**.
2. Llena:
 - **Nombre** (obligatorio)
 - **Identificación** (RFC, NIT, RIF, etc.) — debe ser única
 - Teléfono, email, dirección (opcionales)
 - **Activo**: sí (default)
3. Guarda.

### 8.2 Crear una factura con líneas

Ver sección **7.2 Compra con factura** (arriba).

### 8.3 Entender la consistencia (subtotal + impuesto = total)

Cada factura tiene un campo `total` que debe coincidir con:

```
SUM(cantidad × precio_unitario de las líneas) + impuesto = total
```

El sistema lo verifica automáticamente. Si la factura está
inconsistente:

- **Badge ámbar** "Esperado: $X" en el detalle.
- Edita las líneas o el total hasta que cuadre.

### 8.4 Estados de pago (independientes del estado del gasto)

Una factura tiene su propio ciclo de pago:

| Estado | Significado |
|---|---|
| PENDIENTE | La factura existe pero no se ha pagado al proveedor |
| PARCIAL | Se pagó parte |
| PAGADO | Se pagó completa |

> 📌 **Importante**: el estado de pago de la factura es independiente
> del estado del gasto. Una factura PENDIENTE puede tener su gasto
> APROBADO. Eso es normal: el gasto afecta el saldo apenas se aprueba,
> independientemente de cuándo se pague al proveedor.

### 8.5 Borrar vs anular

| Acción | Cuándo |
|---|---|
| **Borrar** 🗑 | Solo para facturas recién creadas con error de digitación evidente y que **no** tengan un GastoObra aprobado. |
| **Anular** 🚫 | Facturas con flujo ya iniciado. Se anula la factura y, si querés, se anula también el gasto asociado. |

> ⚠ Si intentás borrar una factura con GastoObra aprobado, el sistema
> no te dejará. Solución: anula el gasto primero, luego anula la factura.

---

## 9. Inventario y materiales

### 9.1 Alta de material

1. Menú → Inventario → Materiales → **+ Nuevo material**.
2. Llena:
 - **Nombre** (obligatorio)
 - **Unidad** (saco, kg, m3, pieza, etc.)
 - **Categoría** (construcción, acero, plomería, etc.)
 - **Precio unitario de referencia** (opcional, para informes)
3. Guarda.

### 9.2 Ver stock por obra

1. Menú → Inventario → Stock por obra.
2. Filtra por obra: `?obra=6` (o click en una obra desde su detalle).
3. Verás: material, cantidad actual, última actualización.

### 9.3 Registrar movimientos

Un movimiento es un evento de stock: una entrada de material, una
salida a obra, una transferencia, etc.

1. Menú → Inventario → Movimientos → **+ Nuevo movimiento**.
2. Llena: obra, material, usuario (tú), tipo (ENTRADA, SALIDA,
   TRANSFERENCIA, DEVOLUCION, AJUSTE), cantidad, fecha.
3. Guarda.

### 9.4 Importante: el form libre no actualiza el stock

> ⚠ **REGLA CRÍTICA**: cuando creas un `MovimientoMaterial` desde el
> formulario anterior, **el stock en `InventarioObra` NO se modifica**.
> El stock solo se actualiza mediante los **servicios transaccionales**
> internos (`registrar_entrada_material`, `registrar_salida_material`,
> `ajustar_inventario`, etc.).

En el MVP actual, los movimientos desde el form libre quedan en el
historial pero no afectan el stock físico. Para una versión definitiva
del control de inventario, se recomienda usar un formulario dedicado
que invoque el servicio correspondiente.

### 9.5 Por qué este diseño

- **Historial** (MovimientoMaterial) y **estado actual**
  (InventarioObra) son cosas distintas.
- Un mismo evento (ej: "entregué 100 sacos de cemento") puede implicar
  varios movimientos (entrada al stock + salida a obra).
- Mantener la consistencia entre ambos requiere operaciones
  atómicas que eviten duplicar efectos.

---

## 10. Personal y nóminas

### 10.1 Alta de empleado

1. Menú → Personal → Empleados → **+ Nuevo empleado**.
2. Llena:
 - **Cédula** (obligatorio, único)
 - **Nombres** (obligatorio)
 - **Apellidos** (obligatorio)
 - **Cargo** (Maestro, Albañil, Ingeniero, etc.)
 - **Salario diario** (obligatorio, decimal)
3. Guarda.

### 10.2 Crear una nómina: cabecera + líneas

Ver sección **7.3 Pago de nómina** (arriba).

### 10.3 Recalcular total (botón clave)

Si editas manualmente las líneas (agregas o quitas empleados, cambias
montos), el total de la cabecera puede quedar desactualizado.

**Solución**: en el detalle de la nómina, click en **🔄 Recalcular
total desde detalles**. Esto:

1. Suma todas las líneas.
2. Actualiza el `GastoObra.monto` asociado.

> 📌 **Es una operación explícita**, no automática. Decidí cuándo
> recalcular (por ejemplo, al cerrar la nómina).

### 10.4 Anular una nómina

1. Menú → Personal → Nóminas.
2. Encuentra la nómina.
3. Click en 🚫 **Anular** → confirma.

> Al anular la nómina se anula también el GastoObra asociado, por lo
> que el saldo de la obra se restaura.

---

## 11. Maquinaria

### 11.1 Alta con costo/hora

1. Menú → Maquinaria → Catálogo → **+ Nueva maquinaria**.
2. Llena:
 - **Nombre** (Excavadora, Mezcladora, etc.)
 - Marca, modelo, identificación
 - **Costo/hora** (decimal)
3. Guarda.

### 11.2 Registrar uso: el monto se calcula automático

Ver sección **7.4 Uso de maquinaria** (arriba).

Ejemplo:

```
Excavadora CAT 320D (costo $100/hora) se usa 8 horas en una obra
→ Uso: 8h × $100/h = $800
→ GastoObra automático por $800
→ Al aprobarse: el saldo de la obra baja $800
```

---

## 12. Otros gastos

### 12.1 Cuándo usar este módulo

Usa **Otros gastos** para registrar gastos que **no tienen** factura,
nómina ni maquinaria asociada. Ejemplos típicos:

- Multas municipales
- Permisos / licencias
- Combustible sin factura (con vale)
- Comida de personal en obra
- Cualquier egreso sin documento formal

### 12.2 Siempre se asocian a un GastoObra

Al crear un "Otro gasto" el sistema crea automáticamente un `GastoObra`
asociado. El monto vive en `GastoObra.monto` (no en OtroGasto).

---

## 13. Reportes

### 13.1 Reporte PDF de obra individual

Disponible desde el detalle de cualquier obra, click en **Reporte PDF**.

Contiene:

- Header con datos de la obra (nombre, estado, ubicación, fechas)
- KPIs financieros (asignado, gastado, saldo, % ejecución)
- Tabla de asignaciones de fondo
- Tabla de gastos (últimos 20)
- Tabla de facturas de proveedores
- Pie con fecha/hora y usuario que generó el reporte

> 💡 Usos: cierres mensuales, presentaciones, respaldos documentales.

### 13.2 Reportes globales (pendientes)

Aún no implementados:

- Balance de todas las obras
- Listado de gastos por período
- Gráficos comparativos entre obras
- Exportación a Excel

---

## 14. Preguntas frecuentes

### "Creé un movimiento de material pero el stock no cambió"

Es un comportamiento esperado del MVP. Los movimientos creados desde el
formulario libre quedan en el historial pero **no actualizan el
stock**. Ver sección 9.4.

### "El saldo no cuadra con lo que esperaba"

Verifica estos puntos:

1. ¿Hay asignaciones **anuladas**? No cuentan.
2. ¿Hay gastos en **BORRADOR**? No afectan saldo.
3. ¿Hay gastos **ANULADOS**? No afectan saldo.
4. ¿La asignación es de tipo **REDUCCION** o **AJUSTE** negativo? Resta.

### "Anulé un gasto pero sigue apareciendo como activo"

Refresca la página. Si persiste, verifica que la URL tenga el filtro
correcto (por defecto el listado muestra todos los estados, incluidos
ANULADOS — pero tachados).

### "No puedo borrar una factura"

Si la factura tiene un **GastoObra aprobado** asociado, el sistema
protege la integridad y no permite borrarla. Solución:

1. Ve a Operación → Gastos.
2. Encuentra el gasto de la factura.
3. Click en 🚫 **Anular**.
4. Vuelve a la factura y vuelve a intentar.

### "El reporte PDF está vacío"

El reporte muestra los últimos 20 gastos y facturas. Si la obra no
tiene ninguno, los bloques aparecen vacíos. Esto es normal.

### "Olvidé mi contraseña"

Funcionalidad **pendiente**. Por ahora, contacta al administrador del
sistema para que la restablezca directamente en la base de datos.

### "El sistema está lento"

Puede deberse a:

- Muchos movimientos de inventario en el mismo día.
- Múltiples usuarios consultando reportes PDF al mismo tiempo.

Si persiste, contacta al administrador.

### "¿Por qué este gasto no aparece en el saldo?"

Verifica su **estado**:

- BORRADOR → no aparece
- APROBADO → aparece (resta del saldo)
- ANULADO → no aparece

Si está en BORRADOR, cámbialo a APROBADO desde Editar.

### "¿Puedo cambiar el monto de un gasto ya aprobado?"

**No directamente.** Si necesitas corregirlo:

1. Anula el gasto (🚫).
2. Crea un nuevo gasto con el monto correcto.
3. Apruébalo.

### "¿Por qué la factura dice 'Esperado: $X'?"

La factura no cuadra con sus líneas. Ver sección 8.3.

---

## 15. Buenas prácticas

1. **Revisa el dashboard al inicio del día.** Te da una vista
   panorámica de todas las obras en segundos.

2. **Anula en lugar de borrar.** Toda operación financiera
   (asignación, gasto, factura, nómina, uso) se puede anular pero
   **no borrar físicamente**. Esto preserva la trazabilidad.

3. **Aprueba gastos en lote.** Al final del día, ve a Operación →
   Gastos → filtra por `?estado=BORRADOR` y aprueba de a varios.

4. **Documenta las observaciones.** Usa los campos de observaciones,
   referencia y comprobante para dejar rastro de cada operación
   importante.

5. **Carga primero los catálogos.** Antes de registrar gastos, ten
   dados de alta los proveedores, materiales, empleados y
   maquinarias que vas a usar.

6. **Genera reportes PDF regularmente.** Una vez al mes o al
   culminar cada fase importante. Es tu respaldo documental.

7. **Verifica la consistencia de las facturas** antes de aprobar
   sus gastos. Una factura inconsistente genera alertas en el
   reporte PDF.

8. **No mezcles roles de edición.** Hoy todos los usuarios tienen
   acceso completo. Cuando se implemente roles (pendiente), el
   operador de captura y el aprobador serán usuarios distintos.

---

## 16. Glosario

| Término | Definición |
|---|---|
| **Obra** | Proyecto de construcción. Unidad principal del sistema. |
| **Asignación de fondo** | Dinero que la empresa pone a disposición de una obra. |
| **Gasto** | Egreso contra una obra. Siempre tiene un documento origen. |
| **Documento origen** | Factura, nómina, uso de maquinaria u otro gasto. |
| **Saldo** | Diferencia entre asignaciones y gastos aprobados. |
| **APROBADO** | Estado de un gasto cuando ya es definitivo. |
| **BORRADOR** | Estado de un gasto pendiente de aprobación. |
| **ANULADO** | Estado de un gasto cancelado (no afecta saldo). |
| **Material** | Insumo usado en obra (cemento, arena, etc.). |
| **Movimiento de material** | Evento de stock (entrada, salida, etc.). |
| **Inventario** | Cantidad actual de un material en una obra. |
| **Nómina** | Pago al personal por un período. |
| **Uso de maquinaria** | Registro de horas-máquina usadas en una obra. |
| **Proveedor** | Empresa externa que vende materiales o servicios. |
| **Factura** | Documento emitido por un proveedor. |
| **Detalle de factura** | Línea de producto dentro de una factura. |
| **Reporte PDF** | Documento descargable con el resumen de una obra. |
| **Dashboard** | Pantalla principal con KPIs globales. |
| **Sidebar** | Menú lateral de navegación. |
| **KPI** | Indicador clave de rendimiento (asignado, gastado, % ejecución). |
| **Consistencia** | Una factura es consistente si `total = suma_subtotal + impuesto`. |
| **Trazabilidad** | Capacidad de seguir el origen de cada gasto. |
| **Anular** | Marcar una operación como cancelada sin borrarla. |
| **Borrar** | Eliminar físicamente un registro (solo para entidades no financieras). |

---

## 17. Pendientes con el cliente

Los siguientes puntos están en desarrollo o pendientes de validación
con el cliente:

### Implementación próxima

- **Roles y permisos** (ADMIN / OPERADOR / CONSULTA). Hoy todos los
  usuarios autenticados tienen acceso completo.
- **Reset de contraseña** desde la UI.
- **Cambio de contraseña** desde la UI del usuario.
- **Reportes globales** (balance de obras, gastos por período, Excel).
- **Auditoría** (registrar quién modificó qué y cuándo).
- **Notificaciones** (alertas por saldo bajo, gastos pendientes, etc.).

### Pendientes de validación con cliente

- **Wizard de creación** de factura con líneas en un solo paso.
- **Importar XML de facturas** (CFDI) automáticamente.
- **Estados adicionales de nómina** (quincenal, mensual).
- **Workflow de aprobación** de gastos (BORRADOR → REVISION → APROBADO)
  con usuario aprobador distinto del que crea.

### Cómo reportar feedback

Si encuentras un problema, una inconsistencia o tienes una sugerencia:

1. Anota el caso: qué hiciste, qué esperabas, qué pasó.
2. Toma captura de pantalla si es posible.
3. Envíalo al equipo de desarrollo con la mayor cantidad de detalle.

---

**Fin del manual.**

> Si este manual queda desactualizado tras una nueva versión del
> sistema, repórtalo al equipo de desarrollo para su actualización.