# 📊 Sistema de Procesamiento de Recibos con IA

Sistema automatizado para procesar recibos mediante OCR con Vision Language Model (VLM) y gestionar coincidencias con movimientos bancarios.

## 🌟 Características Principales

### Procesamiento Automático
- **OCR con IA**: Utiliza Qwen2.5-VL-7B para extracción inteligente de datos
- **Detección Automática**: Clasifica recibos (taxis, comidas, hoteles, etc.)
- **Procesamiento en Cola**: Sistema FIFO con reintentos automáticos
- **Gestión de Recursos**: Monitoreo CPU/RAM con boost automático cuando el PC está inactivo

### Coincidencia Bancaria
- **Matching Exacto**: Por fecha y monto con tolerancia configurable (±2%)
- **Detección de Conflictos**: Identifica múltiples recibos para la misma transacción
- **Recalculación Masiva**: Actualiza todas las coincidencias con un clic

### Panel de Control
- **Revisión de Recibos**: Navegación imagen por imagen con edición manual
- **Estadísticas en Tiempo Real**: Métricas de procesamiento y coincidencias
- **Exportación**: Excel/CSV con todos los datos

### Gestión de Datos
- **Base de Datos SQLite**: Persistencia local sin configuración
- **Backups Automáticos**: Rotación de copias de seguridad (7 días)
- **Recuperación de Errores**: Reinicio automático de procesos interrumpidos
- **Logs Detallados**: Trazabilidad completa del procesamiento

## 📋 Requisitos del Sistema

### Hardware Mínimo
- **CPU**: 4 núcleos (8 recomendado)
- **RAM**: 8 GB (16 GB recomendado para modo turbo)
- **Disco**: 10 GB libres (modelos GGUF + datos)
- **GPU**: Opcional (CUDA compatible para aceleración)

### Software
- **Sistema Operativo**: Windows 10/11, Linux, macOS
- **Python**: 3.9 o superior (3.11+ recomendado)
- **Dependencias**: Ver `requirements.txt`

## 🚀 Instalación

### Opción 1: Ejecutables (Usuario Final - Próximamente)

1. Descargar `RecibosSystem.zip`
2. Extraer en cualquier carpeta
3. Ejecutar `ConfigSetup.exe` para auto-configuración
4. Descargar modelos GGUF en carpeta `models/`
5. Listo para usar:
   - `RecibosProcessor.exe` - Procesar recibos
   - `RecibosDashboard.exe` - Revisar resultados

### Opción 2: Desde Código Fuente (Desarrollo)

```bash
# 1. Clonar proyecto
cd C:\WORKSPACE\gguf

# 2. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Descargar modelos GGUF (ver sección siguiente)

# 5. Auto-configuración (detecta hardware)
python scripts/setup_config.py

# 6. Migrar datos existentes (opcional)
python scripts/migrate_from_json.py

# 7. Ejecutar aplicaciones
streamlit run app_processor.py   # Procesador
streamlit run app_dashboard.py   # Dashboard
```

### Descarga de Modelos GGUF

**Modelos requeridos** (descargar en carpeta `models/`):

1. **Modelo Principal**: `Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf` (~4.5 GB)
2. **Proyector Multimodal**: `mmproj-Qwen2.5-VL-7B-Instruct-f16.gguf` (~600 MB)

**Fuente**: [Hugging Face - Qwen2.5-VL-7B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct-GGUF)

```bash
# Estructura esperada:
models/
├── Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf
└── mmproj-Qwen2.5-VL-7B-Instruct-f16.gguf
```

## 📁 Estructura del Proyecto

```
gguf/
├── models/                           # Modelos GGUF (5 GB)
│   ├── Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf
│   └── mmproj-Qwen2.5-VL-7B-Instruct-f16.gguf
├── img/                              # Imágenes de entrada
│   └── bankmov/                      # Excel de transacciones bancarias
├── result/                           # Recibos procesados (renombrados)
├── logs/                             # Logs de aplicaciones
│   ├── processor.log                 # Procesador OCR
│   └── dashboard.log                 # Dashboard
├── backups/                          # Backups automáticos (rotación 7 días)
├── exports/                          # Exportaciones Excel/CSV
├── temp/                             # Archivos temporales (seguro eliminar)
├── src/                              # Código fuente modular
│   ├── core/                         # Funcionalidades core
│   │   ├── config.py                 # Gestión config.yaml
│   │   ├── database.py               # Manager SQLite
│   │   ├── backup_manager.py         # Backups automáticos
│   │   ├── resource_manager.py       # Monitor CPU/RAM
│   │   └── logging.py                # Logging centralizado
│   ├── models/                       # Modelos de datos (dataclasses)
│   │   └── domain.py                 # Receipt, Transaction, Match, etc.
│   ├── repositories/                 # Capa de acceso a datos
│   │   ├── receipt_repository.py
│   │   ├── bank_repository.py
│   │   ├── match_repository.py
│   │   ├── queue_repository.py
│   │   └── ignored_repository.py
│   ├── services/                     # Lógica de negocio
│   │   ├── receipt_service.py        # Gestión de recibos
│   │   ├── bank_matching_service.py  # Algoritmo matching
│   │   ├── queue_service.py          # Gestión cola FIFO
│   │   ├── statistics_service.py     # Métricas y reportes
│   │   └── export_service.py         # Exportación datos
│   ├── utils/                        # Utilidades
│   │   ├── formatters.py             # Formato fecha/importe
│   │   └── file_helpers.py           # Procesamiento imágenes
│   └── ocr_processor.py              # Motor OCR con llama.cpp
├── scripts/                          # Scripts de mantenimiento
│   ├── setup_config.py               # Auto-configuración hardware
│   └── migrate_from_json.py          # Migración datos antiguos
├── tests/                            # Suite de tests (75 tests, 44% coverage)
│   ├── conftest.py                   # Fixtures compartidos
│   ├── unit/                         # Tests unitarios (servicios)
│   └── integration/                  # Tests integración (repositorios)
├── build_config/                     # Configuraciones PyInstaller
│   ├── processor.spec
│   ├── dashboard.spec
│   └── setup.spec
├── app_processor.py                  # UI Procesador (Streamlit)
├── app_dashboard.py                  # UI Dashboard (Streamlit)
├── config.yaml                       # Configuración principal
├── receipts.db                       # Base de datos SQLite
├── requirements.txt                  # Dependencias Python
└── pytest.ini                        # Configuración tests
```

## ⚙️ Configuración

### config.yaml - Configuración Principal

El archivo `config.yaml` contiene toda la configuración del sistema:

```yaml
processor:
  threads: 8                   # Threads CPU (auto-detectado por setup_config.py)
  batch_size: 2048             # Tamaño de batch para procesamiento
  gpu_layers: 35               # Capas en GPU (0 = solo CPU, 35 = todas en GPU)
  max_cpu_percent: 70          # Límite CPU modo normal (70% para multitarea)
  max_ram_percent: 70          # Límite RAM modo normal (70%)
  idle_boost_enabled: true     # Activar boost automático cuando PC idle
  idle_cpu_percent: 95         # Límite CPU en modo boost (95%)
  idle_ram_percent: 95         # Límite RAM en modo boost (95%)
  idle_timeout_seconds: 300    # Tiempo inactivo para activar boost (5 min)
  max_image_size_kb: 150       # Tamaño máximo de imagen para procesar
  
queue:
  max_attempts: 3              # Reintentos máximos por error antes de marcar como fallido
  warning_threshold: 300       # Advertir si cola > 300 items pendientes
  
paths:
  input_dir: ./img             # Carpeta de entrada para imágenes
  output_dir: ./result         # Carpeta de salida (recibos renombrados)
  database: ./receipts.db      # Archivo de base de datos SQLite
  bank_excel: ./img/bankmov/Detalle de Tarjeta de Crédito.xlsx  # Transacciones bancarias
  temp_dir: ./temp             # Archivos temporales
  backup_dir: ./backups        # Backups automáticos
  export_dir: ./exports        # Exportaciones Excel/CSV
  
backup:
  enabled: true                # Activar backups automáticos
  retention_days: 7            # Días de retención (elimina backups antiguos)
  backup_on_startup: true      # Backup al iniciar procesador
  
matching:
  amount_tolerance: 0.02       # Tolerancia de coincidencia (±2% del importe)
  exact_date_match: true       # Requiere fecha exacta para matching
  
logging:
  level: INFO                  # Nivel de logging (DEBUG, INFO, WARNING, ERROR)
  max_file_size_mb: 10         # Tamaño máximo de archivo de log
  backup_count: 5              # Número de archivos de log rotados
  
receipt_types:                # Tipos de recibo disponibles
  - taxis
  - comidas
  - hoteles
  - estacionamiento
  - vuelos
  - alquiler_coche
  - gasolina
  - tren
  - peajes
  - otros
```

### Ajustes Manuales

**Para mejorar rendimiento**:
- Aumentar `threads` si tienes CPU potente
- Aumentar `batch_size` si tienes mucha RAM
- Ajustar `gpu_layers` según VRAM disponible

**Para reducir uso de recursos**:
- Reducir `max_cpu_percent` y `max_ram_percent` (ej: 50%)
- Desactivar `idle_boost_enabled: false`
- Reducir `max_image_size_kb` (ej: 100)

**Para matching más flexible**:
- Aumentar `amount_tolerance` (ej: 0.05 = ±5%)
- Cambiar `exact_date_match: false` (permite ±1 día)

**Para añadir tipos de recibo personalizados**:
```yaml
receipt_types:
  - tu_tipo_personalizado  # Añadir al final de la lista
```

## 🖥️ Uso del Sistema

### 1. Procesador de Recibos (app_processor.py)

**Iniciar**:
```bash
streamlit run app_processor.py
```

**Panel de Control**:
- ▶️ **Start** - Iniciar procesamiento de la cola
- ⏸️ **Pause** - Pausar después del recibo actual (se puede reanudar)
- ⏹️ **Stop** - Detener inmediatamente (forzado)
- 🔄 **Toggle Normal/Turbo** - Cambiar modo de recursos

**Gestión de Cola**:
- **🔄 Scan & Enqueue Images** - Escanea carpeta `img/` y añade a cola
- Muestra: Pendientes, Procesando, Completados, Fallidos
- **Reset Interrupted** - Reintenta items interrumpidos (crashes)
- **Clear Completed** - Limpia items completados de la base de datos

**Logs en Tiempo Real**:
- **Registro de Actividad** - Eventos principales (inicio, fin, resúmenes)
- **Debug Logs** - Salida completa (incluye logs internos de llama.cpp)
- Auto-scroll para seguir últimos mensajes

**Estadísticas**:
- Estado del procesador (Running/Paused/Stopped)
- Modo de recursos (Normal 70% / Turbo 95%)
- Uso de CPU y RAM en tiempo real
- Imágenes procesadas / Total en cola
- ETA estimado de finalización

**Modos de Operación**:

**Modo Normal (70% recursos)**:
- Para uso mientras trabajas en otras tareas
- Procesamiento en segundo plano
- ~30-60 segundos por recibo
- No ralentiza el sistema

**Modo Turbo (95% recursos)**:
- Para procesamiento masivo dedicado
- Máximo rendimiento
- ~15-30 segundos por recibo
- Requiere PC dedicado

**Modo Automático** (recomendado):
- Detecta inactividad del sistema (5 minutos sin usar)
- Cambia automáticamente a Turbo
- Vuelve a Normal al detectar actividad
- Configurar `idle_boost_enabled: true` en config.yaml

**Flujo de Trabajo Típico**:
1. Colocar imágenes de recibos en `./img/`
2. Ejecutar `streamlit run app_processor.py`
3. Clic en "🔄 Scan & Enqueue Images" (muestra N imágenes añadidas)
4. Clic en "▶️ Start" para iniciar procesamiento
5. Monitorear progreso en logs y estadísticas
6. Recibos procesados aparecen en `./result/` con formato `YYMMDD_IMPORTE_TIPO.ext`
7. Puedes cerrar la ventana, la cola se guarda (reanudar después)
8. Notificación al completar (Windows Toast)

**Solución de Problemas**:
- **Cola no avanza**: Verificar logs, puede haber error en imagen específica
- **Uso alto de RAM**: Reducir `max_image_size_kb` en config.yaml
- **Muy lento**: Activar modo Turbo o ajustar `threads` en config
- **Items fallidos**: Usar "Reset Interrupted" para reintentar (máx 3 intentos)

### 2. Dashboard de Revisión (app_dashboard.py)

**Páginas:**

**📄 Receipts (Revisión)**
- Navegar por recibos procesados (◀️ Prev | Next ▶️)
- Ver imagen del recibo
- Editar tipo, fecha, monto
- Marcar como ignorado
- Ver coincidencia bancaria
- Aceptar conflictos

**🏦 Bank Transactions**
- Tabla de transacciones bancarias
- Estados: Matched ✅ | Unmatched ⚠️ | Conflict 🔴
- Botón para recargar desde Excel
- Recalcular coincidencias

**📊 Statistics**
- Total recibos, montos
- Breakdown por tipo (taxis, comidas, hoteles...)
- Gráficas de distribución
- Tasa de coincidencia

**📤 Export**
- Exportar todo a Excel/CSV
- Exportar solo transacciones sin coincidencia
- Descargar archivo generado

## 🔧 Tareas de Mantenimiento

### Migración de Datos Antiguos

Si tienes datos en JSON del sistema anterior:

```bash
python scripts/migrate_from_json.py
```

Lee:
- `result/historial_procesamiento.json` → `receipts` table
- `result/recibos_ignorados.json` → `ignored_receipts` table
- `result/conflictos_aceptados.json` → `matches` table

### Backup Manual

Backups automáticos se crean al iniciar el procesador. Para backup manual:

```python
from src.core.backup_manager import BackupManager

backup = BackupManager('./receipts.db', './backups', retention_days=7)
backup.perform_backup_with_cleanup()
```

### Limpieza de Cola

Si la cola tiene muchos items completados:

```python
from src.services.queue_service import QueueService

queue_service = QueueService(config)
removed = queue_service.clear_completed_items()
print(f"Removed {removed} completed items")
```

## 🧪 Testing

```bash
# Ejecutar todos los tests
pytest

# Con coverage
pytest --cov=src --cov-report=html

# Solo tests unitarios
pytest -m unit

# Solo tests de integración
pytest -m integration
```

Tests incluidos:
- Repositories (CRUD operations)
- Services (business logic)
- Queue (FIFO, retry, recovery)
- Formatters (date/amount normalization)

## 🏗️ Build (Crear Ejecutables)

Para crear los `.exe`:

```bash
# Activar entorno virtual
.venv\Scripts\activate

# Ejecutar build
build.bat
```

Genera en `dist/`:
- `RecibosProcessor.exe` (~500MB + modelos externos)
- `RecibosDashboard.exe` (~400MB)
- `ConfigSetup.exe` (~50MB)

**Importante:** Los modelos `.gguf` NO se incluyen en el .exe (son muy grandes). Deben estar en carpeta `models/` relativa al ejecutable.

## 📝 Arquitectura Técnica

### Capas

1. **UI Layer** (Streamlit)
   - `app_processor.py` - Control del procesador
   - `app_dashboard.py` - Dashboard de revisión

2. **Services Layer** (Business Logic)
   - `ReceiptService` - CRUD y renombrado de recibos
   - `BankMatchingService` - Algoritmo de coincidencia
   - `QueueService` - Gestión de cola con retry
   - `StatisticsService` - Agregaciones y reportes
   - `ExportService` - Exportación a Excel/CSV

3. **Repositories Layer** (Data Access)
   - `ReceiptRepository` - Acceso a recibos
   - `BankRepository` - Transacciones bancarias
   - `MatchRepository` - Coincidencias
   - `QueueRepository` - Cola de procesamiento
   - `IgnoredRepository` - Recibos ignorados

4. **Core Layer**
   - `Database` - Gestión de SQLite
   - `Config` - Configuración YAML
   - `BackupManager` - Backups automáticos
   - `ResourceMonitor` - Monitoreo CPU/RAM con boost

5. **Models Layer**
   - `Receipt`, `BankTransaction`, `Match`, `ProcessingQueueItem`

### Tecnologías

- **Backend**: Python 3.10+
- **UI**: Streamlit
- **Database**: SQLite 3
- **VLM**: llama.cpp + Qwen2.5-VL-7B
- **Data**: pandas, openpyxl
- **System**: psutil (resources), win10toast (notifications), pystray (tray)
- **Build**: PyInstaller
- **Testing**: pytest, pytest-cov

## ❓ Troubleshooting

### Error: "Model file not found"
- Verificar que modelos `.gguf` están en carpeta `models/`
- Revisar rutas en `config.yaml`

### Error: "GPU not detected"
- Normal si no tienes GPU NVIDIA
- El sistema usará CPU (más lento pero funciona)
- Ajustar `gpu_layers: 0` en config.yaml

### Procesamiento muy lento
- Ejecutar `ConfigSetup.exe` para reconfigurar
- Verificar que boost automático está activo
- Dejar el PC idle (>5 min sin uso) para activar modo boost

### Cola no avanza
- Revisar logs en `logs/processor.log`
- Verificar items en estado "interrupted": ejecutar auto-reset
- Revisar disco lleno o permisos

### Dashboard no muestra recibos
- Verificar que `receipts.db` existe y tiene datos
- Ejecutar migración: `python scripts/migrate_from_json.py`
- Revisar logs de la aplicación

## 📄 Licencia

[Especificar licencia según necesidad]

## 🤝 Contribución

Para contribuir al proyecto:
1. Implementar TODOs marcados en el código
2. Añadir tests para nuevas funcionalidades
3. Actualizar documentación
4. Mantener separación de capas (UI → Services → Repositories)

---

**Desarrollado con ❤️ para simplificar la gestión de recibos empresariales**
