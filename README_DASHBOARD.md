# Dashboard de Procesamiento de Documentos

## 📊 Descripción

Aplicación web interactiva desarrollada con Streamlit para visualizar y gestionar los resultados del procesamiento de documentos (recibos, tickets, facturas) y realizar conciliación bancaria automática.

## 🚀 Características Principales

### 1. Visualización de Fichas
- Navegación intuitiva entre todas las fichas procesadas
- Visualización de la imagen del documento original
- Información detallada de cada documento extraído

### 2. Conciliación Bancaria Automática
- **Coincidencia por Importe**: Busca movimientos bancarios con el mismo importe (tolerancia ±0.01€)
- **Coincidencia por Fecha**: Busca movimientos bancarios en la misma fecha
- **Coincidencia Completa**: Identifica movimientos que coinciden en fecha e importe
- **Asignación Única**: Cada movimiento bancario solo puede asignarse a un recibo

### 3. Sistema de Checks Visuales
- ✅ Check verde: Coincidencia encontrada
- ❌ Check rojo: Sin coincidencia
- ⚠️ Advertencia: Información importante

### 4. Navegación
- **Botones de navegación**: Primera, Anterior, Siguiente, Última
- **Slider**: Ir directamente a cualquier ficha
- **Filtros**:
  - Por tipo de documento (taxis, hoteles, comidas, estacionamiento, etc.)
  - Por estado de coincidencia (completa, parcial, sin coincidencia)

### 5. Estadísticas en Tiempo Real
- Total de fichas procesadas
- Fichas con coincidencia completa
- Fichas con coincidencia parcial (solo importe o solo fecha)
- Fichas sin coincidencias
- Distribución por tipo de documento

### 6. Configuración Integrada
- **Edición de configuración desde la interfaz web**
- Rutas de archivos (Excel bancario, directorios)
- Parámetros de coincidencia bancaria (tolerancia, fechas)
- Gestión de tipos de recibos
- Configuración de backups
- Vista del archivo YAML completo

## 📋 Requisitos

```bash
pip install streamlit pandas openpyxl pillow
```

## 🔧 Instalación y Uso

1. Instalar dependencias:
```bash
pip install streamlit pandas openpyxl pillow
```

2. Ejecutar la aplicación:
```bash
streamlit run app_dashboard.py
```

3. Abrir en el navegador:
```
http://localhost:8501
```

## 📁 Estructura de Datos

### Archivo de Resultados
- **Ubicación**: `result/historial_procesamiento.json`
- **Contenido**: Información de todos los documentos procesados

### Movimientos Bancarios
- **Ubicación**: `img/bankmov/Detalle de Tarjeta.xlsx`
- **Formato**: Excel con columnas: FECHA, DESCRIPCIÓN, MÉTODO, IMPORTE

### Imágenes de Resultados
- **Ubicación**: `result/`
- **Formato**: JPEG con nomenclatura: `YYMMDD_IMPORTE_TIPO.jpeg`

## 🎨 Interfaz

### Navegación Principal
El dashboard incluye 5 páginas accesibles desde el menú lateral:

1. **Receipts** - Visualización y gestión de recibos
2. **Bank Transactions** - Gestión de transacciones bancarias
3. **Statistics** - Estadísticas y reportes
4. **Export** - Exportación de datos
5. **⚙️ Settings** - Configuración de la aplicación

### Panel Izquierdo (Navegación y Filtros)
- Botones de navegación
- Slider de posición
- Filtros por tipo y coincidencia
- Estadísticas del sistema

### Panel Derecho (Visualización)
- Imagen del documento
- Información detallada con formato HTML
- Indicadores de coincidencia bancaria
- Datos extraídos del documento

## 🔍 Sistema de Coincidencias

### Algoritmo de Coincidencia
1. **Normalización de Datos**:
   - Fechas: Convierte diferentes formatos a datetime
   - Importes: Normaliza a float positivo

2. **Búsqueda de Coincidencias**:
   - Compara cada recibo con todos los movimientos bancarios
   - Verifica coincidencia de importe (tolerancia ±0.01€)
   - Verifica coincidencia de fecha exacta

3. **Priorización**:
   - Prioridad 1: Coincidencia completa (fecha + importe)
   - Prioridad 2: Solo importe
   - Prioridad 3: Solo fecha

4. **Asignación**:
   - Un movimiento bancario solo puede asignarse a un recibo
   - Los movimientos asignados no están disponibles para otros recibos

### Indicadores Visuales por Ficha
- **Fondo Verde**: Coincidencia completa (fecha + importe)
- **Fondo Amarillo**: Coincidencia parcial (solo fecha o solo importe)
- **Fondo Rojo**: Sin coincidencia

## 📊 Tipos de Documentos Soportados
- Taxis
- Hoteles
- Comidas/Restaurantes
- Estacionamiento/Parking
- Vuelos
- Alquiler de vehículos
- Peajes
- Otros

## 🔄 Flujo de Trabajo

1. Los documentos se procesan y se guardan en `result/historial_procesamiento.json`
2. Al iniciar el dashboard, se cargan automáticamente:
   - Todas las fichas de documentos
   - Los movimientos bancarios del Excel
3. Se calculan las coincidencias para todas las fichas
4. El usuario navega por las fichas y visualiza:
   - La imagen del documento
   - Los datos extraídos
   - Las coincidencias con movimientos bancarios
5. Los filtros permiten encontrar rápidamente:
   - Documentos sin coincidencia (requieren revisión)
   - Documentos con coincidencia completa (validados)
   - Documentos por tipo específico

## ⚙️ Configuración

### Editar Configuración desde la Interfaz
La página **Settings** permite modificar la configuración sin editar archivos manualmente:

#### 📁 Paths (Rutas)
- Ruta del archivo Excel de transacciones bancarias
- Directorio de imágenes de entrada
- Directorio de resultados procesados
- Directorio de exportaciones

#### 🏦 Bank Matching (Coincidencia Bancaria)
- **Amount Tolerance**: Tolerancia de coincidencia de importes (€)
- **Exact Date Match**: Requerir coincidencia exacta de fecha o permitir ±1 día

#### 📝 Receipt Types (Tipos de Recibos)
- Gestión de categorías de documentos
- Añadir/eliminar tipos personalizados
- Editor de texto multi-línea

#### 💾 Backup (Respaldos)
- Activar/desactivar backups automáticos
- Días de retención de backups
- Backup automático al iniciar procesador

### Guardar Cambios
Cada sección tiene su propio botón **💾 Save** que:
1. Actualiza la configuración en memoria
2. Guarda los cambios en `config.yaml`
3. Recarga la aplicación automáticamente

### Configuración Manual
También puedes editar `config.yaml` directamente. Los cambios se aplicarán al reiniciar la aplicación.

## 🛠️ Mantenimiento

### Actualizar Movimientos Bancarios
Reemplazar el archivo Excel en `img/bankmov/` y reiniciar la aplicación.

### Agregar Nuevos Documentos
Los nuevos documentos procesados se cargarán automáticamente al reiniciar la aplicación.

## 📝 Notas Técnicas

- La aplicación usa caching para las coincidencias (mejor rendimiento)
- Las fechas soportan múltiples formatos automáticamente
- Los importes se normalizan eliminando símbolos y usando punto decimal
- La tolerancia de 0.01€ en importes evita problemas de redondeo

## 🎯 Próximas Mejoras Sugeridas

- Marcar manualmente coincidencias
- Deshacer asignaciones automáticas
- Agregar notas a cada ficha
- Filtro por rango de fechas
- Búsqueda por texto en descripción
- Auditoría de cambios en configuración
