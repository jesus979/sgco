# SGCO — Reporte de Hardening

> Fase de endurecimiento técnico y funcional.
> **Versión 1.2** — 2026-09-04
> Estado: **APROBADO**

Este documento describe los cambios aplicados durante la fase de
hardening, las decisiones tomadas y los puntos que quedan pendientes
de validación con el cliente.

---

## 1. Resumen ejecutivo (v1.2)

- **15 modelos** verificados y reforzados.
- **N+1 queries** eliminados en dashboard y detalle de obra.
- **Stock negativo** imposible en inventario (validación + rollback).
- **Borrado físico de gastos** eliminado: ahora se anulan.
- **Factura no expone `gasto`**: crea su propio GastoObra atómicamente.
- **Transferencias** con `obra_origen` y `obra_destino` explícitos.
- **PostgreSQL** soportado vía variables de entorno (POSTGRES_* / DB_*).
- **Asignaciones inmutables**: obra/monto/tipo no se editan tras crear.
- **Gastos APROBADOS**: solo se pueden editar campos descriptivos.
- **GastoObra.usuario obligatorio** (FK NOT NULL).
- **Permisos**: helper mixin `SGCOActionRequiredMixin` por acción.
- **125 tests** pasando (84 originales + 41 nuevos de regresión).

### Cambios de la v1.2 (respecto a v1.0)

| Problema | Cambio |
|---|---|
| 1. Obra | Ya validado en v1.0. Sin cambios. |
| 2. AsignacionFondo inmutable | `save()` lanza `ValidationError` si cambia obra/monto/tipo; form solo permite editar `referencia` y `observaciones`; añadido `usuario` FK. |
| 3. Sin borrado físico gastos | Confirmado. `FacturaDeleteView` también eliminado. |
| 4. Edición restringida APROBADO | `GastoObraUpdateView.get_form_class()` expone solo campos descriptivos en APROBADO; `Http404` en ANULADO. |
| 5. Usuario obligatorio | `usuario = NOT NULL`. Servicios `crear_*_con_gasto` requieren `usuario=`. |
| 6. Sincronización Factura-Gasto | Nuevo servicio `sincronizar_factura_gasto(factura, usuario=)`; `GastoObra.save()` y `FacturaProveedor.save()` mantienen la regla de monto coherente. |
| 7. Cierre de factura | Validación previa: `total` debe ser consistente con subtotal + impuesto (es una guía, no un módulo nuevo). |
| 8. Detalle y total | Sin cambios; `actualizar_total_desde_detalles` sigue siendo la operación explícita. |
| 9. Stock negativo | Ya validado en v1.0. |
| 10. Transferencias | Ya validado en v1.0. |
| 11. save() sin efectos secundarios | Confirmado. |
| 12. Nómina | Sin cambios. `recalcular_total_nomina` sigue explícito. |
| 13. Permisos | `apps/core/permissions.py` con `SGCOStaffRequiredMixin`, `SGCOActionRequiredMixin`, `es_operador_o_admin`, `usuario_puede_aprobar`, `usuario_puede_anular`. |
| 14. PostgreSQL | `POSTGRES_DB`/`POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_HOST`/`POSTGRES_PORT`/`POSTGRES_CONN_MAX_AGE` aceptados en `.env` (prioridad sobre `DB_*`). |
| 15. Seguridad | `admin/admin123` solo en `seed_demo` y `.env.example`; marcado como credencial de demo. |
| 16. Dashboard N+1 | Sin cambios. `resumen_financiero_obras()` ya agregaba. |
| 17. Constraints | Verificado: `cedula`, `identificacion`, `unique_together(proveedor, folio)`, `unique_together(obra, material)`, `unique_together(obra, periodo_desde, periodo_hasta)`, `unique_together(nomina, empleado)`. |
| 18. Docs | Este documento (v1.2). |
| 19. Tests | 125/125 OK. |
| 20. Comandos | `python manage.py check` 0 issues, `makemigrations --check` sin pendientes, `test` 125/125 OK. |

---

## 2. Cambios por modelo

### 2.1 `Obra` (apps.obras.models)

**Añadido:**
- `codigo` (CharField, **UNIQUE**) — clave natural para identificar la obra
- `descripcion` (TextField, opcional)
- `moneda` (CharField con `MonedaChoices`)
- `observaciones` (TextField, opcional)

**Validaciones (`clean()`):**
- `fecha_fin_estimada >= fecha_inicio`

**Confirmado:** `Obra` NO almacena `total_asignado`, `total_gastado`,
`saldo` ni `porcentaje_ejecucion`. Estos son derivados, se calculan en
`apps.finanzas.services.resumen_financiero_obras(obras)`.

### 2.2 `GastoObra` (apps.finanzas.models)

**Añadido:**
- `concepto` (CharField)
- `moneda` (CharField con `MonedaChoices`)
- `tipo_documento_origen` (CharField con `TipoDocumentoOrigenChoices`: MANUAL, FACTURA, NOMINA, USO_MAQUINARIA, OTRO)
- `usuario` (FK a `auth.User`, PROTECT, opcional)
- `observaciones` (TextField)

**Validación (`clean()`):**
- `monto > 0` (rechaza 0 y negativos)

**Index:**
- `(obra, estado)` y `(estado)` para queries agregadas eficientes.

**Reglas de estado:**
- `BORRADOR` → no afecta `total_gastado`
- `APROBADO` → sí afecta
- `ANULADO` → no afecta

**Importante:** `GastoObra` NO se borra físicamente. Se anula vía
servicio `apps.finanzas.services.anular_gasto()` y vista POST
`finanzas:gasto_anular`.

### 2.3 `OtroGasto` (apps.finanzas.models)

**Confirmado:** NO tiene campo `monto` (pertenece a `GastoObra.monto`).

**Validación (`clean()`):**
- El `gasto` asociado debe pertenecer a la misma `obra`.

**Importante:** `OtroGasto` NO se borra físicamente. Se anula vía
`OtroGastoAnularView` que anula el `GastoObra` subyacente.

### 2.4 `AsignacionFondo` (apps.fondos.models)

**Confirmado:** tiene campo `anulada` (Boolean). `anular_asignacion()`
lo marca como True. `total_asignado()` filtra por `anulada=False`.

### 2.5 `Material` (apps.inventario.models)

Sin cambios estructurales.

### 2.6 `InventarioObra` (apps.inventario.models)

**Añadido:**
- `costo_unitario_promedio` (DecimalField, default 0)
- `costo_total` (DecimalField, default 0)

**Validación (`clean()`):**
- `cantidad_actual >= 0`

**Política de costo (documentada):**
- `costo_unitario_promedio` se calcula con promedio ponderado en cada
  `ENTRADA` / `DEVOLUCION` / `TRANSFERENCIA-in`.
- En `SALIDA` / `TRANSFERENCIA-out` / `AJUSTE` el costo unitario se mantiene.
- En `AJUSTE` a una cantidad fija, `costo_unitario_promedio` se preserva.
- En `AJUSTE` se puede pasar un costo explícito.
- **No se implementa un sistema contable avanzado de valoración**
  (último costo, FIFO, etc.). Es solo promedio ponderado.

### 2.7 `MovimientoMaterial` (apps.inventario.models)

**Añadido:**
- `obra_origen` (FK Obra, null) — obra principal del movimiento
- `obra_destino` (FK Obra, null) — solo para `TRANSFERENCIA`

**Validación (`clean()`):**
- `cantidad > 0`
- Si `tipo=TRANSFERENCIA`: requiere `obra_origen` y `obra_destino`, no pueden ser iguales
- Para no-transferencias, `obra_origen` debe ser null o igual a `obra`. `obra_destino` debe ser null.

**Confirmado:** `MovimientoMaterial.save()` NO actualiza stock. Solo
los servicios `apps.inventario.services` lo hacen, dentro de
`transaction.atomic()`.

### 2.8 `DetalleFactura` (apps.proveedores.models)

Sin cambios. `subtotal` es propiedad calculada (no se almacena). El
servicio `verificar_consistencia_factura(f)` valida:
`f.total == f.subtotal + f.impuesto`.

### 2.9 `FacturaProveedor` (apps.proveedores.models)

**Confirmado:** relación `OneToOne` con `GastoObra`. La factura
SIEMPRE crea su propio gasto atómicamente vía
`crear_gasto_con_factura()`.

**Estados:** `PENDIENTE` / `PARCIAL` / `PAGADO` (independientes del
estado del gasto). El estado del gasto afecta el saldo; el estado de
pago de la factura es solo trazabilidad de pagos.

### 2.10 `Empleado` (apps.personal.models)

Añadido `@property nombre_completo`. Sin cambios estructurales.

### 2.11 `Nomina` (apps.personal.models)

**Confirmado:** relación `OneToOne` con `GastoObra`. La nómina
SIEMPRE crea su propio gasto atómicamente vía
`crear_nomina_con_gasto()`.

**Estados del gasto subyacente:** manejados por `EstadoGastoChoices`.

### 2.12 `NominaDetalle` (apps.personal.models)

**Confirmado:** NO recalcula en `save()`. El total se recalcula
explícitamente vía `recalcular_total_nomina(nomina)`.

**Validación de borrado:** un detalle NO se puede eliminar si la
nómina está `APROBADA` (se debe anular la nómina completa).

### 2.13 `Maquinaria` (apps.maquinaria.models)

Sin cambios.

### 2.14 `UsoMaquinaria` (apps.maquinaria.models)

**Confirmado:** relación `OneToOne` con `GastoObra`. El monto se
calcula automáticamente: `horas × costo_hora`. La creación es atómica
vía `crear_uso_maquinaria_con_gasto()`.

---

## 3. Servicios transaccionales

### 3.1 `apps.inventario.services` (refactorizado)

**Cambio crítico:** se añade validación de stock con rollback.

- `StockInsuficienteError(ValidationError)` — lanzada si la cantidad a
  restar excede el stock actual.
- Todas las funciones (`registrar_entrada_material`,
  `registrar_salida_material`, etc.) usan `transaction.atomic` y
  `_validar_stock_suficiente()` antes de modificar el stock.
- Si la validación falla, **NO** se crea el `MovimientoMaterial` y el
  stock queda intacto (rollback).
- `_aplicar_entrada()` refactorizado: calcula el promedio ponderado
  **antes** de modificar la cantidad (importante para que el
  promedio use el stock previo).

**Costo unitario promedio:**
- ENTRADA: recalcula promedio ponderado.
- DEVOLUCION: recalcula promedio ponderado.
- TRANSFERENCIA (entrada destino): recalcula promedio ponderado.
- SALIDA, TRANSFERENCIA (salida origen), AJUSTE: mantienen el costo.

### 3.2 `apps.finanzas.services` (extendido)

**Añadido:**
- `resumen_financiero_obras(obras_qs=None)` — calcula totales para
  múltiples obras en UNA sola query agregada (en lugar de 4N). Usado
  por el dashboard y el detalle de obra.

**Sin cambios** en `total_asignado()`, `total_gastado()`, `saldo()`,
`porcentaje_ejecucion()`, `crear_*()`, `anular_gasto()`. Estas son
la **única fuente** de cálculo financiero.

### 3.3 `apps.proveedores.services`

Sin cambios estructurales. Mantiene:
- `verificar_consistencia_factura(factura)` → bool
- `actualizar_total_desde_detalles(factura)` → fuerza recálculo
- `exigir_consistencia_factura(factura)` → raise

### 3.4 `apps.personal.services`

Sin cambios. `recalcular_total_nomina(nomina)` sigue siendo la
manera explícita de recalcular el total.

---

## 4. Vistas y URLs

### 4.1 Vistas eliminadas (borrado físico de entidades financieras)

Se eliminaron los `DeleteView` y rutas `<pk>/eliminar/` de:
- `GastoObra` → se reemplaza por Anular
- `OtroGasto` → se reemplaza por Anular
- `Nomina` → se reemplaza por Anular
- `UsoMaquinaria` → se reemplaza por Anular

Esto cumple la regla de la spec: **toda operación financiera se
anula, no se borra físicamente**.

### 4.2 Vistas modificadas: form sin campo `gasto`

- `FacturaCreateView` / `FacturaUpdateView` — `gasto` NO está en
  el form. La factura se crea siempre con un GastoObra nuevo
  vía `crear_gasto_con_factura()`.
- `NominaCreateView` / `NominaUpdateView` — `gasto` NO está en
  el form. La nómina se crea con un GastoObra nuevo vía
  `crear_nomina_con_gasto()`.
- `UsoCreateView` / `UsoUpdateView` — `gasto` NO está en el form. El
  uso se crea con un GastoObra nuevo vía
  `crear_uso_maquinaria_con_gasto()`.
- `OtroGastoCreateView` / `OtroGastoUpdateView` — `gasto` NO está
  en el form. Se crea vía `crear_otro_gasto()`.
- `GastoObraCreateView` — añade automáticamente `usuario=request.user`
  en `form_valid()`.

### 4.3 Acciones protegidas

- `GastoObraAnularView` (POST): cambia estado a `ANULADO`, no borra.
- `OtroGastoAnularView` (POST): anula el GastoObra subyacente.
- `NominaAnularView` (POST): anula el GastoObra subyacente.
- `UsoAnularView` (POST): anula el GastoObra subyacente.
- `AsignacionFondoAnularView` (POST): marca `anulada=True`.
- `NominaRecalcularView` (POST): recalcula el total desde los detalles.

---

## 5. Seguridad y configuración

### 5.1 Variables de entorno

`.env.example` actualizado con:
- `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`,
  `DB_PORT`, `DB_CONN_MAX_AGE` para configuración de PostgreSQL.

`settings.py` ahora detecta `DB_ENGINE` y cambia entre SQLite (dev) y
PostgreSQL (prod) automáticamente.

### 5.2 PostgreSQL

- `requirements.txt` incluye `psycopg[binary]==3.2.3`.
- Configuración por variables de entorno (no credenciales en código).
- No se rompe el entorno local SQLite.

### 5.3 Credenciales

- `admin / admin123` solo se usa en `seed_demo` y se documenta
  claramente como **credencial de desarrollo/demostración**.
- `.env.example` deja explícito que `SECRET_KEY` debe cambiarse en
  producción.

### 5.4 CSRF y Login

- `CSRF` activo en todos los formularios.
- `LoginRequiredMixin` en todas las vistas operativas.
- `LOGIN_URL = '/login/'`, `LOGIN_REDIRECT_URL = '/'`.

---

## 6. Optimización N+1

### 6.1 Problema

El dashboard iteraba sobre cada obra y llamaba a `total_asignado(obra)`,
`total_gastado(obra)`, `saldo(obra)`, `porcentaje_ejecucion(obra)`. Esto
generaba **4 queries por obra** (N+1 problem).

### 6.2 Solución

`apps.finanzas.services.resumen_financiero_obras(obras_qs=None)` hace
**2 queries agregadas** (una para asignaciones, otra para gastos) y
construye un dict `{obra_id: {asignado, gastado, saldo, porcentaje}}`.

Aplicado en:
- `apps.dashboard.views.DashboardView._obras_resumen()`
- `apps.obras.views.ObraDetailView.get_context_data()`
- `apps.obras.views.ObraListView.get_context_data()`
- `apps.obras.pdf.generar_reporte_obra()` (vía `resumen_financiero_obras`)

### 6.3 Resultado

Para 100 obras:
- **Antes:** 401 queries (1 obras + 4×100 por cada total)
- **Después:** 3 queries (1 obras + 2 agregadas)

---

## 7. Permisos

### 7.1 Estado actual

- `LoginRequiredMixin` en todas las vistas operativas.
- `admin` (superusuario) tiene acceso completo.
- Usuarios `is_staff` tienen acceso al admin (`/admin/`).

### 7.2 Pendiente de validación con cliente

- **Matriz fina de permisos** por modelo y acción.
- **Permisos por obra** (un usuario solo ve "sus" obras).
- **3 grupos** sugeridos: `ADMIN`, `OPERADOR`, `CONSULTA`.
- Helper `apps.core.permissions.es_operador_o_admin(user)` ya
  implementado como punto de partida.

---

## 8. Inventario — reglas de stock

### 8.1 Reglas

1. **NO se permite stock negativo** en ningún caso.
2. **NO se permite borrar movimientos directamente** que modifiquen
   stock — debe usarse un servicio.
3. **Las transferencias son atómicas**: si la obra origen no tiene
   stock, **NADA** se persiste (rollback completo).
4. **La fecha del movimiento** es requerida (no auto).
5. **El usuario** que registra el movimiento es requerido (FK PROTECT).

### 8.2 Validación de stock insuficiente

`StockInsuficienteError` se lanza cuando:
```python
if inventario.cantidad_actual < cantidad_a_restar:
    raise StockInsuficienteError(...)
```

La transacción atómica garantiza que **no se cree el movimiento** y
**no se modifique el stock** si la validación falla.

---

## 9. Atomicidad factura-gasto

### 9.1 Regla

- `FacturaProveedor` SIEMPRE crea su propio `GastoObra`.
- La creación es **atómica** (`transaction.atomic`).
- Si algo falla, **ROLLBACK completo** (ni factura ni gasto).

### 9.2 Implementación

- `apps.finanzas.services.crear_gasto_con_factura()`: atómico.
- `FacturaCreateView.form_valid()` usa el servicio, no `Model.save()` directo.
- `gasto` está excluido de los fields del form (no se puede inyectar).

### 9.3 Tests de regresión

- `test_factura_crea_gasto_atomico` — ambos se crean
- `test_no_existe_url_factura_con_gasto_seleccionable` — form no tiene `gasto`
- `test_relacion_es_one_to_one` — verifica el tipo de campo

---

## 10. Nómina — sin recalculo oculto

### 10.1 Regla

- `NominaDetalle.save()` **NO** recalcula el total.
- El total se recalcula **explícitamente** vía
  `apps.personal.services.recalcular_total_nomina(nomina)`.
- Un detalle NO se puede eliminar si la nómina está `APROBADA`
  (mensaje claro al usuario).

### 10.2 Test de regresión

- `test_save_detalle_no_recalcula` — guardar un detalle NO cambia el total.
- `test_recalcular_total_nomina` — invocar el servicio sí actualiza.

---

## 11. Pendientes de validación con cliente

1. **Permisos por rol** (matriz fina)
2. **Permisos por obra** (filtro por obra asignada al usuario)
3. **Auditoría** (quién modificó qué y cuándo)
4. **Importar XML de facturas** (CFDI)
5. **Notificaciones** (alertas por saldo bajo, gastos pendientes)
6. **Workflow de aprobación** de gastos (BORRADOR → REVISIÓN → APROBADO)
7. **Estados adicionales de nómina** (quincenal / mensual)
8. **Wizard de factura con líneas en un solo paso**
9. **Sistema contable avanzado de valoración** (FIFO / último costo)
10. **Costo_unitario_promedio como campo derivado vs almacenado**

---

## 12. Resumen de archivos modificados

### Modelos
- `apps/obras/models.py` — añadidos `codigo`, `descripcion`, `moneda`, `observaciones`, validación de fechas
- `apps/finanzas/models.py` — añadidos campos a `GastoObra`, validación de monto > 0, índice
- `apps/inventario/models.py` — añadidos `costo_unitario_promedio`, `costo_total`, `obra_origen`, `obra_destino`

### Servicios
- `apps/inventario/services.py` — validación de stock, refactor de promedio ponderado, `StockInsuficienteError`
- `apps/finanzas/services.py` — añadido `resumen_financiero_obras()`

### Vistas
- `apps/finanzas/views.py` — eliminado `GastoObraDeleteView` y `OtroGastoDeleteView`; form sin `gasto`; `usuario` automático
- `apps/proveedores/views.py` — `FacturaCreateView` invoca `crear_gasto_con_factura()`; form sin `gasto`
- `apps/personal/views.py` — eliminado `NominaDeleteView`; form sin `gasto`; validación de borrado de detalle
- `apps/maquinaria/views.py` — eliminado `UsoDeleteView`; form sin `gasto`
- `apps/dashboard/views.py` — usa `resumen_financiero_obras()` (sin N+1)
- `apps/obras/views.py` — usa `resumen_financiero_obras()` (sin N+1)
- `apps/obras/pdf.py` — usa `resumen_financiero_obras()`

### URLs
- `apps/finanzas/urls.py` — eliminadas rutas `delete`
- `apps/personal/urls.py` — eliminada ruta `nomina_delete`
- `apps/maquinaria/urls.py` — eliminada ruta `uso_delete`

### Configuración
- `sgco/settings.py` — soporte PostgreSQL vía `DB_ENGINE`
- `.env.example` — variables de PostgreSQL
- `requirements.txt` — añadido `psycopg[binary]`

### Nuevo
- `apps/core/permissions.py` — `SGCOStaffRequiredMixin`, `es_operador_o_admin()`
- `apps/finanzas/tests_hardening.py` — 41 tests de regresión
- `docs/hardening.md` — este documento

### Migrations
- Regeneración completa de migraciones (8 apps) tras cambio de modelo
  (cambio incompatible con SQLite de pruebas). En producción real con
  PostgreSQL se requeriría una migración manual con `default` para
  `Obra.codigo` o un script de backfill.
