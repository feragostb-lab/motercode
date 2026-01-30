# 🧾 Receipt Management System

Sistema automatizado para procesar recibos mediante OCR con IA (Vision Language Model) y gestionar coincidencias con transacciones bancarias.

## 🚀 Inicio Rápido

### Ejecutar la Aplicación

```bash
# Aplicación unificada (RECOMENDADO)
streamlit run app.py
```

La aplicación unificada integra cuatro módulos principales:
- 🖼️ **OCR Processor** - Procesamiento automático de recibos
- 📊 **Dashboard** - Revisión y gestión de datos
- 👥 **ROC Skincare** - Gestión multi-trabajador/multi-periodo
- ⚙️ **Administración** - Herramientas de configuración y testing

### Aplicaciones Legacy (Separadas)

```bash
streamlit run app_processor.py   # Solo procesador OCR
streamlit run app_dashboard.py   # Solo dashboard
streamlit run app_rocskincare.py  # Solo ROC Skincare
```

## 📚 Documentación

### 📖 [USER_GUIDE.md](USER_GUIDE.md) - Guía del Usuario
**Para usuarios finales del sistema**
- Cómo usar cada módulo de la aplicación
- Navegación y flujos de trabajo
- Gestión de recibos, transacciones y trabajadores
- Configuración básica

### 🔧 [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - Guía Técnica
**Para desarrolladores y administradores del sistema**
- Instalación completa y requisitos
- Configuración avanzada (config.yaml)
- Arquitectura y estructura del código
- Base de datos y migraciones
- Testing y build de ejecutables
- Troubleshooting detallado

### 📁 Documentación Adicional

- [doc/IMPLEMENTATION_GUIDE.md](doc/IMPLEMENTATION_GUIDE.md) - Detalles de implementación
- [doc/README_ROCSKINCARE.md](doc/README_ROCSKINCARE.md) - Documentación ROC Skincare
- [doc/ADMIN_PANEL_FEATURES.md](doc/ADMIN_PANEL_FEATURES.md) - Features del panel admin
- [TEST_GUIDE.md](TEST_GUIDE.md) - Guía de testing

## 🌟 Características Principales

- **OCR con IA** - Extracción inteligente de datos con Qwen2.5-VL-7B
- **Procesamiento Automático** - Cola FIFO con gestión de reintentos
- **Matching Bancario** - Coincidencia automática con transacciones
- **Multi-Trabajador** - Gestión de múltiples trabajadores y periodos
- **Gestión de Recursos** - Modo turbo automático cuando el PC está inactivo
- **Exportación** - Reportes en Excel/CSV
- **Base de Datos SQLite** - Persistencia local sin configuración

## ⚡ Instalación Rápida

```bash
# 1. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Descargar modelos GGUF en ./models/
# Ver DEVELOPER_GUIDE.md para enlaces de descarga

# 4. Auto-configuración
python scripts/setup_config.py

# 5. Ejecutar aplicación
streamlit run app.py
```

> 💡 **Nota**: Los modelos GGUF deben descargarse desde [Hugging Face](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct-GGUF) (~5 GB)

## 📁 Estructura del Proyecto

```
gguf/
├── app.py                    # ✨ Aplicación unificada (punto de entrada)
├── modules/                  # Páginas modulares de la aplicación
├── src/                      # Código fuente
│   ├── core/                 # Componentes centrales
│   ├── models/               # Modelos de datos
│   ├── repositories/         # Acceso a datos
│   ├── services/             # Lógica de negocio
│   └── utils/                # Utilidades
├── scripts/                  # Scripts de mantenimiento
├── tests/                    # Suite de tests
├── models/                   # Modelos GGUF (descargar aparte)
├── config.yaml               # Configuración principal
└── receipts.db               # Base de datos SQLite
```

Ver [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) para la estructura completa.

## ⚙️ Configuración Básica

El archivo `config.yaml` contiene la configuración del sistema:

```yaml
paths:
  input_dir: "./img"          # Imágenes de entrada
  result_dir: "./result"      # Recibos procesados
  database: "./receipts.db"   # Base de datos

processor:
  max_cpu_percent: 70         # Límite CPU (70% normal, 95% turbo)
  max_ram_percent: 70         # Límite RAM
  idle_boost_enabled: true    # Boost automático cuando idle

model:
  model_path: "./models/Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf"
  n_gpu_layers: 33            # 0 para solo CPU, 33 para GPU
```

Ver [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) para configuración avanzada.

## 🧪 Testing

```bash
# Ejecutar tests
pytest

# Con coverage
pytest --cov=src --cov-report=html
```

## 📦 Build (Crear Ejecutables)

```bash
# Crear ejecutables con PyInstaller
build.bat
```

Genera archivos .exe en `dist/` para distribución.

## ❓ Ayuda y Soporte

- **Problemas de uso**: Ver [USER_GUIDE.md](USER_GUIDE.md)
- **Problemas técnicos**: Ver [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - Sección Troubleshooting
- **Issues**: Reportar en el repositorio

## 📝 Changelog

### v2.0 - Aplicación Unificada (Enero 2026)
- ✨ Nueva aplicación unificada con navegación integrada
- 🎨 Arquitectura modular mejorada
- ⚙️ Panel de administración y herramientas de testing
- 🖼️ Carga de imágenes para ROC Skincare
- ❌ Gestión de items fallidos
- 📚 Documentación reorganizada

### v1.0 - Versión Inicial
- Aplicaciones independientes por módulo
- Funcionalidad completa de procesamiento OCR
- Dashboard de revisión
- Sistema ROC Skincare multi-trabajador

## 👨‍💻 Autor

Sistema desarrollado para la gestión automatizada de recibos y transacciones bancarias.

## 📄 Licencia

[Especificar licencia]

---

**Documentación organizada:**
- 📖 [USER_GUIDE.md](USER_GUIDE.md) - Guía para usuarios finales  
- 🔧 [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - Guía para desarrolladores
- 📚 [doc/](doc/) - Documentación adicional
