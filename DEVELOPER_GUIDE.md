# 🔧 Guía Técnica para Desarrolladores

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

## 🚀 Instalación Completa

### Paso 1: Clonar y Preparar Entorno
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

# 6. (Opcional) Configurar ROC Skincare
python scripts/setup_rocskincare.py

# 7. Ejecutar aplicación unificada
streamlit run app.py
```

### Paso 2: Descarga de Modelos GGUF

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

## 📁 Estructura Completa del Proyecto

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
├── workers/                          # Directorios de trabajadores (ROC Skincare)
│   └── {nombre_trabajador}/          # Un directorio por trabajador
│       └── {MMYYYY}/                 # Periodos mensuales
│           ├── img/                  # Imágenes del periodo
│           ├── result/               # Recibos procesados
│           └── csv/                  # CSVs bancarios
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
│   │   ├── worker_repository.py
│   │   ├── period_repository.py
│   │   └── ignored_repository.py
│   ├── services/                     # Lógica de negocio
│   │   ├── receipt_service.py        # Gestión de recibos
│   │   ├── bank_matching_service.py  # Algoritmo matching
│   │   ├── queue_service.py          # Gestión cola FIFO
│   │   ├── statistics_service.py     # Métricas y reportes
│   │   ├── export_service.py         # Exportación datos
│   │   ├── worker_service.py         # Gestión trabajadores
│   │   ├── period_service.py         # Gestión periodos
│   │   └── period_closure_service.py # Cierre de periodos
│   ├── utils/                        # Utilidades
│   │   ├── formatters.py             # Formato fecha/importe
│   │   └── file_helpers.py           # Procesamiento imágenes
│   └── ocr_processor.py              # Motor OCR con llama.cpp
├── modules/                          # Páginas modulares para app unificada
│   ├── processor_page.py             # Página del procesador OCR
│   ├── failed_items_page.py          # Página de items fallidos
│   ├── dashboard_receipts.py         # Página de recibos
│   ├── dashboard_bank_transactions.py # Página de transacciones
│   ├── dashboard_statistics.py       # Página de estadísticas
│   ├── dashboard_export.py           # Página de exportación
│   ├── rocskincare_workers.py        # Gestión de trabajadores
│   ├── rocskincare_periods.py        # Gestión de periodos
│   ├── rocskincare_image_upload.py   # Carga de imágenes
│   ├── rocskincare_csv_upload.py     # Carga de CSV
│   ├── rocskincare_period_closure.py # Cierre de periodos
│   ├── rocskincare_visualization.py  # Visualización de datos
│   ├── admin_page.py                 # Panel de administración
│   └── admin_test_receipt.py         # Test de recibos
├── scripts/                          # Scripts de mantenimiento
│   ├── setup_config.py               # Auto-configuración hardware
│   ├── setup_rocskincare.py          # Configuración ROC Skincare
│   ├── migrate_from_json.py          # Migración datos antiguos
│   └── normalize_amounts.py          # Normalización de importes
├── tests/                            # Suite de tests (75 tests, 44% coverage)
│   ├── conftest.py                   # Fixtures compartidos
│   ├── unit/                         # Tests unitarios (servicios)
│   └── integration/                  # Tests integración (repositorios)
├── build_config/                     # Configuraciones PyInstaller
│   ├── processor.spec
│   ├── dashboard.spec
│   └── setup.spec
├── doc/                              # Documentación adicional
│   ├── ADMIN_PANEL_FEATURES.md
│   ├── IMPLEMENTATION_GUIDE.md
│   ├── README_DASHBOARD.md
│   ├── README_ROCSKINCARE.md
│   └── ...
├── app.py                            # ✨ Aplicación unificada (punto de entrada)
├── app_processor.py                  # UI Procesador (Streamlit, legacy)
├── app_dashboard.py                  # UI Dashboard (Streamlit, legacy)
├── app_rocskincare.py                # UI ROC Skincare (Streamlit, legacy)
├── config.yaml                       # Configuración principal
├── receipts.db                       # Base de datos SQLite
├── requirements.txt                  # Dependencias Python
└── pytest.ini                        # Configuración tests
```

## ⚙️ Configuración Detallada

### config.yaml - Referencia Completa

El archivo `config.yaml` contiene toda la configuración del sistema:

```yaml
# Modelo OCR
model:
  model_path: "./models/Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf"
  clip_model_path: "./models/mmproj-Qwen2.5-VL-7B-Instruct-f16.gguf"
  n_ctx: 32768                 # Contexto del modelo
  n_batch: 2048                # Tamaño de batch para procesamiento
  n_gpu_layers: 33             # Capas en GPU (0 = solo CPU, 33 = todas)

# Procesador
processor:
  threads: 8                   # Threads CPU (auto-detectado por setup_config.py)
  max_cpu_percent: 70          # Límite CPU modo normal (70% para multitarea)
  max_ram_percent: 70          # Límite RAM modo normal (70%)
  idle_boost_enabled: true     # Activar boost automático cuando PC idle
  idle_cpu_percent: 95         # Límite CPU en modo boost (95%)
  idle_ram_percent: 95         # Límite RAM en modo boost (95%)
  idle_timeout_seconds: 300    # Tiempo inactivo para activar boost (5 min)
  max_image_size_kb: 150       # Tamaño máximo de imagen para procesar
  
# Cola de procesamiento
queue:
  max_attempts: 3              # Reintentos máximos por error antes de marcar como fallido
  warning_threshold: 300       # Advertir si cola > 300 items pendientes
  
# Rutas del sistema
paths:
  input_dir: "./img"           # Carpeta de entrada para imágenes
  result_dir: "./result"       # Carpeta de salida (recibos renombrados)
  database: "./receipts.db"    # Archivo de base de datos SQLite
  bank_excel: "./img/bankmov/Detalle de Tarjeta de Crédito.xlsx"
  temp_dir: "./temp"           # Archivos temporales
  backup_dir: "./backups"      # Backups automáticos
  export_dir: "./exports"      # Exportaciones Excel/CSV
  logs_dir: "./logs"           # Directorio de logs
  
# Backups automáticos
backup:
  enabled: true                # Activar backups automáticos
  retention_days: 7            # Días de retención (elimina backups antiguos)
  backup_on_startup: true      # Backup al iniciar procesador
  
# Coincidencia bancaria
matching:
  amount_tolerance: 0.02       # Tolerancia de coincidencia (±2% del importe)
  exact_date_match: true       # Requiere fecha exacta para matching
  
# Logging
logging:
  level: "INFO"                # Nivel de logging (DEBUG, INFO, WARNING, ERROR)
  max_file_size_mb: 10         # Tamaño máximo de archivo de log
  backup_count: 5              # Número de archivos de log rotados
  
# Tipos de recibo disponibles
receipt_types:
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

### Ajustes de Rendimiento

**Para mejorar rendimiento**:
```yaml
processor:
  threads: 12                  # Aumentar si tienes CPU potente
  max_cpu_percent: 90          # Usar más recursos
  
model:
  n_batch: 4096                # Aumentar si tienes mucha RAM
  n_gpu_layers: 33             # Todas las capas en GPU
```

**Para reducir uso de recursos**:
```yaml
processor:
  threads: 4                   # Reducir threads
  max_cpu_percent: 50          # Limitar al 50%
  max_ram_percent: 50
  max_image_size_kb: 100       # Reducir tamaño de imágenes
  idle_boost_enabled: false    # Desactivar boost automático
  
model:
  n_batch: 1024                # Reducir batch
  n_gpu_layers: 0              # Solo CPU
```

**Para matching más flexible**:
```yaml
matching:
  amount_tolerance: 0.05       # ±5% en lugar de ±2%
  exact_date_match: false      # Permite ±1 día de diferencia
```

## 📊 Base de Datos

El sistema utiliza SQLite con las siguientes tablas:

### Esquema de Tablas

**Tablas Generales:**
```sql
-- Recibos procesados
CREATE TABLE receipts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_path TEXT NOT NULL,
    renamed_path TEXT,
    receipt_date TEXT,
    amount REAL,
    receipt_type TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT,
    processed_at TEXT,
    worker_id INTEGER,
    period_id INTEGER
);

-- Transacciones bancarias
CREATE TABLE bank_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date TEXT NOT NULL,
    amount REAL NOT NULL,
    description TEXT,
    loaded_at TEXT,
    worker_id INTEGER,
    period_id INTEGER
);

-- Coincidencias
CREATE TABLE matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_id INTEGER,
    transaction_id INTEGER,
    matched_at TEXT,
    match_type TEXT,
    confidence REAL,
    FOREIGN KEY (receipt_id) REFERENCES receipts(id),
    FOREIGN KEY (transaction_id) REFERENCES bank_transactions(id)
);

-- Cola de procesamiento
CREATE TABLE processing_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path TEXT NOT NULL UNIQUE,
    status TEXT DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    error_message TEXT,
    queued_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    worker_id INTEGER,
    period_id INTEGER
);

-- Estado del procesador
CREATE TABLE processor_state (
    id INTEGER PRIMARY KEY,
    is_running INTEGER DEFAULT 0,
    current_item_id INTEGER,
    last_updated TEXT
);
```

**Tablas ROC Skincare:**
```sql
-- Trabajadores
CREATE TABLE workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    is_active INTEGER DEFAULT 1,
    created_at TEXT
);

-- Periodos
CREATE TABLE periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id INTEGER NOT NULL,
    month INTEGER NOT NULL,
    year INTEGER NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    is_active INTEGER DEFAULT 0,
    created_at TEXT,
    closed_at TEXT,
    FOREIGN KEY (worker_id) REFERENCES workers(id),
    UNIQUE (worker_id, month, year)
);

-- Cierres de periodos
CREATE TABLE period_closures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period_id INTEGER NOT NULL,
    closed_at TEXT,
    total_receipts INTEGER,
    total_amount REAL,
    matched_count INTEGER,
    unmatched_count INTEGER,
    export_path TEXT,
    notes TEXT,
    FOREIGN KEY (period_id) REFERENCES periods(id)
);
```

## 🏗️ Arquitectura del Sistema

### Capas de la Aplicación

```
┌─────────────────────────────────────────────────────────┐
│                    UI Layer (Streamlit)                  │
│  app.py, app_processor.py, app_dashboard.py, modules/*  │
└─────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────┐
│              Services Layer (Business Logic)             │
│  ReceiptService, BankMatchingService, QueueService, etc. │
└─────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────┐
│            Repositories Layer (Data Access)              │
│  ReceiptRepository, BankRepository, MatchRepository, etc.│
└─────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    Core Layer                            │
│  Database, Config, BackupManager, ResourceMonitor, etc.  │
└─────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────┐
│                   Models Layer                           │
│         Receipt, BankTransaction, Match, etc.            │
└─────────────────────────────────────────────────────────┘
```

### Componentes Principales

**1. UI Layer (Streamlit)**
- `app.py` - Aplicación unificada con navegación entre módulos
- `modules/*` - Páginas modulares independientes
- `app_processor.py`, `app_dashboard.py`, `app_rocskincare.py` - Apps legacy

**2. Services Layer**
- `ReceiptService` - CRUD de recibos, renombrado, validación
- `BankMatchingService` - Algoritmo de coincidencia, detección de conflictos
- `QueueService` - Gestión de cola FIFO con reintentos
- `StatisticsService` - Agregaciones y métricas
- `ExportService` - Exportación a Excel/CSV
- `WorkerService` - Gestión de trabajadores
- `PeriodService` - Gestión de periodos
- `PeriodClosureService` - Cierre y exportación de periodos

**3. Repositories Layer**
- Abstracción de acceso a datos
- Operaciones CRUD básicas
- Queries especializadas
- Transacciones de base de datos

**4. Core Layer**
- `Database` - Connection pooling, gestión de SQLite
- `Config` - Carga y validación de config.yaml
- `BackupManager` - Backups automáticos con rotación
- `ResourceMonitor` - Monitoreo CPU/RAM con boost automático
- `Logging` - Logging centralizado y estructurado

**5. Models Layer**
- Dataclasses para entidades del dominio
- Validación de tipos
- Serialización/deserialización

### Flujo de Procesamiento de Recibos

```
1. Usuario coloca imagen en ./img/
2. Procesador escanea y añade a processing_queue
3. QueueService obtiene siguiente item (FIFO)
4. OCRProcessor procesa la imagen con VLM
5. ReceiptService valida y guarda en receipts
6. ReceiptService renombra archivo (YYMMDD_IMPORTE_TIPO.ext)
7. BankMatchingService busca coincidencias automáticas
8. Dashboard permite revisión y edición manual
9. ExportService genera reportes finales
```

### Tecnologías y Dependencias

- **Backend**: Python 3.10+
- **UI Framework**: Streamlit 1.28.0
- **Database**: SQLite 3
- **VLM Engine**: llama-cpp-python 0.3.16
- **Data Processing**: pandas 2.3.3, openpyxl 3.1.3
- **Configuration**: PyYAML 6.0.3
- **System Monitoring**: psutil 5.9.0+
- **Image Processing**: Pillow 12.1.0
- **Notifications**: win10toast 0.9+ (Windows)
- **System Tray**: pystray 0.19.0+
- **Testing**: pytest 7.4.0+, pytest-cov 4.1.0+
- **Build**: PyInstaller 6.0.0+

## 🧪 Testing

### Ejecutar Tests

```bash
# Activar entorno virtual
.venv\Scripts\activate

# Todos los tests
pytest

# Con coverage
pytest --cov=src --cov-report=html

# Solo tests unitarios
pytest -m unit

# Solo tests de integración
pytest -m integration

# Test específico
pytest tests/unit/test_receipt_service.py

# Ver coverage en navegador
start htmlcov/index.html  # Windows
```

### Estructura de Tests

```
tests/
├── conftest.py                    # Fixtures compartidos
├── unit/                          # Tests unitarios
│   ├── test_receipt_service.py
│   ├── test_bank_matching_service.py
│   ├── test_queue_service.py
│   ├── test_statistics_service.py
│   └── test_formatters.py
└── integration/                   # Tests de integración
    ├── test_receipt_repository.py
    ├── test_bank_repository.py
    ├── test_match_repository.py
    └── test_queue_repository.py
```

### Cobertura Actual

- **Tests totales**: 75
- **Cobertura**: ~44%
- **Áreas cubiertas**: Repositories, Services, Queue, Formatters
- **Áreas pendientes**: OCR Processor, UI components

## 🏗️ Build y Distribución

### Crear Ejecutables

```bash
# Activar entorno virtual
.venv\Scripts\activate

# Ejecutar build completo
build.bat
```

Esto genera en `dist/`:
- `RecibosProcessor.exe` (~500MB + modelos externos)
- `RecibosDashboard.exe` (~400MB)
- `ConfigSetup.exe` (~50MB)

### Configuración PyInstaller

Los archivos `.spec` en `build_config/` contienen la configuración:

**processor.spec:**
```python
# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['app_processor.py'],
    pathex=[],
    binaries=[],
    datas=[('config.yaml', '.'), ('src', 'src')],
    hiddenimports=['llama_cpp', 'streamlit', 'PIL', 'openpyxl'],
    # ...
)
```

**Importante**: 
- Los modelos `.gguf` NO se incluyen en el .exe (son muy grandes)
- Deben estar en carpeta `models/` relativa al ejecutable
- Total distribución: ~500MB (exe) + ~5GB (modelos)

### Distribución

Para distribuir la aplicación:

1. **Copiar carpeta completa**:
   ```
   dist/
   ├── RecibosProcessor.exe
   ├── models/
   │   ├── Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf
   │   └── mmproj-Qwen2.5-VL-7B-Instruct-f16.gguf
   └── config.yaml
   ```

2. **Primera ejecución**:
   - Ejecutar `ConfigSetup.exe` para auto-configurar
   - O ajustar `config.yaml` manualmente

3. **Uso**:
   - Doble clic en `RecibosProcessor.exe`
   - Se abre navegador en `http://localhost:8501`

## 🔧 Tareas de Mantenimiento

### Migración de Datos Antiguos

Si tienes datos en JSON del sistema anterior:

```bash
python scripts/migrate_from_json.py
```

Migra:
- `result/historial_procesamiento.json` → tabla `receipts`
- `result/recibos_ignorados.json` → tabla `ignored_receipts`
- `result/conflictos_aceptados.json` → tabla `matches`

### Backup Manual

Backups automáticos se crean al iniciar el procesador. Para backup manual:

```python
from src.core.backup_manager import BackupManager

backup = BackupManager('./receipts.db', './backups', retention_days=7)
backup_path = backup.perform_backup_with_cleanup()
print(f"Backup creado en: {backup_path}")
```

### Limpieza de Cola

Si la cola tiene muchos items completados:

```python
from src.core.config import get_config
from src.services.queue_service import QueueService

config = get_config()
queue_service = QueueService(config)
removed = queue_service.clear_completed_items()
print(f"Eliminados {removed} items completados")
```

### Normalización de Importes

Para normalizar importes en la base de datos:

```bash
python scripts/normalize_amounts.py
```

Corrige:
- Importes con formato incorrecto
- Conversión de strings a números
- Validación de rangos

### Logs y Debugging

**Ubicación de logs**:
- `logs/processor.log` - Procesador OCR
- `logs/dashboard.log` - Dashboard
- `logs/unified_app.log` - Aplicación unificada

**Cambiar nivel de logging**:
```yaml
# config.yaml
logging:
  level: "DEBUG"  # DEBUG, INFO, WARNING, ERROR
```

**Ver logs en tiempo real** (Windows):
```powershell
Get-Content logs/processor.log -Wait -Tail 50
```

## ❓ Troubleshooting Avanzado

### Problemas con Modelos

**Error: "Model file not found"**
```bash
# Verificar rutas
python -c "from pathlib import Path; print(Path('models/Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf').exists())"

# Revisar config.yaml
python -c "import yaml; print(yaml.safe_load(open('config.yaml'))['model'])"
```

**Error: "GPU not detected"**
- Normal si no tienes GPU NVIDIA
- El sistema usará CPU (más lento pero funciona)
- Ajustar `gpu_layers: 0` en config.yaml

**Error: "Out of Memory"**
```yaml
# Reducir uso de memoria en config.yaml
model:
  n_batch: 512        # Reducir batch size
  n_gpu_layers: 0     # Desactivar GPU
processor:
  max_image_size_kb: 80  # Reducir tamaño de imágenes
```

### Problemas de Rendimiento

**Procesamiento muy lento**
1. Ejecutar auto-configuración:
   ```bash
   python scripts/setup_config.py
   ```

2. Verificar boost automático:
   ```yaml
   processor:
     idle_boost_enabled: true
     idle_timeout_seconds: 300  # 5 minutos
   ```

3. Dejar el PC idle (>5 min sin uso) para activar modo boost

4. Verificar uso de GPU:
   ```python
   import llama_cpp
   # Debería mostrar GPU disponible si está configurada
   ```

**CPU/RAM al 100%**
```yaml
# Reducir límites en config.yaml
processor:
  max_cpu_percent: 50
  max_ram_percent: 50
  threads: 4
```

### Problemas con Base de Datos

**Cola no avanza**
```bash
# Revisar items interrumpidos
python -c "
from src.core.database import get_database
from src.core.config import get_config
config = get_config()
db = get_database(config.paths['database'])
cursor = db.execute('SELECT COUNT(*) FROM processing_queue WHERE status = ?', ('interrupted',))
print(f'Items interrumpidos: {cursor.fetchone()[0]}')
"
```

**Corrupción de base de datos**
```bash
# Verificar integridad
sqlite3 receipts.db "PRAGMA integrity_check;"

# Recuperar desde backup
copy backups\receipts_YYYYMMDD_HHMMSS.db receipts.db
```

**Resetear base de datos**
```bash
# PRECAUCIÓN: Esto elimina todos los datos
del receipts.db
python scripts/setup_config.py  # Recrear tablas
```

### Problemas con ROC Skincare

**Trabajador no se puede crear**
- Verificar nombre único (case-insensitive)
- Revisar permisos de carpeta `workers/`

**Periodo no se activa**
- Solo puede haber un periodo activo a la vez
- Desactivar periodo actual primero

**CSV no carga**
- Verificar formato (debe tener columnas: Fecha, Importe, Descripción)
- Revisar encoding (debe ser UTF-8)

### Problemas de Interfaz

**Dashboard no muestra recibos**
```bash
# Verificar datos en base de datos
python -c "
from src.core.database import get_database
from src.core.config import get_config
config = get_config()
db = get_database(config.paths['database'])
cursor = db.execute('SELECT COUNT(*) FROM receipts')
print(f'Total recibos: {cursor.fetchone()[0]}')
"
```

**Streamlit no inicia**
```bash
# Verificar instalación
streamlit --version

# Reinstalar si es necesario
pip install --force-reinstall streamlit==1.28.0

# Limpiar caché
streamlit cache clear
```

**Puerto ocupado**
```bash
# Cambiar puerto
streamlit run app.py --server.port 8502
```

## 🤝 Contribución al Proyecto

### Implementar Nuevas Funcionalidades

1. **Crear rama de feature**:
   ```bash
   git checkout -b feature/nueva-funcionalidad
   ```

2. **Seguir estructura de capas**:
   - Modelo → `src/models/`
   - Repository → `src/repositories/`
   - Service → `src/services/`
   - UI → `modules/` o `app_*.py`

3. **Añadir tests**:
   ```bash
   # Crear test en tests/unit/ o tests/integration/
   pytest tests/unit/test_nueva_funcionalidad.py
   ```

4. **Documentar**:
   - Docstrings en funciones
   - Actualizar README si es necesario
   - Añadir ejemplos de uso

### TODOs Pendientes

Ver comentarios `# TODO:` en el código para áreas de mejora identificadas.

### Coding Standards

- **PEP 8** para estilo de código
- **Type hints** para parámetros y retornos
- **Docstrings** en formato Google
- **Tests** para nueva lógica de negocio
- **Logging** en lugar de prints

### Pull Requests

1. Asegurar que todos los tests pasan
2. Cobertura de tests >40% para nuevo código
3. Actualizar documentación
4. Describir cambios claramente

---

**Documentación para desarrolladores del Receipt Management System**
