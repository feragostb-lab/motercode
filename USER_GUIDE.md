# Receipt Management System - Aplicación Unificada

## 🎯 Descripción

Sistema unificado de gestión de recibos con tres módulos principales integrados en una sola aplicación:

1. **🖼️ OCR Processor** - Procesamiento automático de imágenes de recibos
2. **📊 Dashboard** - Revisión y gestión de recibos procesados
3. **👥 ROC Skincare** - Gestión multi-trabajador y multi-periodo

## 🚀 Inicio Rápido

### Ejecutar la Aplicación Unificada

```bash
streamlit run app.py
```

La aplicación estará disponible en `http://localhost:8501`

## 📁 Estructura del Proyecto

```
gguf/
├── app.py                      # ✨ PUNTO DE ENTRADA PRINCIPAL - Aplicación unificada
├── app_processor.py            # Módulo OCR Processor (independiente, también importado)
├── app_dashboard.py            # Módulo Dashboard (independiente, también importado)
├── app_rocskincare.py          # Módulo ROC Skincare (independiente, también importado)
├── modules/                    # Páginas modulares para la app unificada
│   ├── processor_page.py       # Página del procesador OCR
│   ├── failed_items_page.py    # Página de items fallidos
│   ├── dashboard_*.py          # Páginas del dashboard
│   ├── rocskincare_*.py        # Páginas de ROC Skincare
│   ├── admin_page.py           # Panel de administración
│   └── admin_test_receipt.py   # Página de test de recibos
├── src/                        # Código fuente principal
│   ├── core/                   # Componentes centrales
│   ├── models/                 # Modelos de datos
│   ├── ocr_processor.py        # Procesador OCR principal
│   ├── repositories/           # Capa de acceso a datos
│   ├── services/               # Lógica de negocio
│   └── utils/                  # Utilidades
└── config.yaml                 # Configuración del sistema
```

## 🎮 Guía de Uso

### Navegación Principal

En la barra lateral izquierda, selecciona el módulo que deseas usar:

#### 1. 🖼️ OCR Processor

**Páginas disponibles:**
- **🖼️ Procesador**: Procesamiento principal de recibos
- **❌ Items Fallidos**: Revisión de items que fallaron en el procesamiento

**Panel de Control (Procesador):**
- **Start/Pause/Stop**: Controla el procesamiento de imágenes
- **Toggle Mode**: Cambia entre modo Normal (70%) y Turbo (95%)
- **Scan & Enqueue**: Escanea el directorio de entrada y añade imágenes a la cola

**Funcionalidades:**
- Procesamiento en segundo plano con gestión de recursos automática
- Monitoreo en tiempo real (CPU, RAM, progreso)
- Sistema de logs con filtrado automático
- Cálculo de ETA basado en velocidad de procesamiento
- Modo Turbo automático cuando el sistema está inactivo

**Flujo de trabajo:**
1. Coloca imágenes de recibos en el directorio `./img/` (o el configurado)
2. Haz clic en "Scan & Enqueue Images"
3. Haz clic en "Start" para iniciar el procesamiento
4. Monitorea el progreso en tiempo real
5. Los resultados se guardan en `./result/`

#### 2. 📊 Dashboard

**Páginas disponibles:**

**📄 Recibos**
- Revisar todos los recibos procesados
- Editar fecha, monto y tipo de recibo
- Ver imagen original
- Marcar recibos como ignorados
- Navegar entre recibos con filtros

**🏦 Transacciones Bancarias**
- Importar transacciones desde Excel
- Ver matching automático con recibos
- Identificar transacciones sin match
- Navegar entre transacciones no emparejadas

**📊 Estadísticas**
- Ver estadísticas globales del sistema
- Desglose por tipo de recibo
- Gráficos de distribución
- Métricas de matching

**📥 Exportar**
- Exportar datos a Excel/CSV
- Incluye recibos, transacciones y matches
- Filtrado personalizable

#### 3. 👥 ROC Skincare (Multi-Trabajador)

**Páginas disponibles:**

**👥 Trabajadores**
- Crear y gestionar trabajadores
- Activar/desactivar trabajadores
- Nombres únicos (case-insensitive)
- Estructura de directorios automática

**📅 Periodos**
- Crear periodos mensuales por trabajador
- Un periodo activo para procesamiento
- Ver estadísticas por periodo
- Control de estado (ACTIVE/CLOSED)

**�️ Cargar Imágenes**
- Subir imágenes de recibos al periodo activo
- Procesar imágenes directamente desde la interfaz
- Gestión de archivos por trabajador y periodo

**📤 Cargar CSV**
- Subir transacciones bancarias del periodo activo
- Soporte para múltiples cargas (se reemplazan)
- Re-matching automático tras cada carga
- Archivos timestamped

**🔒 Cierre de Periodos**
- Cerrar periodos completados
- Exportación automática al cerrar
- Snapshot de estadísticas
- Reabrir periodos si es necesario

**📊 Visualización**
- Tablas de recibos por periodo
- Detalle de matches y conflictos
- Exportación de datos del periodo

#### 4. ⚙️ Administración

**Páginas disponibles:**

**⚙️ Administración**
- Panel de control administrativo del sistema
- Gestión de configuración
- Herramientas de mantenimiento

**🧪 Test Receipt**
- Probar procesamiento de recibos individuales
- Validación de OCR y extracción de datos
- Debug y resolución de problemas

## ⚙️ Configuración

### Archivo `config.yaml`

```yaml
# Configuración de paths
paths:
  input_dir: "./img"
  result_dir: "./result"
  database: "./receipts.db"
  logs_dir: "./logs"
  backups_dir: "./backups"

# Configuración del modelo OCR
model:
  model_path: "./models/Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf"
  clip_model_path: "./models/mmproj-Qwen2.5-VL-7B-Instruct-f16.gguf"
  n_ctx: 32768
  n_batch: 2048
  n_gpu_layers: 33

# Límites de recursos
resource_limits:
  max_cpu_percent: 70
  max_ram_percent: 70
  idle_boost_cpu: 95
  idle_boost_ram: 95
```

### Configuración Automática

```bash
python scripts/setup_config.py
```

Este script detecta automáticamente tu hardware y configura los parámetros óptimos.

## 🔧 Instalación

### Requisitos

- Python 3.10+
- CUDA (opcional, para aceleración GPU)
- 16GB RAM mínimo (recomendado 32GB)

### Pasos de Instalación

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd gguf
```

2. **Crear entorno virtual**
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Descargar modelos**
Coloca los modelos GGUF en la carpeta `./models/`:
- `Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf`
- `mmproj-Qwen2.5-VL-7B-Instruct-f16.gguf`
> 💡 **Nota**: Los modelos GGUF deben descargarse desde Hugging Face u otra fuente compatible.
5. **Configurar el sistema**
```bash
python scripts/setup_config.py
```

6. **(Opcional) Configurar ROC Skincare**
```bash
python scripts/setup_rocskincare.py
```

7. **Ejecutar la aplicación**
```bash
streamlit run app.py
```

## 📊 Base de Datos

El sistema utiliza SQLite con las siguientes tablas principales:

### Tablas Generales
- `receipts` - Recibos procesados
- `bank_transactions` - Transacciones bancarias
- `matches` - Matches entre recibos y transacciones
- `processing_queue` - Cola de procesamiento
- `processor_state` - Estado del procesador

### Tablas ROC Skincare
- `workers` - Trabajadores
- `periods` - Periodos por trabajador
- `period_closures` - Cierres de periodos

## 🎯 Flujos de Trabajo Típicos

### Flujo Básico (Sin Multi-Trabajador)

1. Configurar el sistema con `setup_config.py`
2. Colocar imágenes en `./img/`
3. Usar el módulo **OCR Processor** para procesar las imágenes
4. Importar transacciones bancarias en **Dashboard > Transacciones Bancarias**
5. Revisar y editar recibos en **Dashboard > Recibos**
6. Exportar datos en **Dashboard > Exportar**

### Flujo ROC Skincare (Multi-Trabajador)

1. Configurar ROC Skincare con `setup_rocskincare.py`
2. Crear trabajadores en **ROC Skincare > Trabajadores**
3. Crear periodos para cada trabajador en **ROC Skincare > Periodos**
4. Activar el periodo a procesar
5. Colocar imágenes del trabajador en `./workers/{nombre}/{MMYYYY}/img/`
6. Usar **OCR Processor** para procesar
7. Subir CSV bancario en **ROC Skincare > Cargar CSV**
8. Revisar y cerrar en **ROC Skincare > Cierre de Periodos**
9. Visualizar datos en **ROC Skincare > Visualización**

## 🐛 Solución de Problemas

### La aplicación no inicia

- Verifica que el entorno virtual esté activado
- Asegúrate de que todas las dependencias estén instaladas
- Revisa los logs en `./logs/`

### El procesador no encuentra las imágenes

- Verifica la ruta del directorio de entrada en `config.yaml`
- Asegúrate de que las imágenes tengan extensiones válidas (.jpg, .jpeg, .png, .webp)

### Error de memoria (Out of Memory)

- Reduce `n_batch` en `config.yaml`
- Reduce `n_gpu_layers` si usas GPU
- Cierra otras aplicaciones que consuman RAM

### Conflictos de worker names

- Los nombres de trabajadores son case-insensitive
- Verifica que no exista un trabajador con nombre similar (ej: "David" vs "david")

## 📚 Documentación Adicional

- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - Guía técnica para desarrolladores
- [doc/IMPLEMENTATION_GUIDE.md](doc/IMPLEMENTATION_GUIDE.md) - Detalles de implementación
- [doc/README_ROCSKINCARE.md](doc/README_ROCSKINCARE.md) - Documentación específica de ROC Skincare
- [doc/README_DASHBOARD.md](doc/README_DASHBOARD.md) - Guía del dashboard
- [doc/ROCSkincare_Implementation.md](doc/ROCSkincare_Implementation.md) - Detalles de implementación multi-trabajador

## 🔄 Migración desde Versiones Anteriores

Si venías usando las aplicaciones separadas (`app_processor.py`, `app_dashboard.py`, `app_rocskincare.py`), puedes seguir usándolas, pero se recomienda migrar a la aplicación unificada `app.py` para:

- Navegación más fluida entre módulos
- Sesión compartida entre componentes
- Mejor experiencia de usuario
- Mantenimiento simplificado

Los datos existentes en la base de datos son completamente compatibles.

## 📝 Changelog

### v2.0 - Aplicación Unificada (Enero 2026)

- ✨ Nueva aplicación unificada `app.py`
- 🎨 Navegación mejorada entre módulos
- 📦 Arquitectura modular con páginas separadas
- 🔧 Sesión compartida entre componentes
- ⚙️ Panel de administración y herramientas de testing
- 🖼️ Página de carga de imágenes para ROC Skincare
- ❌ Gestión de items fallidos en procesamiento
- 📚 Documentación actualizada

### v1.0 - Versiones Separadas

- Aplicaciones independientes por módulo
- Funcionalidad completa de cada componente

## 👨‍💻 Autor

Sistema desarrollado para la gestión automatizada de recibos y transacciones bancarias.

## 📄 Licencia

[Especificar licencia]
