# SGCO — Diagramas de flujo

> Diagramas en ASCII art que documentan el funcionamiento de los procesos
> clave del sistema. Complementan a `docs/database.md` (modelos y reglas
> financieras) y al código de `apps/*/services.py`.

---

## 0. Leyenda

```
  ┌─────────────┐
  │   Proceso   │   → bloque de acción o vista
  └─────────────┘
       │
       ▼
  ┌─────────────┐
  │   Estado /  │   → dato, modelo o resultado
  │   Modelo    │
  └─────────────┘

  [Sí]   → camino cuando la condición se cumple
  [No]   → camino contrario

  ╔═════════╗
  ║ Decisión║   → bifurcación (sí/no)
  ╚═════════╝

  ═══════>   → flujo principal
  ·······>   → flujo opcional / secundario
```

---

## 1. Navegación del usuario (demo principal)

```
                              ┌────────────────────┐
                              │  GET / (no auth)   │
                              └─────────┬──────────┘
                                        │ 302
                                        ▼
                              ┌────────────────────┐
                              │   /login/ (form)   │
                              └─────────┬──────────┘
                                        │ POST admin/admin123
                                        ▼
                              ┌────────────────────┐
                              │  / (Dashboard)     │
                              │  KPIs + gráficos   │
                              └─────────┬──────────┘
                                        │ click en una obra
                                        ▼
   ┌────────────────────────────────────────────────────┐
   │              /obras/<id>/ (Detalle)                │
   │  Resumen + secciones ancladas:                     │
   └──────┬─────────┬─────────┬─────────┬─────────┬─────┘
          │         │         │         │         │
          ▼         ▼         ▼         ▼         ▼
      ┌──────┐  ┌──────┐  ┌────────┐ ┌──────┐ ┌────────┐
      │Fondos│  │Gastos│  │Facturas│ │Invent│ │Maquina│
      └──┬───┘  └──┬───┘  └───┬────┘ └──┬───┘ └───┬────┘
         │         │          │         │          │
         ▼         ▼          ▼         ▼          ▼
       "+Nueva"   "+Nuevo"   "+Nueva"  ver      "+Nuevo"
       Anular     Anular     Detalle   stock    Anular
       Editar     Drill-down Consisten
```

Acciones disponibles por sección (en la pantalla de la obra):

```
  ┌─────────────┐    Sí    ┌─────────────────────┐
  │ ¿Entidad    ├────────► │ Anular servicio     │
  │ financiera? │          │ (apps.finanzas.     │
  └──────┬──────┘          │  services.anular_*) │
         │ No              └─────────────────────┘
         ▼
  ┌─────────────────────┐
  │ DeleteView (borrar)  │
  └─────────────────────┘
```

---

## 2. Regla financiera — SALDO = ASIGNADO − GASTO_APROBADO

```
   ┌──────────────────────┐                ┌──────────────────────┐
   │ AsignacionFondo      │                │ GastoObra            │
   │ WHERE anulada=False  │                │ WHERE estado=APROBADO │
   └──────────┬───────────┘                └──────────┬───────────┘
              │                                       │
              ▼                                       ▼
       SUM(monto)                               SUM(monto)
              │                                       │
              └─────────────┬─────────────────────────┘
                            │
                            ▼
                  ┌──────────────────────┐
                  │ SALDO = A − G       │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ % Ejecución = G / A  │
                  │   × 100              │
                  └──────────┬───────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │ ¿A == 0?       │
                    └────┬───────┬───┘
                         │Sí     │No
                         ▼       ▼
                    ┌────────┐  ┌────────────────┐
                    │ 0.00 % │  │ (G / A) × 100  │
                    └────────┘  └────────────────┘
```

Decisión de si afecta el saldo según estado del gasto:

```
              ┌──────────────┐
              │   GastoObra  │
              │  .estado     │
              └──────┬───────┘
                     │
        ┌────────────┼────────────┬────────────┐
        │            │            │            │
     BORRADOR    APROBADO     ANULADO      (otro)
        │            │            │
        ▼            ▼            ▼
   ┌─────────┐  ┌──────────┐  ┌──────────┐
   │No suma  │  │Suma a G  │  │No suma   │
   │al saldo │  │al saldo  │  │al saldo  │
   └─────────┘  └──────────┘  └──────────┘
```

---

## 3. Creación de GastoObra desde documentos origen

```
                ┌────────────────┐
                │   Obra (1)     │
                └───────┬────────┘
                        │
        ┌───────────────┼───────────────┬───────────────┐
        │               │               │               │
        ▼               ▼               ▼               ▼
   ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
   │Factura  │    │ Nómina   │    │Uso Maq.  │    │Otro Gasto│
   │Proveedor│    │          │    │          │    │          │
   └────┬────┘    └─────┬────┘    └─────┬────┘    └─────┬────┘
        │               │               │               │
        │ servicio:     │ servicio:     │ servicio:     │ servicio:
        │ crear_gasto_  │ crear_nomina_ │ crear_uso_    │ crear_otro_
        │ con_factura() │ con_gasto()   │ maquinaria_   │ gasto()
        │               │               │ con_gasto()   │
        └───────┬───────┴───────┬───────┴───────┬───────┘
                │               │               │
                └───────────────┼───────────────┘
                                │
                                ▼
                ┌────────────────────────────┐
                │   GastoObra (UNO)           │
                │   obra + monto + estado     │
                │   + tipo_gasto              │
                └────────────┬───────────────┘
                             │
                             ▼
                ┌────────────────────────────┐
                │   Trazabilidad              │
                │   GastoObra → documento     │
                │   via related_name          │
                └────────────────────────────┘
```

Regla: **GastoObra NO tiene `proveedor_id`**. El proveedor se obtiene
transitando: `GastoObra → FacturaProveedor → Proveedor`.

---

## 4. Atomicidad factura + gasto (transaction.atomic + rollback)

```
   Usuario                  Servicio                DB
   ───────                  ────────                ──
      │                        │                    │
      │  crear_gasto_con_      │                    │
      ├──────factura(...)─────►│                    │
      │                        │ BEGIN              │
      │                        ├───────────────────►│
      │                        │  INSERT GastoObra  │
      │                        ├───────────────────►│
      │                        │  INSERT Factura    │
      │                        ├───────────────────►│
      │                        │                    │
      │                  ╔═════╧═════╗              │
      │                  ║ ¿OK?     ║              │
      │                  ╚═════╤═════╝              │
      │                 Sí/  │  \No (raise)        │
      │                   /  │   \                  │
      │                      │    \                 │
      │                      ▼     \                │
      │               ┌──────────┐  \               │
      │               │  COMMIT  │   \              │
      │               └────┬─────┘    \             │
      │                    │          \            │
      │                    │    ┌──────▼──────┐     │
      │                    │    │  ROLLBACK  │     │
      │                    │    │ (ningún    │     │
      │                    │    │  registro  │     │
      │                    │    │  persiste) │     │
      │                    │    └────────────┘     │
      │                    │                       │
      │  (gasto, factura)  │                       │
      │◄───────────────────┤                       │
      │                    │                       │
```

Garantía: o se crean ambos, o ninguno. Nunca queda un gasto sin factura ni
una factura sin gasto.

---

## 5. Movimientos de inventario (sin `save()` mágico)

```
   ┌──────────────────────┐
   │ MovimientoMaterial   │   ← historial (inmutable una vez creado)
   │ - tipo               │      NO descuenta stock en save()
   │ - cantidad           │
   │ - fecha              │
   │ - usuario            │
   └──────────┬───────────┘
              │ creado por servicio
              ▼
   ┌──────────────────────┐
   │ apps.inventario.     │
   │ services.registrar_* │
   │ (transaction.atomic) │
   └──────────┬───────────┘
              │ modifica
              ▼
   ┌──────────────────────┐
   │ InventarioObra       │   ← estado actual (cantidad_actual)
   │ unique(obra,material)│
   └──────────────────────┘
```

Tipos de movimiento y su efecto:

```
   ┌────────────────┐
   │    TIPO        │
   └───────┬────────┘
           │
   ┌───────┼───────┬────────┬─────────┬─────────┐
   │       │       │        │         │         │
   ▼       ▼       ▼        ▼         ▼         ▼
ENTRADA  SALIDA  TRANSF.  DEVOL.   AJUSTE     (otro)
   │       │       │        │         │
   │       │       │        │         │
   ▼       ▼       ▼        ▼         ▼
  +c     -c      -c(orig)  +c       =c
                  +c(dest)  (vuelve al stock)
```

Regla fundamental: **Si creas un `MovimientoMaterial` directamente con
`Model.save()`, el stock NO cambia.** El stock solo cambia a través de los
servicios `registrar_entrada_material()`, `registrar_salida_material()`,
`registrar_devolucion_material()`, `registrar_transferencia_material()` y
`ajustar_inventario()`. Cada uno usa `transaction.atomic()`.

---

## 6. Consistencia de FacturaProveedor

```
   ┌──────────────────┐
   │ DetalleFactura   │  N líneas
   │  - cantidad      │
   │  - precio_unit.  │
   │  - material (FK) │
   └────────┬─────────┘
            │ SUM(cantidad × precio_unitario)
            ▼
   ┌──────────────────┐
   │    subtotal      │
   └────────┬─────────┘
            │ + impuesto
            ▼
   ┌──────────────────┐
   │ total_calculado  │
   └────────┬─────────┘
            │
            ▼
       ╔══════════╗
       ║total == ?║
       ╚════╤═════╝
       Sí/  │  \No
        /   │   \
            ▼    ▼
       ┌──────┐  ┌──────────────────┐
       │ OK   │  │ Inconsistente    │
       └──────┘  │ (mostrar alerta) │
                 └──────────────────┘
```

Uso desde UI:

```
   apps.proveedores.services
       ├── verificar_consistencia_factura(f)  → bool
       ├── exigir_consistencia_factura(f)     → raise ValidationError
       └── actualizar_total_desde_detalles(f)  → total = subtotal + impuesto
```

---

## 7. Anular vs. Borrar (decisión de UI)

```
              ┌─────────────────────┐
              │  Acción en frontend │
              └──────────┬──────────┘
                         │
            ┌────────────┼─────────────┐
            │            │             │
            ▼            ▼             ▼
       Ver (👁)     Editar (✏)    Anular/Borrar (🚫/🗑)
       siempre      siempre        ↓
       habilitado   habilitado   ╔══════════╗
                                 ║ ¿Modelo  ║
                                 ║financier?║
                                 ╚════╤═════╝
                                Sí/  │  \No
                                 /   │   \
                                     │    ▼
                                     │  ┌──────────┐
                                     │  │ DeleteView│
                                     │  │ (borrar) │
                                     │  └──────────┘
                              ┌──────────────────────┐
                              │ Anular servicio       │
                              │ (apps.finanzas.       │
                              │  services.anular_*)   │
                              │ Estado → ANULADO      │
                              │ No borra físicamente  │
                              └──────────────────────┘
```

Modelos **financieros** (solo Anular):

- AsignacionFondo → `apps.fondos.services.anular_asignacion()`
- GastoObra → `apps.finanzas.services.anular_gasto()`
- Nomina → anular el `GastoObra` subyacente
- UsoMaquinaria → anular el `GastoObra` subyacente
- OtroGasto → anular el `GastoObra` subyacente

Modelos **NO financieros** (borrar OK):

- Obra, Empleado, Material, Maquinaria, Proveedor
- FacturaProveedor, DetalleFactura, NominaDetalle

---

## 8. Cálculo de % de ejecución (división por cero)

```
              ┌────────────────────┐
              │ total_asignado(A)  │
              │ total_gastado(G)   │
              └─────────┬──────────┘
                        │
                        ▼
                  ╔════════════╗
                  ║ A == 0?   ║
                  ╚════╤═══════╝
                   Sí/ │  \No
                    /  │   \
                       ▼    ▼
                ┌────────┐  ┌────────────────────┐
                │ 0.00 % │  │ (G / A) × 100     │
                └────────┘  └─────────┬──────────┘
                                    │
                                    ▼
                          ┌──────────────────────┐
                          │  Decimal(2dec)       │
                          │  p.ej. 25.00         │
                          └──────────────────────┘
```

Implementación (en `apps.finanzas.services.porcentaje_ejecucion`):

```
   if A == 0:
       return Decimal('0.00')
   return (G / A) * Decimal('100')
```

---

## 9. Pipeline de login / logout

```
   ┌────────────────────┐
   │ GET /              │
   │ (sin sesión)       │
   └─────────┬──────────┘
             │ 302 /login/?next=/
             ▼
   ┌────────────────────┐
   │ GET /login/        │  ← 200 con formulario
   └─────────┬──────────┘
             │ POST username + password
             ▼
   ┌────────────────────┐
   │ auth.authenticate  │
   │ (User.check_password)
   └─────────┬──────────┘
             │
      ╔══════╧══════╗
      ║¿válido?    ║
      ╚════╤═══════╝
        Sí/ │  \No
         /  │   \
            ▼    ▼
     ┌────────┐  ┌────────────────┐
     │302 /  │  │ 200 login.html │
     │(Login │  │ con error      │
     │ done) │  └────────────────┘
     └────┬───┘
          │
          ▼
   ┌────────────────────┐
   │ GET / (con sesión) │  ← 200 Dashboard
   │ Dashboard con KPIs  │
   └────────────────────┘

   Para salir:
   ┌────────────────────┐
   │ POST /logout/      │
   │ (con CSRF)         │
   └─────────┬──────────┘
             │ limpia sesión
             ▼
   ┌────────────────────┐
   │ 302 /login/        │
   └────────────────────┘
```

---

## 10. Anular un gasto (impacto inmediato en saldo)

```
   ┌────────────────────┐
   │ Usuario ve un      │
   │ gasto APROBADO     │
   └─────────┬──────────┘
             │ click 🚫
             ▼
   ┌────────────────────┐
   │ confirm() JS       │  ← "¿Anular este registro?"
   └─────────┬──────────┘
             │ Aceptar
             ▼
   ┌────────────────────────────────────────┐
   │ POST /finanzas/gastos/<id>/anular/    │
   └─────────────────┬──────────────────────┘
                     │
                     ▼
   ┌────────────────────────────────────────┐
   │ GastoObraAnularView.post()             │
   │   → anular_gasto(g)                     │
   │     → g.estado = ANULADO                │
   │     → g.save()                          │
   └─────────────────┬──────────────────────┘
                     │
                     ▼
   ┌────────────────────────────────────────┐
   │ próxima consulta de total_gastado(obra)│
   │   WHERE estado=APROBADO                │
   │   → ya NO incluye este gasto          │
   │   → SALDO se recalcula automáticamente  │
   └────────────────────────────────────────┘
```

No hay cron, no hay cache que invalidar: el saldo se recalcula cada vez
que se lee.

---

## Anexo A — Servicios transaccionales clave

| Servicio | Ubicación | Función | `transaction.atomic` |
|---|---|---|---|
| `total_asignado(obra)` | `apps.finanzas.services` | Suma asignaciones vigentes | No (solo lectura) |
| `total_gastado(obra)` | `apps.finanzas.services` | Suma gastos APROBADO | No (solo lectura) |
| `saldo(obra)` | `apps.finanzas.services` | Asignado − Gastado | No (solo lectura) |
| `porcentaje_ejecucion(obra)` | `apps.finanzas.services` | % con guard div/0 | No (solo lectura) |
| `anular_gasto(gasto)` | `apps.finanzas.services` | estado → ANULADO | No (un solo UPDATE) |
| `crear_gasto_con_factura(...)` | `apps.finanzas.services` | Crea ambos atómicamente | **Sí** |
| `crear_otro_gasto(...)` | `apps.finanzas.services` | Crea ambos atómicamente | **Sí** |
| `crear_nomina_con_gasto(...)` | `apps.finanzas.services` | Crea 3 entidades | **Sí** |
| `crear_uso_maquinaria_con_gasto(...)` | `apps.finanzas.services` | Crea 2 entidades | **Sí** |
| `anular_asignacion(a)` | `apps.fondos.services` | anulada=True | No (un solo UPDATE) |
| `recalcular_total_nomina(n)` | `apps.personal.services` | suma detalles → gasto.monto | **Sí** |
| `registrar_entrada/salida/devolucion/transferencia/ajuste` | `apps.inventario.services` | Actualiza stock + crea movimiento | **Sí** (cada uno) |
| `verificar_consistencia_factura` | `apps.proveedores.services` | bool | No (solo lectura) |
| `actualizar_total_desde_detalles` | `apps.proveedores.services` | total = subtotal + impuesto | No (un solo UPDATE) |
| `exigir_consistencia_factura` | `apps.proveedores.services` | raise ValidationError | No (solo lectura) |
| `generar_reporte_obra(obra)` | `apps.obras.pdf` | Genera PDF con reportlab | No (lectura) |

---

## Anexo B — Pendientes de validación con cliente

Los siguientes elementos están marcados como "Pendiente de validación" en
los templates o en este documento:

1. **Reporte PDF**: hoy es 1 página A4 con datos básicos. Si se requiere
   multipágina, gráficos, o fotos, hay que ampliar el servicio.
2. **Gráficos Chart.js**: vía CDN. Si se requiere offline, hay que
   bundlear localmente.
3. **Filtros**: implementados `?obra=`, `?factura=`, `?nomina=`, `?estado=`.
   Falta decidir si la búsqueda por texto (q) debe ser full-text o LIKE simple.
4. **Wizard de factura con líneas en un solo paso**: hoy se crea la
   factura vacía y luego se agregan detalles. Pendiente confirmar UX.
5. **Importar XML de factura (CFDI)**: no implementado.
6. **Permisos por rol**: todos los autenticados tienen acceso completo.
7. **Auditoría**: no se registra quién modificó qué.
8. **Notificaciones**: ninguna.

---

## Anexo C — Cómo se ve en la UI

| Sección | URL ejemplo | Acción rápida |
|---|---|---|
| Dashboard | `/` | KPIs + gráficos Chart.js |
| Listado de obras | `/obras/` | Saldo y % por obra |
| Detalle de obra | `/obras/6/` | Drill-down + botón "Reporte PDF" |
| Fondos por obra | `/fondos/?obra=6` | Anular / Editar |
| Gastos por obra | `/finanzas/gastos/?obra=6` | Anular / Drill-down al documento |
| Facturas por obra | `/proveedores/facturas/?obra=6` | Consistencia + líneas |
| Inventario por obra | `/inventario/inventarios/?obra=6` | Stock actual |
| Movimientos por obra | `/inventario/movimientos/?obra=6` | Historial |
| Nóminas por obra | `/personal/nominas/?obra=6` | Recalcular / Anular |
| Maquinaria por obra | `/maquinaria/usos/?obra=6` | Anular |

---

**Mantenedor**: este documento se actualiza cuando cambia un proceso de
negocio. Si modificas un servicio o una regla financiera, refleja el
cambio aquí.
