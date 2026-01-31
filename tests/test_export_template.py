"""Script de prueba para verificar la exportación con plantilla."""
from pathlib import Path
from src.services.export_service import ExportService
from src.core.config import Config

def test_export_with_template():
    """Prueba la exportación usando la plantilla resultado.xlsx."""
    print("Iniciando prueba de exportación con plantilla...")
    
    # Cargar configuración
    config = Config()
    
    # Crear servicio de exportación
    export_service = ExportService(config)
    
    # Datos de prueba (simulando datos generados)
    test_data = [
        {
            'id': 1,
            'Date / Fecha': '15-01-2026',
            'Tipo': 'Gasolina',
            'Expense': 'Fuel',
            'GL Account': '6290',
            'Description / Descripcion': 'Repostaje vehículo',
            'Amount (local currency) / Importe (moneda local)': 45.50,
            'Local currency / Moneda local': 'EUR',
            'Payment type / Tipo de pago': 'Corporate Card',
            'Company': 'Roc',
            'Comments / Notas': 'Gasolina estación BP',
            'Img. Filename / Nombre imagen': 'receipt_001.jpg'
        },
        {
            'id': 2,
            'Date / Fecha': '16-01-2026',
            'Tipo': 'Comida',
            'Expense': 'Meals',
            'GL Account': '6280',
            'Description / Descripcion': 'Almuerzo cliente',
            'Amount (local currency) / Importe (moneda local)': 67.80,
            'Local currency / Moneda local': 'EUR',
            'Payment type / Tipo de pago': 'Corporate Card',
            'Company': 'Roc',
            'Comments / Notas': 'Restaurante La Máquina',
            'Img. Filename / Nombre imagen': 'receipt_002.jpg'
        },
        {
            'id': 3,
            'Date / Fecha': '17-01-2026',
            'Tipo': 'Taxi',
            'Expense': 'Transportation',
            'GL Account': '6270',
            'Description / Descripcion': 'Taxi al aeropuerto',
            'Amount (local currency) / Importe (moneda local)': 32.00,
            'Local currency / Moneda local': 'EUR',
            'Payment type / Tipo de pago': 'Corporate Card',
            'Company': 'Roc',
            'Comments / Notas': 'Taxi Uber',
            'Img. Filename / Nombre imagen': 'receipt_003.jpg'
        }
    ]
    
    # Exportar usando el método interno
    output_path = Path("doc/examples/test_export_resultado.xlsx")
    
    # Datos de prueba del trabajador y periodo
    worker_name = "Juan Pérez"
    period_month_year = "12-2025"  # Diciembre 2025
    
    try:
        export_service._export_to_excel_openpyxl(test_data, output_path, worker_name=worker_name, period_month_year=period_month_year)
        print(f"\n✅ Exportación exitosa!")
        print(f"📁 Archivo generado: {output_path}")
        print(f"📊 Registros exportados: {len(test_data)}")
        print(f"👤 Trabajador: {worker_name}")
        print(f"📅 Periodo: {period_month_year}")
        print("\nAhora puedes abrir el archivo y verificar que:")
        print("  - Se copió correctamente la plantilla")
        print("  - Los datos están en las filas 8-10")
        print("  - El formato condicional se ajustó")
        print("  - Hay una fórmula de suma en la fila 11")
        print("  - Las filas vacías fueron eliminadas")
        print("  - Celda F3 contiene el nombre del trabajador")
        print("  - Celda E4 contiene el rango de fechas")
        print("  - Celda I3 contiene 'Corporate Card - December 2025'")
        
    except Exception as e:
        print(f"\n❌ Error durante la exportación: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_export_with_template()
