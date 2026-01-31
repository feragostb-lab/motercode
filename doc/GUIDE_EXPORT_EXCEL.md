# Guía de Ingeniería de Prompts y Manipulación Excel con OpenPyXL

**Destinatario:** GPT-5.1-Codex-Mini
**Contexto:** Procesamiento de Reportes de Gastos (Expense Reports)
**Librería Objetivo:** `openpyxl==3.1.3`

## 1. Análisis de Estructura y Detección de Anclas

El archivo de entrada (`ejemplo.xlsx`) no es un dataset plano estándar (CSV-like), sino un formulario diseñado para lectura humana.

* **El Desafío:** Los datos reales no comienzan en la fila 1. Las primeras 6-8 filas contienen metadatos (Nombre, Rango de fechas) y celdas combinadas.
* **La Solución (Algoritmo de Anclaje):** No asumas `min_row=1`. Debes iterar las primeras 10-15 filas buscando una "Fila Ancla".
* *Patrón de Ancla:* Busca la fila que contenga cadenas específicas como `"id"`, `"Date /Fecha"` o `"GL Account"`.
* *Código Sugerido:*
```python
header_row_idx = None
for row in ws.iter_rows(min_row=1, max_row=15):
    # Buscar la celda que contiene 'Date /Fecha' para definir el inicio de la tabla
    cell_values = [c.value for c in row]
    if "Date /Fecha" in cell_values:
        header_row_idx = row[0].row
        break

```





## 2. Inferencia de Datos y Mapeo (Hoja "Drop Down")

Se detectó una hoja auxiliar llamada `drop down options`. El modelo no debe ignorarla, ya que contiene la lógica de negocio para completar columnas faltantes en la tabla principal.

* **Relación detectada:**
* En `ejemplo.xlsx`, el usuario selecciona un "Tipo" (ej. *Estacionamiento*).
* Automáticamente, esto debe poblar "Expense" (traducción al inglés: *Parking*) y "GL Account" (ej. *724000*).


* **Instrucción para el Modelo:**
1. Cargar `drop down options` en un diccionario de mapeo.
2. Clave: Columna "tipo" (Español).
3. Valor: Tupla de ("Expense", "GL Account").
4. Al procesar la hoja principal, si `GL Account` está vacío pero `Tipo` tiene valor, usar el diccionario para rellenar los datos.



## 3. Manejo de Celdas y Tipos de Datos con OpenPyXL

Al leer `ejemplo.xlsx` para generar `resultado.xlsx`, existen riesgos específicos de formato:

* **`data_only=True`:** Es imperativo cargar el libro con `load_workbook(filename, data_only=True)`.
* *Razón:* Es muy probable que columnas como "Importe" o "Total" contengan fórmulas de Excel (`=SUM(...)`). Si no usas `data_only=True`, `openpyxl` leerá la fórmula como string en lugar del valor numérico calculado.


* **Fechas:** Excel devuelve objetos `datetime.datetime`.
* Al escribir en el `resultado.xlsx`, asegúrate de aplicar el formato de fecha correcto (`cell.number_format = 'DD-MM-YYYY'`) para mantener la consistencia con el snippet `18-12-2025`.


* **Limpieza de None:** Las filas vacías al final del reporte visual son comunes.
* *Regla:* Si la columna `Date /Fecha` o `Amount` es `None`, descarta la fila completa. No proceses filas basándote solo en que tengan formato (bordes/colores) sin contenido.



## 4. Estrategia de Extracción de Metadatos

El archivo `resultado.xlsx` parece ser una versión "aplanada". Sin embargo, si se requiere extraer información del encabezado (Filas 1-6 de `ejemplo.xlsx`):

* **Celdas Combinadas (`merged_cells`):**
* La información como "Nombre" o "Rango de Fechas" suele estar en celdas combinadas.
* *Advertencia:* En `openpyxl`, solo la celda superior izquierda del rango combinado contiene el valor (las demás son `None`).
* *Acceso seguro:* Si visualmente el dato está en `C3` pero es un merge de `C3:E3`, debes leer explícitamente `ws['C3'].value`.



## 5. Generación del Resultado (Output)

Para replicar `resultado.xlsx`:

1. Crear un nuevo `Workbook`.
2. Escribir una **cabecera limpia** en la fila 1 (sin metadatos superiores).
3. Copiar los datos validados fila por fila.
4. **Sanitización de Strings:** Los snippets muestran espacios extra (ej. `"UBER   *TRIP"`). Se recomienda aplicar `.strip()` a las descripciones y nombres de proveedores para normalizar la salida, a menos que se requiera fidelidad exacta.

## Resumen del Flujo de Código Recomendado

```python
import openpyxl

def procesar_gastos(input_path, output_path):
    # 1. Carga con data_only para obtener valores de fórmulas
    wb = openpyxl.load_workbook(input_path, data_only=True)
    
    # 2. Leer mapeos de la hoja de opciones si existe lógica de completado
    # (Pseudocódigo: crear dict map_categorias desde sheet 'drop down options')
    
    ws_report = wb['Expense Report'] # O la hoja activa
    
    # 3. Detectar encabezado dinámicamente
    start_row = detect_header_row(ws_report) # Función auxiliar descrita en punto 1
    
    # 4. Iterar y filtrar
    data_rows = []
    for row in ws_report.iter_rows(min_row=start_row + 1, values_only=True):
        # row[1] es Date, row[6] es Amount (ajustar índices según archivo real)
        if row[1] is None and row[6] is None: 
            continue # Saltar filas vacías
            
        # Aplicar lógica de negocio (mapeo de cuentas, limpieza)
        processed_row = apply_business_logic(row)
        data_rows.append(processed_row)
        
    # 5. Guardar resultado limpio
    save_clean_excel(data_rows, output_path)

