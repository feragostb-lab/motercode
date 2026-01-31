import openpyxl
from pathlib import Path
import shutil
import traceback
from openpyxl.formatting.formatting import ConditionalFormattingList
from openpyxl.worksheet.cell_range import MultiCellRange

def detectar_ultima_fila_con_datos(worksheet, columna):
    for row in range(worksheet.max_row, 0, -1):
        cell_value = worksheet.cell(row=row, column=columna).value
        if cell_value is not None and str(cell_value).strip() != "":
            return row
    return None

def limpiar_estilos_celdas(ws, fila_inicio, fila_fin, col_inicio, col_fin):
    default_font = openpyxl.styles.Font()
    default_border = openpyxl.styles.Border()
    default_fill = openpyxl.styles.PatternFill(fill_type=None)
    default_alignment = openpyxl.styles.Alignment()

    for row in range(fila_inicio, fila_fin + 1):
        for col in range(col_inicio, col_fin + 1):
            cell = ws.cell(row=row, column=col)
            cell.font = default_font
            cell.border = default_border
            cell.fill = default_fill
            cell.alignment = default_alignment

def redimensionar_formato_condicional_tecnico(ws, fila_limite):
    """
    Reconstruye el formato condicional extrayendo (Key, Value) del OrderedDict interno.
    Key: Objeto ConditionalFormatting (contiene sqref).
    Value: Lista de objetos Rule.
    """
    print(f"  -> Reajustando reglas de formato condicional hasta la fila {fila_limite}...")
    
    # 1. Extracción Segura de Datos
    # Accedemos a _cf_rules solo para LEER. Convertimos a lista para congelar el estado.
    # Cada item es una tupla: (ConditionalFormattingObject, [Rule1, Rule2, ...])
    if not hasattr(ws.conditional_formatting, '_cf_rules'):
        print("  Advertencia: No se encontraron reglas o estructura incompatible.")
        return

    datos_reglas = list(ws.conditional_formatting._cf_rules.items())
    
    # 2. Reinicio Total
    # Creamos una lista limpia. Esto elimina cualquier corrupción anterior.
    ws.conditional_formatting = ConditionalFormattingList()
    
    contador_reglas = 0
    
    # 3. Procesamiento y Re-inserción
    for cf_container, lista_reglas in datos_reglas:
        # cf_container.sqref es un MultiCellRange (ej: "A1:A10 B1:B10")
        ranges_a_mantener = []
        
        # Iteramos sobre los rangos individuales dentro del MultiCellRange
        # (sqref es iterable, devuelve objetos CellRange)
        for rango in cf_container.sqref:
            
            # Caso A: Rango totalmente fuera del límite -> Se descarta
            if rango.min_row > fila_limite:
                continue
            
            # Caso B: Rango cruza el límite -> Se recorta
            if rango.max_row > fila_limite:
                # Modificamos el límite superior
                rango.max_row = fila_limite
            
            ranges_a_mantener.append(rango)
        
        # Si nos queda algún rango válido después del recorte
        if ranges_a_mantener:
            # Convertimos la lista de rangos a un string legible por Excel (ej: "A1:A50 B1:B50")
            # Usamos str() sobre un nuevo MultiCellRange para formatearlo correctamente
            nuevo_sqref = MultiCellRange(ranges_a_mantener)
            nuevo_sqref_str = str(nuevo_sqref)
            
            # Re-insertamos CADA REGLA asociada a este rango
            for regla in lista_reglas:
                # Usamos .add() que es seguro porque:
                # 1. Pasamos un string como rango (lo que espera)
                # 2. Pasamos un objeto 'Rule' válido (que extrajimos de la lista de valores)
                ws.conditional_formatting.add(nuevo_sqref_str, regla)
                contador_reglas += 1

    print(f"  -> Proceso técnico completado. Se migraron {contador_reglas} reglas.")

def main():
    base_path = Path("doc/examples")
    archivo_origen = base_path / "resultado.xlsx"
    archivo_export = base_path / "export.xlsx"
    archivo_destino = base_path / "resultado_copia.xlsx"
    
    if not archivo_origen.exists():
        print(f"Error: No existe {archivo_origen}")
        return

    print("Iniciando proceso...")
    shutil.copy2(archivo_origen, archivo_destino)
    
    wb_destino = None
    wb_export = None

    try:
        wb_destino = openpyxl.load_workbook(archivo_destino)
        ws_destino = wb_destino.active
        
        # 1. Limpieza Datos
        for row in range(8, 1001):
            for col in range(3, 15):
                ws_destino.cell(row=row, column=col).value = None
        
        # 2. Copia
        wb_export = openpyxl.load_workbook(archivo_export, data_only=True)
        ws_export = wb_export.active
        max_row_export = detectar_ultima_fila_con_datos(ws_export, 3) or 2
        
        fila_destino = 8
        for fila_origen in range(2, max_row_export + 1):
            for col in range(3, 15):
                val = ws_export.cell(row=fila_origen, column=col).value
                ws_destino.cell(row=fila_destino, column=col).value = val
            fila_destino += 1
            
        wb_export.close()
        wb_export = None
        
        # 3. Ajuste Final
        ultima_fila = detectar_ultima_fila_con_datos(ws_destino, columna=3)
        
        if ultima_fila:
            fila_formula = ultima_fila + 1
           
                        # --- LLAMADA A LA FUNCIÓN CORREGIDA ---
            redimensionar_formato_condicional_tecnico(ws_destino, ultima_fila)
            
            if ultima_fila < 1000:
                limpiar_estilos_celdas(ws_destino, ultima_fila + 1, 1000, 1, 20)
                ws_destino.delete_rows(ultima_fila + 1, 1000 - ultima_fila)
            ws_destino.cell(row=ultima_fila+1, column=9).value = f"=SUM(I8:I{ultima_fila})"    

        wb_destino.save(archivo_destino)
        print("¡Éxito!")

    except Exception:
        traceback.print_exc()
    finally:
        if wb_destino: wb_destino.close()
        if wb_export: wb_export.close()

if __name__ == "__main__":
    main()