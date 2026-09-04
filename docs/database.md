# SGCO — Documentación de Base de Datos

> Sistema de Gestión y Control de Obras.
> Eje: **OBRA → FONDOS ASIGNADOS → GASTOS → SALDO → TRAZABILIDAD**

---

## 1. Estructura de apps

```
sgco/
└── apps/
    ├── core/         # Choices compartidos, utilidades comunes
    ├── obras/        # Obra
    ├── fondos/       # AsignacionFondo
    ├── finanzas/     # GastoObra, OtroGasto  (representación financiera central)
    ├── proveedores/  # Proveedor, FacturaProveedor, DetalleFactura
    ├── inventario/   # Material, InventarioObra, MovimientoMaterial
    ├── personal/     # Empleado, Nomina, NominaDetalle
    └── maquinaria/   # Maquinaria, UsoMaquinaria
```

---

## 2. Entidades, campos y relaciones

### 2.1 `Obra` (`apps.obras`)
| Campo | Tipo | Notas |
|---|---|---|
| `nombre` | CharField(150) | |
| `ubicacion` | CharField(200) | |
| `fecha_inicio` | DateField | |
| `fecha_fin_estimada` | DateField | |
| `estado` | CharField(20) | choices: EstadoObraChoices |
| `created_at` | DateTimeField | auto_now_add |
| `updated_at` | DateTimeField | auto |

**Relaciones**
- 1:N → `AsignacionFondo`
- 1:N → `GastoObra`
- 1:N → `FacturaProveedor`
- 1:N → `InventarioObra`
- 1:N → `MovimientoMaterial`
- 1:N → `Nomina`
- 1:N → `UsoMaquinaria`
- 1:N → `OtroGasto`

---

### 2.2 `AsignacionFondo` (`apps.fondos`)
| Campo | Tipo | Notas |
|---|---|---|
| `obra` | FK Obra (PROTECT) | |
| `fecha` | DateField | |
| `monto` | DecimalField(14,2) | fuente del asignado |
| `tipo` | CharField(20) | INICIAL, AMPLIACION, REDUCCION, AJUSTE |
| `referencia` | CharField(100) | |
| `observaciones` | TextField | |

**Relación**: OBRA 1:N ASIGNACION_FONDO.

---

### 2.3 `GastoObra` (`apps.finanzas`)
| Campo | Tipo | Notas |
|---|---|---|
| `obra` | FK Obra (PROTECT) | |
| `fecha` | DateField | |
| `tipo_gasto` | CharField(20) | MATERIAL, PERSONAL, MAQUINARIA, COMBUSTIBLE, SERVICIO, TRANSPORTE, OTROS |
| `descripcion` | CharField(200) | |
| `monto` | DecimalField(14,2) | **fuente de verdad del monto** |
| `estado` | CharField(20) | BORRADOR, APROBADO, ANULADO |

**Relaciones**
- 1:N ← `Obra`
- 1:1 ← `FacturaProveedor`
- 1:1 ← `Nomina`
- 1:1 ← `UsoMaquinaria`
- 1:1 ← `OtroGasto`

> **No tiene `proveedor_id` directo**. Se obtiene transitando por la factura o documento origen.

---

### 2.4 `OtroGasto` (`apps.finanzas`)
| Campo | Tipo | Notas |
|---|---|---|
| `obra` | FK Obra (PROTECT) | |
| `gasto` | OneToOne GastoObra (PROTECT) | monto vive en GastoObra |
| `fecha` | DateField | |
| `concepto` | CharField(200) | |
| `comprobante` | CharField(100) | |
| `proveedor` | FK Proveedor (SET_NULL) | opcional |
| `observaciones` | TextField | |

> **No tiene monto propio**. El monto pertenece siempre a `GastoObra.monto`.

---

### 2.5 `Proveedor` (`apps.proveedores`)
| Campo | Tipo |
|---|---|
| `nombre` | CharField(200) |
| `identificacion` | CharField(30), **unique**, opcional |
| `telefono` | CharField(20) |
| `email` | EmailField |
| `direccion` | CharField(250) |
| `activo` | BooleanField |

---

### 2.6 `FacturaProveedor` (`apps.proveedores`)
| Campo | Tipo |
|---|---|
| `obra` | FK Obra (PROTECT) |
| `proveedor` | FK Proveedor (PROTECT) |
| `gasto` | OneToOne GastoObra (PROTECT) |
| `folio` | CharField(50) |
| `fecha_emision` | DateField |
| `impuesto` | DecimalField(14,2), default 0 |
| `total` | DecimalField(14,2) |
| `estado` | CharField(20): PENDIENTE, PARCIAL, PAGADO |

**Unique**: `(proveedor, folio)`.

**Consistencia (regla de la spec):**
```
FacturaProveedor.subtotal  = SUM(DetalleFactura.cantidad * DetalleFactura.precio_unitario)
FacturaProveedor.total_calculado = subtotal + impuesto
es_consistente() = (total == total_calculado)
```

La verificación y el recálculo se hacen mediante
`apps.proveedores.services` (`verificar_consistencia_factura`,
`actualizar_total_desde_detalles`, `exigir_consistencia_factura`).

---

### 2.7 `DetalleFactura` (`apps.proveedores`)
| Campo | Tipo |
|---|---|
| `factura` | FK FacturaProveedor (CASCADE) |
| `material` | FK Material (PROTECT) |
| `cantidad` | DecimalField(10,2) |
| `precio_unitario` | DecimalField(12,2) |

> **Material es obligatorio** en cada línea de detalle (regla de la spec).

---

### 2.8 `Material` (`apps.inventario`)
| Campo | Tipo |
|---|---|
| `nombre` | CharField(150) |
| `unidad` | CharField(30) |
| `categoria` | CharField(80) |
| `precio_unitario_referencia` | DecimalField(12,2) |
| `activo` | BooleanField |

---

### 2.9 `InventarioObra` (`apps.inventario`)
| Campo | Tipo |
|---|---|
| `obra` | FK Obra (PROTECT) |
| `material` | FK Material (PROTECT) |
| `cantidad_actual` | DecimalField(12,2) |

**Unique**: `(obra, material)`.

> Estado actual. Se modifica mediante servicios transaccionales, nunca desde `MovimientoMaterial.save()`.

---

### 2.10 `MovimientoMaterial` (`apps.inventario`)
| Campo | Tipo |
|---|---|
| `obra` | FK Obra (PROTECT) |
| `material` | FK Material (PROTECT) |
| `usuario` | FK auth.User (PROTECT) |
| `tipo` | CharField(20): ENTRADA, SALIDA, TRANSFERENCIA, DEVOLUCION, AJUSTE |
| `cantidad` | DecimalField(12,2) |
| `fecha` | DateField |
| `referencia` | CharField(100) |
| `observaciones` | TextField |

> Historial. **No aplica efectos secundarios en `save()`**.

---

### 2.11 `Empleado` (`apps.personal`)
| Campo | Tipo |
|---|---|
| `cedula` | CharField(20), **unique** |
| `nombres` | CharField(100) |
| `apellidos` | CharField(100) |
| `cargo` | CharField(100) |
| `salario_diario` | DecimalField(10,2) |
| `activo` | BooleanField |

> Sin tipo_empleado, contrato, prestaciones, vacaciones ni deducciones en esta fase.

---

### 2.12 `Nomina` (`apps.personal`)
| Campo | Tipo |
|---|---|
| `obra` | FK Obra (PROTECT) |
| `gasto` | OneToOne GastoObra (PROTECT) |
| `fecha` | DateField |
| `periodo_desde` | DateField |
| `periodo_hasta` | DateField |

**Unique**: `(obra, periodo_desde, periodo_hasta)`.

---

### 2.13 `NominaDetalle` (`apps.personal`)
| Campo | Tipo |
|---|---|
| `nomina` | FK Nomina (CASCADE) |
| `empleado` | FK Empleado (PROTECT) |
| `monto` | DecimalField(12,2) |

**Unique**: `(nomina, empleado)`.

---

### 2.14 `Maquinaria` (`apps.maquinaria`)
| Campo | Tipo |
|---|---|
| `nombre` | CharField(150) |
| `marca` | CharField(100) |
| `modelo` | CharField(100) |
| `identificacion` | CharField(50) |
| `costo_hora` | DecimalField(10,2) |
| `activo` | BooleanField |

---

### 2.15 `UsoMaquinaria` (`apps.maquinaria`)
| Campo | Tipo |
|---|---|
| `obra` | FK Obra (PROTECT) |
| `maquinaria` | FK Maquinaria (PROTECT) |
| `gasto` | OneToOne GastoObra (PROTECT) |
| `fecha` | DateField |
| `horas` | DecimalField(8,2) |

---

## 3. Cardinalidades (resumen)

| Relación | Tipo |
|---|---|
| OBRA 1:N ASIGNACION_FONDO | OneToMany |
| OBRA 1:N GASTO_OBRA | OneToMany |
| OBRA 1:N FACTURA_PROVEEDOR | OneToMany |
| PROVEEDOR 1:N FACTURA_PROVEEDOR | OneToMany |
| GASTO_OBRA 1:1 FACTURA_PROVEEDOR | OneToOne |
| FACTURA_PROVEEDOR 1:N DETALLE_FACTURA | OneToMany |
| MATERIAL 1:N DETALLE_FACTURA | OneToMany |
| OBRA 1:N INVENTARIO_OBRA | OneToMany |
| MATERIAL 1:N INVENTARIO_OBRA | OneToMany |
| OBRA 1:N MOVIMIENTO_MATERIAL | OneToMany |
| MATERIAL 1:N MOVIMIENTO_MATERIAL | OneToMany |
| USUARIO 1:N MOVIMIENTO_MATERIAL | OneToMany |
| OBRA 1:N NOMINA | OneToMany |
| GASTO_OBRA 1:1 NOMINA | OneToOne |
| NOMINA 1:N NOMINA_DETALLE | OneToMany |
| EMPLEADO 1:N NOMINA_DETALLE | OneToMany |
| OBRA 1:N USO_MAQUINARIA | OneToMany |
| MAQUINARIA 1:N USO_MAQUINARIA | OneToMany |
| GASTO_OBRA 1:1 USO_MAQUINARIA | OneToOne |
| OBRA 1:N OTRO_GASTO | OneToMany |
| GASTO_OBRA 1:1 OTRO_GASTO | OneToOne |

---

## 4. Reglas financieras

```
TOTAL_ASIGNADO = SUM(AsignacionFondo.monto)

TOTAL_GASTADO  = SUM(GastoObra.monto WHERE estado = APROBADO)

SALDO          = TOTAL_ASIGNADO - TOTAL_GASTADO

PORCENTAJE_EJECUCION = TOTAL_GASTADO / TOTAL_ASIGNADO * 100
                       (0 si TOTAL_ASIGNADO = 0)
```

**Estado de gasto ≠ estado de factura.** Ambos pueden evolucionar por separado.
- Un gasto APROBADO afecta el saldo aunque la factura siga PENDIENTE.
- Una factura PAGADA no implica que su gasto esté APROBADO.

**Estados de GastoObra**
- `BORRADOR` — no afecta saldo.
- `APROBADO` — afecta saldo.
- `ANULADO` — no afecta saldo (no se borra físicamente).

**Estados de FacturaProveedor**
- `PENDIENTE` / `PARCIAL` / `PAGADO` — sólo controlan el pago, no el saldo.

---

## 5. Servicios transaccionales

### 5.1 Inventario (`apps.inventario.services`)

| Función | Efecto |
|---|---|
| `registrar_entrada_material()` | Suma a `InventarioObra` + crea `MovimientoMaterial` ENTRADA |
| `registrar_salida_material()` | Resta a `InventarioObra` + crea `MovimientoMaterial` SALIDA |
| `registrar_devolucion_material()` | Suma a `InventarioObra` + crea `MovimientoMaterial` DEVOLUCION |
| `registrar_transferencia_material()` | Resta en origen + suma en destino + crea 2 movimientos TRANSFERENCIA |
| `ajustar_inventario()` | Reemplaza `cantidad_actual` + crea `MovimientoMaterial` AJUSTE |

Todas usan `transaction.atomic()`.

### 5.2 Finanzas (`apps.finanzas.services`)

| Función | Efecto |
|---|---|
| `total_asignado(obra)` | SUM(AsignacionFondo.monto) |
| `total_gastado(obra)` | SUM(GastoObra.monto WHERE estado=APROBADO) |
| `saldo(obra)` | asignado − gastado |
| `porcentaje_ejecucion(obra)` | gastado / asignado * 100, sin dividir por cero |
| `crear_gasto_con_factura()` | Crea GastoObra + FacturaProveedor atómicamente |
| `crear_otro_gasto()` | Crea GastoObra + OtroGasto atómicamente |
| `crear_nomina_con_gasto()` | Crea GastoObra + Nomina + NominaDetalle atómicamente |
| `crear_uso_maquinaria_con_gasto()` | Crea GastoObra + UsoMaquinaria atómicamente |
| `anular_gasto(gasto)` | Marca como ANULADO (no borra) |

### 5.3 Personal (`apps.personal.services`)

| Función | Efecto |
|---|---|
| `recalcular_total_nomina(nomina)` | SUM(NominaDetalle.monto) → actualiza GastoObra.monto |

### 5.4 Proveedores (`apps.proveedores.services`)

| Función | Efecto |
|---|---|
| `registrar_detalle_factura()` | Crea un DetalleFactura (no toca `total`) |
| `actualizar_total_desde_detalles(factura)` | `total = suma(subtotal) + impuesto` |
| `verificar_consistencia_factura(factura)` | True si total == calculado |
| `exigir_consistencia_factura(factura)` | Lanza `ValidationError` si no coincide |

---

## 6. Decisiones de diseño

1. **No hay tablas de catálogo**. Todos los valores finitos usan `TextChoices`.
2. **No hay lógica en `save()`** de `MovimientoMaterial`, `NominaDetalle` ni `DetalleFactura`.
3. **GastoObra es la representación financiera central**. Documentos (Factura, Nomina, UsoMaquinaria, OtroGasto) generan GastoObra en transacciones atómicas.
4. **No hay borrado físico** indiscriminado en operaciones financieras. Preferir anulación / desactivación.
5. **DetalleFactura.material** es obligatorio. La factura es por materiales de la obra.
6. **OtroGasto NO tiene monto propio**. El monto es siempre `GastoObra.monto`.
7. **Proveedor se obtiene transitando** GastoObra → FacturaProveedor → Proveedor.

---

## 7. Supuestos

- `cedula` (única) se considera identificador del empleado.
- `identificacion` (única) en Proveedor actúa como RFC/TaxID/RIF.
- `auth.User` de `django.contrib.auth` se usa como `usuario` de MovimientoMaterial.
- `FacturaProveedor.total` es campo explícito editable; la consistencia
  con `suma(DetalleFactura.subtotal) + impuesto` se verifica mediante
  servicios (no se recalcula implícitamente en `save()`).
- `OtroGasto.proveedor` es opcional (`null=True, blank=True, on_delete=SET_NULL`).

---

## 8. Pendientes de validación

- ¿Conviene cambiar `cedula` por `rfc`? (legal/tributario)
- ¿La FK `obra` en `FacturaProveedor` debe existir, o basta con `gasto.obra`?
- ¿`activo` debería ser `estado` con TextChoices en lugar de BooleanField?
- ¿`horas` en UsoMaquinaria debe aceptar `Decimal` o sólo enteros?
- ¿`Periodo` de nómina debe ser quincenal/ semanal / mensual como choices?
- ¿`categoria` en Material debe tener catálogo propio en próximas fases?
- ¿Conviene que `total` de FacturaProveedor se fuerce siempre via `actualizar_total_desde_detalles`
  o se permite edicion manual?

---

## 9. Comandos rápidos

```bash
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py test apps
python manage.py runserver
```

Usuario admin por defecto: **admin / admin123**.