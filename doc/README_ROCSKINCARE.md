# ROC Skincare - Sistema de Gestión de Recibos Multi-Trabajador

> Distribución personalizada para gestión de recibos con múltiples trabajadores y periodos mensuales

## 🎯 Características Principales

### Multi-Trabajador
- ✅ Gestión de múltiples trabajadores (empleados, departamentos, etc.)
- ✅ Nombres alfanuméricos únicos
- ✅ Activación/desactivación de trabajadores
- ✅ Estructura de directorios automática por trabajador

### Gestión de Periodos
- ✅ Periodos mensuales por trabajador (formato MMYYYY: 022025 = Febrero 2025)
- ✅ Solo un periodo puede estar activo para procesamiento a la vez
- ✅ Estados: ACTIVE / CLOSED
- ✅ Estadísticas detalladas por periodo

### Carga Incremental de CSV
- ✅ Múltiples cargas de CSV durante el mes
- ✅ Cada carga reemplaza los datos previos del periodo
- ✅ Archivos timestamped: `banco_{YYYYMMDD_HHMMSS}.csv`
- ✅ Re-matching automático tras cada carga
- ✅ Soporte para formato español de fechas (dd/mm/yyyy)

### Cierre de Periodos
- ✅ Validaciones estrictas antes de cerrar
- ✅ Generación automática de ZIP con:
  - Todos los recibos procesados
  - CSV bancario
  - Excel resumen multi-hoja en español
- ✅ Exportación temporal disponible en cualquier momento
- ✅ Reapertura de periodos con registro de razón

### Procesamiento OCR Inteligente
- ✅ Detección automática del periodo activo
- ✅ Guardado automático en directorio del periodo
- ✅ Enlace automático de recibos con trabajador y periodo
- ✅ Fallback a modo legacy si no hay periodo activo

---

## 📂 Estructura de Directorios

```
./workers/
    juan/                    # Trabajador
        022025/              # Periodo Febrero 2025
            img/             # Imágenes originales (entrada)
            result/          # Recibos procesados (salida OCR)
            csv/             # CSVs bancarios cargados
                banco_20250214_143022.csv
                banco_20250228_095511.csv
            closure_20250228_180000.zip  # Cierre del periodo
        032025/              # Periodo Marzo 2025
            img/
            result/
            csv/
    maria/
        022025/
            ...
```

---

## 🚀 Instalación y Uso

### Requisitos
- Python 3.9+
- GPU con CUDA (recomendado) o CPU
- Modelo VLM: Qwen2.5-VL-7B-Instruct

### Instalación

1. **Clonar repositorio:**
   ```bash
   git clone <repo-url>
   cd ocr-receipt-processor
   ```

2. **Crear entorno virtual:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Descargar modelos:**
   - Colocar modelos en `./models/`:
     - `Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf`
     - `mmproj-Qwen2.5-VL-7B-Instruct-f16.gguf`

5. **Configurar:**
   ```bash
   python scripts/setup_config.py
   ```

### Ejecución

**Dashboard Multi-Trabajador (ROC Skincare):**
```bash
streamlit run app_rocskincare.py
```

Abrir navegador en: http://localhost:8501

---

## 📖 Guía de Uso

### 1. Crear Trabajador

1. Ir a **👥 Trabajadores**
2. Expandir "➕ Crear Nuevo Trabajador"
3. Ingresar nombre alfanumérico (ej: `juan`, `maria01`)
4. Click "Crear Trabajador"

✅ Se crea automáticamente el directorio `./workers/juan/`

### 2. Crear Periodo

1. Ir a **📅 Periodos**
2. Expandir "➕ Crear Nuevo Periodo"
3. Seleccionar trabajador
4. Seleccionar mes y año
5. Click "Crear Periodo"

✅ Se crean directorios: `./workers/juan/022025/img|result|csv/`

### 3. Activar Periodo para Procesamiento

1. En **📅 Periodos**, localizar el periodo deseado
2. Click botón "▶️ Activar"

✅ Este periodo recibe todos los recibos procesados por OCR

### 4. Subir Imágenes

**Opción A: Copiar manualmente**
- Colocar imágenes en: `./workers/juan/022025/img/`
- El procesador las detecta automáticamente

**Opción B: Usar cola global (modo legacy)**
- Procesador detecta periodo activo y guarda en directorio correcto

### 5. Cargar CSV Bancario

1. Ir a **📤 Cargar CSV**
2. Verificar que el periodo activo sea el correcto
3. Seleccionar archivo CSV o Excel
4. Click "🚀 Cargar y Procesar CSV"

✅ Proceso automático:
- Copia CSV a `./workers/juan/022025/csv/banco_{timestamp}.csv`
- Elimina transacciones previas del periodo
- Inserta nuevas transacciones
- Ejecuta re-matching automático

⚡ **Importante**: Puedes cargar CSV múltiples veces durante el mes. Cada carga reemplaza las transacciones previas.

### 6. Revisar Matches

1. Ir a **📊 Visualización**
2. Filtrar por trabajador y periodo
3. Ver tabla de recibos con estado de matching
4. Exportar datos temporalmente si es necesario

### 7. Cerrar Periodo

1. Ir a **🔒 Cierre de Periodos**
2. Seleccionar trabajador y periodo
3. Revisar validaciones:
   - ✅ CSV cargado
   - ✅ Sin recibos pendientes
   - ✅ Sin recibos sin match
   - ✅ Sin conflictos
4. Si todo está verde, click "🔒 Cerrar Periodo Ahora"

✅ Generación automática de ZIP:
```
./workers/juan/022025/closure_20250228_180000.zip
├── result/              # Todos los recibos procesados
├── banco_*.csv          # Último CSV cargado
└── cierre_juan_022025.xlsx  # Excel resumen
```

### 8. Reabrir Periodo (Opcional)

1. En **🔒 Cierre de Periodos**, seleccionar periodo cerrado
2. Ingresar razón para reapertura
3. Click "🔓 Reabrir Periodo"

✅ El ZIP se renombra a: `closure_X_reopened_{timestamp}.zip`

---

## 📊 Formato de Excel de Cierre

El archivo Excel generado contiene 4 hojas:

### 1. Resumen
- Información del trabajador y periodo
- Estado y tipo de exportación
- Contadores totales:
  - Total recibos / Procesados / Pendientes
  - Con match / Sin match / Conflictos
  - Total transacciones / Matched / Sin match
- Fecha de última carga CSV

### 2. Recibos
Columnas:
- ID Recibo
- Fecha Recibo (dd/mm/yyyy)
- Importe Recibo
- Tipo
- Descripción
- Archivo
- Procesado (Sí/No)
- Tipo Match (both/amount_only/date_only/sin_match)
- Confianza (100%/70%/50%/0%)
- Conflicto (Sí/No)
- Fecha Banco (dd/mm/yyyy)
- Importe Banco
- Descripción Banco
- Referencia Banco

### 3. Transacciones Banco
Columnas:
- ID Transacción
- Fecha (dd/mm/yyyy)
- Importe
- Descripción
- Referencia
- Matched (Sí/No)
- ID Recibo Match
- Tipo Match

### 4. Recibos sin Match
- Filtra solo los recibos que no tienen match
- Mismas columnas que hoja "Recibos"

---

## 🔒 Validaciones del Sistema

### Creación de Trabajador
- ❌ Nombres únicos (case-insensitive)
- ❌ Solo caracteres alfanuméricos (sin espacios, símbolos)

### Creación de Periodo
- ❌ Formato MMYYYY obligatorio
- ❌ No duplicados (trabajador, mes-año)
- ❌ Trabajador debe existir

### Activación de Periodo
- ❌ Solo un periodo puede estar `is_processing_active=True` a la vez
- ✅ Al activar uno, los demás se desactivan automáticamente

### Carga de CSV
- ❌ Archivo debe existir
- ❌ Trabajador y periodo deben existir
- ✅ Parseador robusto de fechas españolas (dd/mm/yyyy, dd.mm.yyyy)
- ✅ Validación y conversión de importes
- ✅ Filtrado automático de filas resumen/totales

### Cierre de Periodo
- ❌ **CSV obligatorio**: Debe haberse cargado al menos un CSV
- ❌ **Sin pendientes**: No puede haber recibos sin procesar
- ❌ **Sin sin-match**: Todos los recibos deben tener match
- ❌ **Sin conflictos**: No puede haber conflictos sin resolver

---

## 🗄️ Base de Datos

### Tablas Principales

**workers**
- id, nombre (UNIQUE), activo, created_at

**periods**
- id, worker_id, month_year (MMYYYY), status, is_processing_active, csv_last_upload, csv_file_path
- UNIQUE(worker_id, month_year)
- INDEX: Solo un periodo puede tener `is_processing_active=1`

**receipts**
- ... (campos originales)
- worker_id, period_id (nuevos)

**bank_transactions**
- ... (campos originales)
- worker_id, period_id, csv_upload_date, csv_file_path (nuevos)

**period_closures**
- id, period_id, closure_date, export_path, reopened_at, reopen_reason

**matches**
- ... (sin cambios)

---

## 🛠️ Troubleshooting

### No aparece el periodo activo en "Cargar CSV"
**Solución**: Ve a **📅 Periodos** y activa el periodo deseado con el botón "▶️ Activar"

### Error "Trabajador ya existe"
**Solución**: Los nombres son case-insensitive. "Juan" y "juan" son considerados duplicados.

### Error al cerrar periodo: "CSV no cargado"
**Solución**: Debes cargar al menos un CSV antes de cerrar. Ve a **📤 Cargar CSV**.

### Error al cerrar periodo: "Recibos sin match"
**Solución**: Revisa en **📊 Visualización** qué recibos no tienen match. Puede que necesites ajustar las fechas o importes.

### El OCR no guarda en el directorio del periodo
**Solución**: Verifica que hay un periodo activo (is_processing_active=True) en **📅 Periodos**.

---

## 📝 Diferencias con Versión Legacy

| Característica | Legacy | ROC Skincare |
|----------------|--------|--------------|
| Trabajadores | ❌ No soportado | ✅ Múltiples trabajadores |
| Periodos | ❌ No soportado | ✅ Periodos mensuales por trabajador |
| Directorios | `./img`, `./result` global | `./workers/{nombre}/{MMYYYY}/` |
| CSV | Una sola carga | ✅ Cargas incrementales con timestamp |
| Cierre | ❌ No soportado | ✅ Validación + ZIP automático |
| Reapertura | ❌ No soportado | ✅ Con registro de razón |
| Formato fechas | Variable | ✅ Español (dd/mm/yyyy) |
| Excel | Columnas inglés | ✅ Columnas español |

---

## 🔜 Roadmap

- [ ] Tests de integración
- [ ] API REST para integración con otros sistemas
- [ ] Dashboard de administración con roles
- [ ] Notificaciones automáticas de cierre
- [ ] Reportes históricos multi-periodo
- [ ] Integración con sistemas contables

---

## 📞 Soporte

Para reportar issues o solicitar features:
- GitHub Issues: <repo-url>/issues
- Email: soporte@example.com

---

## 📄 Licencia

[Especificar licencia]

---

**Versión**: 1.0.0  
**Última actualización**: Enero 2026  
**Cliente**: ROC Skincare
