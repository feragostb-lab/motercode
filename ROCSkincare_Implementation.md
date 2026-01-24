# ROC Skincare - Plan de Implementación Multi-Trabajador

## 🎯 Objetivo del Proyecto

Adaptar el sistema de procesamiento OCR de recibos para soportar múltiples trabajadores con gestión de periodos mensuales, permitiendo a Roc Skincare gestionar notas de gastos de forma incremental con funcionalidad de cierre y archivo de periodos.

**Cliente:** Roc Skincare  
**Fecha inicio:** Enero 2026  
**Trabajadores iniciales:** David, Pedro (ampliable según necesidad)

---

## 📊 Requisitos Funcionales Confirmados

### Estructura de Datos
- ✅ Múltiples trabajadores con gestión individual
- ✅ Periodos mensuales por trabajador (formato MMYYYY)
- ✅ Múltiples periodos abiertos simultáneamente por trabajador
- ✅ Un solo periodo activo para procesamiento a la vez
- ✅ Estructura de directorios: `./workers/{nombre}/{MMYYYY}/img|result|csv/`

### Gestión de CSV Bancarios
- ✅ Carga incremental: reemplaza datos previos del mismo periodo
- ✅ Múltiples cargas permitidas durante el mes
- ✅ Timestamped: `banco_{YYYYMMDD_HHMMSS}.csv`
- ✅ Formato de fechas: español (dd/mm/yyyy)

### Cierre de Periodos
- ✅ **Validación estricta:** No permitir cierre sin CSV cargado (ni con force)
- ✅ **Validación estricta:** No permitir cierre con recibos sin procesar
- ✅ **Validación estricta:** No permitir cierre con conflictos o sin match
- ✅ **Contenido ZIP:** Imágenes procesadas (result/) + CSV original + Excel con matches
- ✅ **Ubicación:** `./workers/{nombre}/{MMYYYY}/closure_{timestamp}.zip`

### Reapertura de Periodos
- ✅ Permitida con doble confirmación
- ✅ Requiere campo razón obligatorio
- ✅ Preserva ZIP anterior: renombrado a `closure_{timestamp}_reopened_{new_timestamp}.zip`

### Exportaciones
- ✅ **Temporal:** Disponible en cualquier momento desde periodo abierto
- ✅ **Cierre:** Generada automáticamente al cerrar periodo
- ✅ Todas las fechas en formato español

### Validaciones
- ✅ Nombres de trabajadores: solo alfanuméricos (sin espacios ni caracteres especiales)
- ✅ Nombres únicos case-insensitive (David = david = DAVID)
- ✅ Validación periodo duplicado: mismo trabajador + mismo month_year

### Interfaz
- ✅ Vista global de periodos: todos los periodos de todos los workers
- ✅ Ordenamiento: cronológico descendente (más reciente primero)
- ✅ Filtro: por trabajador
- ✅ Selector de periodo: muestra todos (activos y cerrados) con icono candado
- ✅ Gestión manual de trabajadores desde dashboard
- ✅ Periodos cerrados: visibles en modo solo lectura

### Futuro (preparación arquitectónica)
- 🔮 Roles de acceso por trabajador (solo visualización/edición propia)
- 🔮 Rol supervisor: aprobar/rechazar gastos, pedir explicaciones
- 🔮 Usuario único actual: contabilidad con acceso total

---

## 🏗️ Arquitectura de Cambios

### Capa de Datos (Database Schema)

#### Nuevas Tablas

**1. workers**
```sql
CREATE TABLE workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE COLLATE NOCASE,
    activo INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_workers_nombre_lower 
ON workers(LOWER(nombre));
```

**2. periods**
```sql
CREATE TABLE periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id INTEGER NOT NULL,
    month_year TEXT NOT NULL,  -- Formato: "MMYYYY"
    status TEXT DEFAULT 'active',  -- 'active' | 'closed'
    is_processing_active INTEGER DEFAULT 0,  -- Solo 1 periodo puede tener TRUE
    csv_last_upload TEXT,  -- Timestamp última carga CSV
    csv_file_path TEXT,    -- Path al último CSV cargado
    closed_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE CASCADE,
    UNIQUE(worker_id, month_year)
);

CREATE UNIQUE INDEX idx_periods_processing_active 
ON periods(is_processing_active) 
WHERE is_processing_active = 1;

CREATE INDEX idx_periods_worker ON periods(worker_id);
CREATE INDEX idx_periods_status ON periods(status);
```

**3. period_closures**
```sql
CREATE TABLE period_closures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period_id INTEGER NOT NULL,
    closure_date TEXT NOT NULL,
    export_path TEXT NOT NULL,  -- Path al ZIP generado
    reopened_at TEXT,
    reopen_reason TEXT,
    stats_snapshot TEXT,  -- JSON con estadísticas al cierre
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (period_id) REFERENCES periods(id) ON DELETE CASCADE
);

CREATE INDEX idx_closures_period ON period_closures(period_id);
```

**4. user_roles (preparación futura)**
```sql
CREATE TABLE user_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL,  -- 'admin' | 'worker' | 'supervisor'
    worker_id INTEGER,   -- NULL para admin/supervisor global
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (worker_id) REFERENCES workers(id)
);
```

#### Modificaciones a Tablas Existentes

**receipts**
```sql
ALTER TABLE receipts ADD COLUMN worker_id INTEGER REFERENCES workers(id);
ALTER TABLE receipts ADD COLUMN period_id INTEGER REFERENCES periods(id);

CREATE INDEX idx_receipts_worker ON receipts(worker_id);
CREATE INDEX idx_receipts_period ON receipts(period_id);
```

**bank_transactions**
```sql
ALTER TABLE bank_transactions ADD COLUMN worker_id INTEGER REFERENCES workers(id);
ALTER TABLE bank_transactions ADD COLUMN period_id INTEGER REFERENCES periods(id);
ALTER TABLE bank_transactions ADD COLUMN csv_upload_date TEXT;
ALTER TABLE bank_transactions ADD COLUMN csv_file_path TEXT;

CREATE INDEX idx_bank_worker ON bank_transactions(worker_id);
CREATE INDEX idx_bank_period ON bank_transactions(period_id);
```

**processing_queue**
```sql
ALTER TABLE processing_queue ADD COLUMN period_id INTEGER REFERENCES periods(id);

CREATE INDEX idx_queue_period ON processing_queue(period_id);
```

---

## 📁 Estructura de Archivos a Crear

### Modelos de Dominio (Completado ✅)
- [x] `src/models/domain.py` - Extendido con Worker, Period, PeriodClosure, PeriodStats

### Repositorios (Completado ✅)
- [x] `src/repositories/worker_repository.py` - CRUD de trabajadores
- [x] `src/repositories/period_repository.py` - CRUD de periodos
- [x] `src/repositories/receipt_repository.py` - Extendido con get_by_period(), get_by_worker()
- [x] `src/repositories/bank_repository.py` - Extendido con métodos por periodo/worker

### Servicios (Completado ✅)
- [x] `src/services/worker_service.py` - Lógica de negocio trabajadores
- [x] `src/services/period_service.py` - Lógica de negocio periodos
- [x] `src/services/period_closure_service.py` - Cierre y reapertura de periodos

### Utilidades (Completado ✅)
- [x] `src/utils/file_helpers.py` - Añadido `get_period_paths()`, `validate_worker_name()`
- [x] `src/utils/formatters.py` - Añadido formateo español completo

### Core (Completado ✅)
- [x] `src/core/database.py` - Añadidas nuevas tablas y migraciones

### Modificaciones a Repositorios Existentes
- [ ] `src/repositories/receipt_repository.py` - Añadir `get_by_period()`, `get_by_worker()`
- [ ] `src/repositories/bank_repository.py` - Añadir métodos por periodo/worker
- [ ] `src/repositories/match_repository.py` - Añadir filtros

### Modificaciones a Servicios Existentes
- [ ] `src/services/bank_matching_service.py` - Añadir `upload_csv_for_period()`
- [ ] `src/services/export_service.py` - Añadir `export_period_data()`
- [ ] `src/services/receipt_service.py` - Adaptar para paths dinámicos
- [ ] `src/ocr_processor.py` - Procesar solo periodo activo

### Interfaz Dashboard (Por modificar completamente)
- [ ] `app_dashboard.py` - Refactorizar con nueva estructura multi-trabajador

---

## 📅 Cronograma de Implementación

### Semana 1: Fundamentos (Backend)

**Días 1-2: Modelos y Base de Datos**
- [x] Extender `domain.py` con Worker, Period, PeriodClosure, PeriodStats
- [x] Modificar `database.py` para crear nuevas tablas
- [x] Añadir migraciones para columnas worker_id, period_id
- [x] Pruebas de esquema

**Días 3-4: Repositorios**
- [x] Implementar `WorkerRepository`
- [x] Implementar `PeriodRepository`
- [x] Extender repositorios existentes (receipt, bank, queue) con filtros por periodo
- [ ] Tests unitarios de repositorios

**Día 5: Utilidades**
- [x] Implementar helpers de paths (`get_period_paths`)
- [x] Implementar formatters españoles
- [x] Validación de nombres de trabajadores

### Semana 2: Servicios (Business Logic)

**Días 1-2: Worker y Period Services**
- [x] Implementar `WorkerService` completo
- [x] Implementar `PeriodService` completo
- [ ] Tests de servicios

**Días 3-4: Period Closure Service**
- [x] Implementar `validate_closure()`
- [x] Implementar `close_period()` con generación ZIP
- [x] Implementar `reopen_period()`
- [ ] Tests de cierre/reapertura

**Día 5: Adaptación de Servicios Existentes**
- [ ] Modificar `BankMatchingService.upload_csv_for_period()`
- [ ] Modificar `ExportService.export_period_data()`
- [ ] Modificar `OCRProcessor` para trabajar con periodo activo

### Semana 3: Interfaz de Usuario

**Días 1-2: Sidebar y Navegación**
- [ ] Implementar selector de trabajador/periodo en sidebar
- [ ] Implementar indicadores visuales (candado, activo)
- [ ] Botón "Activar para Procesamiento"

**Día 3: Páginas de Gestión**
- [ ] Página "Gestión de Trabajadores"
- [ ] Página "Vista Global de Periodos"

**Día 4: Carga CSV y Resumen**
- [ ] Página "Cargar CSV" con histórico
- [ ] Sección "Resumen del Periodo" con stats

**Día 5: Cierre y Reapertura**
- [ ] Implementar flujo de cierre con validaciones
- [ ] Implementar flujo de reapertura con doble confirmación
- [ ] Modales y warnings

### Semana 4: Integración y Testing

**Días 1-2: Pruebas End-to-End**
- [ ] Crear trabajador "David" y "Pedro"
- [ ] Crear periodo 012026
- [ ] Subir imágenes, procesar
- [ ] Cargar CSV, hacer matching
- [ ] Exportar temporal
- [ ] Cerrar periodo
- [ ] Verificar ZIP generado

**Día 3: Reapertura y Multi-periodo**
- [ ] Test de reapertura
- [ ] Test de múltiples periodos abiertos
- [ ] Test de cambio de periodo activo

**Día 4: Formateo Español**
- [ ] Verificar todas las fechas en español
- [ ] Verificar CSV parsing en español
- [ ] Verificar exports en español

**Día 5: Polish y Documentación**
- [ ] Ajustar UX/UI
- [ ] Añadir tooltips y ayudas
- [ ] Crear manual de usuario
- [ ] Preparar demo

---

## ✅ Checklist de Validación Final

### Funcionalidad Core
- [ ] Crear trabajador con nombre alfanumérico
- [ ] Validar duplicados case-insensitive
- [ ] Crear múltiples periodos para un trabajador
- [ ] Validar periodo duplicado
- [ ] Crear estructura de directorios automáticamente
- [ ] Activar periodo para procesamiento
- [ ] Validar que procesador esté detenido antes de cambiar periodo
- [ ] Procesar imágenes en periodo activo
- [ ] Contador de imágenes huérfanas

### CSV y Matching
- [ ] Cargar CSV con timestamp
- [ ] Parsear fechas en formato español (dd/mm/yyyy)
- [ ] Reemplazar transacciones de cargas previas
- [ ] Actualizar referencia a último CSV
- [ ] Re-matching automático después de carga

### Exportación
- [ ] Exportación temporal en cualquier momento
- [ ] Exportación de cierre
- [ ] Fechas en formato español en Excel
- [ ] Diferenciación visual entre tipos de export

### Cierre de Periodo
- [ ] Validar CSV cargado (obligatorio)
- [ ] Validar 100% recibos procesados
- [ ] Validar 100% recibos matched
- [ ] Validar 0 conflictos sin resolver
- [ ] Generar ZIP con: result/ + CSV + Excel
- [ ] Guardar en ubicación correcta
- [ ] Marcar periodo como cerrado
- [ ] Deshabilitar edición en periodos cerrados

### Reapertura
- [ ] Doble modal de confirmación
- [ ] Campo razón obligatorio
- [ ] Renombrar ZIP anterior con sufijo _reopened_
- [ ] Registrar reapertura en BD
- [ ] Habilitar edición nuevamente

### Interfaz
- [ ] Vista global con todos los periodos
- [ ] Ordenamiento cronológico descendente
- [ ] Filtro por trabajador
- [ ] Icono candado para cerrados
- [ ] Indicador de periodo activo para procesamiento
- [ ] Panel de resumen con stats
- [ ] Todas las fechas en español

### Preparación Futura
- [ ] Tabla user_roles creada
- [ ] Comentarios en código para futuras features
- [ ] Arquitectura lista para roles

---

## 🎯 Métricas de Éxito

1. **Correctitud:** 
   - 0 errores en cierre/reapertura
   - 100% de matches correctos
   - 0 pérdida de datos

2. **Usabilidad:**
   - Tiempo de creación trabajador < 30 segundos
   - Tiempo de cierre periodo < 2 minutos
   - Interfaz intuitiva sin necesidad de manual

3. **Performance:**
   - Carga de CSV < 5 segundos para 500 transacciones
   - Generación ZIP < 10 segundos para 100 recibos
   - UI responsiva (< 1 segundo por acción)

4. **Mantenibilidad:**
   - Código documentado
   - Tests unitarios > 80% cobertura
   - Arquitectura extensible para futuras features

---

## 📞 Estado Actual

**Fecha actualización:** 24 Enero 2026

### Completado ✅
- ✅ Plan de implementación documentado ([ROCSkincare_Implementation.md](ROCSkincare_Implementation.md))
- ✅ Modelos de dominio extendidos (Worker, Period, PeriodClosure, PeriodStats)
- ✅ Base de datos extendida (workers, periods, period_closures, user_roles)
- ✅ Migraciones añadidas (worker_id, period_id a tablas existentes)
- ✅ WorkerRepository y PeriodRepository creados
- ✅ WorkerService y PeriodService implementados
- ✅ PeriodClosureService con validate/close/reopen
- ✅ Utilidades: get_period_paths(), formateo español, validaciones
- ✅ Repositorios extendidos: receipt_repository, bank_repository con filtros periodo/worker

### En Progreso 🔄
- 🔄 Modificación de servicios existentes (BankMatchingService, ExportService)

### Pendiente ⏳
- ⏳ Modificación de OCR Processor para periodo activo
- ⏳ Tests unitarios
- ⏳ Modificación completa de interfaz dashboard
- ⏳ Testing end-to-end

---

## 📝 Notas Importantes

- Este plan asume que el código base actual (IMPLEMENTATION_GUIDE.md) está implementado
- Todas las fechas deben manejarse en formato español dd/mm/yyyy
- Los nombres de trabajadores son críticos para paths, validar estrictamente
- Los periodos cerrados son inmutables salvo reapertura controlada
- Preparar arquitectura para multi-tenant aunque se use single-user inicialmente

---

**Versión:** 1.0  
**Última actualización:** 24 Enero 2026  
**Cliente:** Roc Skincare  
**Próximas fases:** Roles de acceso, Sistema de aprobación, Notificaciones
