"""Verificar merged cells y formato de la plantilla."""
import openpyxl
from pathlib import Path

template_path = Path("doc/examples/resultado.xlsx")

if template_path.exists():
    wb = openpyxl.load_workbook(template_path)
    ws = wb.active
    
    print("=" * 70)
    print("ANÁLISIS DE PLANTILLA resultado.xlsx")
    print("=" * 70)
    
    # Verificar merged cells
    print("\n📊 Celdas combinadas (Merged Cells):")
    if ws.merged_cells:
        for merged_range in ws.merged_cells.ranges:
            print(f"   {merged_range}")
            # Verificar si F3 está en algún rango combinado
            if merged_range.min_row <= 3 <= merged_range.max_row:
                if merged_range.min_col <= 6 <= merged_range.max_col:
                    print(f"   ⚠️  F3 está dentro de este rango combinado!")
    else:
        print("   No hay celdas combinadas")
    
    # Verificar contenido original de F3
    print("\n🔍 Celda F3 en la plantilla:")
    f3_value = ws.cell(row=3, column=6).value
    print(f"   Valor: '{f3_value}'")
    
    # Verificar fila 3 completa
    print("\n📋 Fila 3 completa en plantilla:")
    for col in range(1, 15):
        val = ws.cell(row=3, column=col).value
        col_letter = openpyxl.utils.get_column_letter(col)
        if val:
            print(f"   {col_letter}3: '{val}'")
    
    # Verificar si E3 está combinada con F3
    print("\n🔍 Verificando E3:")
    e3_value = ws.cell(row=3, column=5).value
    print(f"   Valor E3: '{e3_value}'")
    
    wb.close()
    print("\n" + "=" * 70)
else:
    print(f"❌ Plantilla no encontrada: {template_path}")
