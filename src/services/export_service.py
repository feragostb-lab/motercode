"""Export service - Export data to Excel/CSV."""
import logging
from pathlib import Path
from typing import Optional
import pandas as pd
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.formatting import ConditionalFormattingList
from openpyxl.worksheet.cell_range import MultiCellRange
import shutil

from ..repositories.receipt_repository import ReceiptRepository
from ..repositories.bank_repository import BankRepository
from ..repositories.match_repository import MatchRepository
from ..core.database import get_database

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting data."""
    
    def __init__(self, config):
        """
        Initialize export service.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.db = get_database(config.paths.get('database', './receipts.db'))
        self.receipt_repo = ReceiptRepository(self.db)
        self.bank_repo = BankRepository(self.db)
        self.match_repo = MatchRepository(self.db)
        self.export_dir = Path(config.paths.get('exports_dir', './exports'))
        
        # Ensure export directory exists
        self.export_dir.mkdir(parents=True, exist_ok=True)
    
    def export_receipts_with_matches_to_excel(self, filename: Optional[str] = None) -> str:
        """
        Export receipts with their bank matches to Excel.
        
        Args:
            filename: Optional filename (auto-generated if None)
            
        Returns:
            Path to exported file
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"receipts_export_{timestamp}.xlsx"
        
        output_path = self.export_dir / filename
        
        # Get all data
        receipts = self.receipt_repo.get_all()
        
        # Build export data
        export_data = []
        for receipt in receipts:
            # Get match info
            match = self.match_repo.get_by_receipt_id(receipt.id)
            
            # Get bank transaction if matched
            bank_trans = None
            if match and match.transaction_id:
                bank_trans = self.bank_repo.get_by_id(match.transaction_id)
            
            row = {
                'Receipt ID': receipt.id,
                'Receipt Date': receipt.date.strftime('%d-%m-%Y') if receipt.date else '',
                'Receipt Amount': float(receipt.amount) if receipt.amount else 0.0,
                'Receipt Type': receipt.receipt_type or '',
                'Receipt Description': receipt.description or '',
                'File Path': receipt.file_path,
                'Processing Success': receipt.processing_successful,
                'Match Type': match.match_type.value if match else 'none',
                'Match Confidence': float(match.confidence) if match else 0.0,
                'Is Conflict': match.is_conflict if match else False,
                'Conflict Accepted': match.conflict_accepted if match else False,
                'Bank Date': bank_trans.date.strftime('%d-%m-%Y') if bank_trans and bank_trans.date else '',
                'Bank Amount': float(bank_trans.amount) if bank_trans and bank_trans.amount else 0.0,
                'Bank Description': bank_trans.description if bank_trans else '',
                'Bank Reference': bank_trans.reference if bank_trans else '',
            }
            export_data.append(row)
        
        # Create DataFrame and export
        df = pd.DataFrame(export_data)
        df.to_excel(output_path, index=False, engine='openpyxl')
        
        logger.info(f"Exported {len(export_data)} receipts to {output_path}")
        return str(output_path)
    
    def export_receipts_with_matches_to_csv(self, filename: Optional[str] = None) -> str:
        """
        Export receipts with their bank matches to CSV.
        
        Args:
            filename: Optional filename (auto-generated if None)
            
        Returns:
            Path to exported file
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"receipts_export_{timestamp}.csv"
        
        output_path = self.export_dir / filename
        
        # Get all data (same as Excel export)
        receipts = self.receipt_repo.get_all()
        
        export_data = []
        for receipt in receipts:
            match = self.match_repo.get_by_receipt_id(receipt.id)
            bank_trans = None
            if match and match.transaction_id:
                bank_trans = self.bank_repo.get_by_id(match.transaction_id)
            
            row = {
                'Receipt ID': receipt.id,
                'Receipt Date': receipt.date.strftime('%d-%m-%Y') if receipt.date else '',
                'Receipt Amount': float(receipt.amount) if receipt.amount else 0.0,
                'Receipt Type': receipt.receipt_type or '',
                'Receipt Description': receipt.description or '',
                'File Path': receipt.file_path,
                'Processing Success': receipt.processing_successful,
                'Match Type': match.match_type.value if match else 'none',
                'Match Confidence': float(match.confidence) if match else 0.0,
                'Is Conflict': match.is_conflict if match else False,
                'Bank Date': bank_trans.date.strftime('%d-%m-%Y') if bank_trans and bank_trans.date else '',
                'Bank Amount': float(bank_trans.amount) if bank_trans and bank_trans.amount else 0.0,
                'Bank Description': bank_trans.description if bank_trans else '',
            }
            export_data.append(row)
        
        df = pd.DataFrame(export_data)
        df.to_csv(output_path, index=False, encoding='utf-8')
        
        logger.info(f"Exported {len(export_data)} receipts to {output_path}")
        return str(output_path)
    
    def export_unmatched_transactions(self, format: str = 'excel') -> str:
        """
        Export only unmatched bank transactions.
        
        Args:
            format: 'excel' or 'csv'
            
        Returns:
            Path to exported file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = 'xlsx' if format == 'excel' else 'csv'
        filename = f"unmatched_transactions_{timestamp}.{ext}"
        output_path = self.export_dir / filename
        
        # TODO: Implement
        transactions = self.bank_repo.get_unmatched()
        
        # Convert to DataFrame
        df = pd.DataFrame([t.to_dict() for t in transactions])
        
        if format == 'excel':
            df.to_excel(output_path, index=False)
        else:
            df.to_csv(output_path, index=False, encoding='utf-8')
        
        logger.info(f"Exported unmatched transactions to {output_path}")
        return str(output_path)
    
    def export_all_transactions_complete(self, format: str = 'excel') -> str:
        """
        Export all bank transactions with matched receipt information.
        Usa openpyxl para generar un Excel con formato según guía.
        Campos: id, Date/Fecha, Tipo, Expense, GL Account, Description/Descripcion, 
                Amount (local currency)/Importe (moneda local), Local currency/Moneda local,
                Payment type / Tipo de pago, Company, Comments/Notas, Img. Filename/Nombre imagen
        
        Args:
            format: 'excel' or 'csv' (solo excel usa openpyxl)
            
        Returns:
            Path to exported file
        """
        from ..services.config_service import ConfigService
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = 'xlsx' if format == 'excel' else 'csv'
        filename = f"all_transactions_complete_{timestamp}.{ext}"
        output_path = self.export_dir / filename
        
        # Get active worker and period info for Excel export
        worker_name = None
        period_month_year = None
        try:
            from ..repositories.period_repository import PeriodRepository
            from ..repositories.worker_repository import WorkerRepository
            
            period_repo = PeriodRepository(self.db)
            worker_repo = WorkerRepository(self.db)
            
            # Get the active processing period
            active_period = period_repo.get_active_processing_period()
            
            if active_period:
                worker = worker_repo.get_by_id(active_period.worker_id)
                if worker:
                    worker_name = worker.nombre
                    period_month_year = active_period.month_year
                    logger.info(f"Export will use active worker: {worker_name}, period: {period_month_year}")
        except Exception as e:
            logger.warning(f"Could not get active worker/period info: {e}")
        
        # Get type definitions to retrieve normalized_type and gl_account
        config_service = ConfigService()
        type_definitions = config_service.get_type_definitions()
        
        # Create a map of receipt_type -> (normalized_type, gl_account)
        type_map = {}
        for type_def in type_definitions:
            type_map[type_def.name] = {
                'normalized_type': type_def.normalized_type,
                'gl_account': type_def.gl_account
            }
        
        # Get all bank transactions
        transactions = self.bank_repo.get_all()
        
        export_data = []
        for idx, trans in enumerate(transactions, start=1):
            # Get matched receipt if exists
            matches = self.match_repo.get_by_transaction_id(trans.id)
            receipt = None
            if matches:  # matches is a list
                # Get the first match (or the accepted one if there are conflicts)
                match = matches[0] if len(matches) == 1 else next((m for m in matches if m.conflict_accepted), matches[0])
                receipt = self.receipt_repo.get_by_id(match.receipt_id)
            
            # Extract filename from receipt file_path
            img_filename = ""
            tipo = ""
            expense = ""
            gl_account = ""
            description = ""
            
            if receipt:
                if receipt.file_path:
                    img_filename = Path(receipt.file_path).name
                
                # Get normalized type and GL account from type definition
                receipt_type = receipt.receipt_type or ''
                tipo = receipt_type  # Tipo en castellano (original)
                description = (receipt.description or '').strip()  # Sanitización de strings
                
                if receipt_type in type_map:
                    expense = type_map[receipt_type]['normalized_type'] or ''
                    gl_account = type_map[receipt_type]['gl_account'] or ''
            
            row = {
                'id': idx,  # Número de orden
                'Date / Fecha': trans.date.strftime('%d-%m-%Y') if trans.date else '',
                'Tipo': tipo,  # Tipo en castellano
                'Expense': expense,  # Normalized type
                'GL Account': gl_account,
                'Description / Descripcion': description,
                'Amount (local currency) / Importe (moneda local)': float(trans.amount) if trans.amount else 0.0,
                'Local currency / Moneda local': 'EUR',  # Asumiendo EUR como moneda local
                'Payment type / Tipo de pago': 'Corporate Card',  # Valor por defecto
                'Company': 'Roc',  # Valor por defecto
                'Comments / Notas': (trans.description or '').strip(),  # DESCRIPCIÓN del CSV bancario - sanitizada
                'Img. Filename / Nombre imagen': img_filename,
            }
            export_data.append(row)
        
        # Export based on format
        if format == 'excel':
            # Usar openpyxl según la guía para mejor control del formato
            # Pasar worker_name y period_month_year si están disponibles
            self._export_to_excel_openpyxl(export_data, output_path, worker_name=worker_name, period_month_year=period_month_year)
        else:
            # CSV fallback usando pandas
            df = pd.DataFrame(export_data)
            df.to_csv(output_path, index=False, encoding='utf-8')
        
        logger.info(f"Exported {len(export_data)} complete transactions to {output_path}")
        return str(output_path)
    
    # ===== ROC SKINCARE: Multi-worker period export =====
    
    def export_period_data(
        self, 
        period_id: int, 
        export_type: str = 'temporal',
        output_dir: Optional[Path] = None
    ) -> str:
        """
        Export all data for a specific period using openpyxl format (según guía).
        
        Args:
            period_id: Period ID to export
            export_type: 'temporal' for temporary exports, 'closure' for final period closure
            output_dir: Optional output directory (uses period result dir if None)
            
        Returns:
            Path to exported Excel file
            
        Raises:
            ValueError: If period doesn't exist
        """
        from ..repositories.period_repository import PeriodRepository
        from ..repositories.worker_repository import WorkerRepository
        from ..services.config_service import ConfigService
        from ..utils.file_helpers import get_period_paths
        from ..utils.formatters import format_date_spanish, format_datetime_spanish
        
        # Get period and worker info
        period_repo = PeriodRepository(self.db)
        worker_repo = WorkerRepository(self.db)
        
        period = period_repo.get_by_id(period_id)
        if not period:
            raise ValueError(f"Periodo con ID {period_id} no existe")
        
        worker = worker_repo.get_by_id(period.worker_id)
        if not worker:
            raise ValueError(f"Trabajador con ID {period.worker_id} no existe")
        
        # Determine output directory
        if output_dir is None:
            paths = get_period_paths(worker.nombre, period.month_year)
            output_dir = paths['result']
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if export_type == 'closure':
            filename = f"cierre_{worker.nombre}_{period.month_year}.xlsx"
        else:
            filename = f"export_{worker.nombre}_{period.month_year}_{timestamp}.xlsx"
        
        output_path = output_dir / filename
        
        # Get type definitions for mapping
        config_service = ConfigService()
        type_definitions = config_service.get_type_definitions()
        
        # Create a map of receipt_type -> (normalized_type, gl_account)
        type_map = {}
        for type_def in type_definitions:
            type_map[type_def.name] = {
                'normalized_type': type_def.normalized_type,
                'gl_account': type_def.gl_account
            }
        
        # Get all data for this period
        # Usar transacciones bancarias como base (similar a export_all_transactions_complete)
        transactions = self.bank_repo.get_by_period(period_id)
        
        # Build export data usando el mismo formato que export_all_transactions_complete
        export_data = []
        for idx, trans in enumerate(transactions, start=1):
            # Get matched receipt if exists
            matches = self.match_repo.get_by_transaction_id(trans.id)
            receipt = None
            if matches:
                match = matches[0] if len(matches) == 1 else next((m for m in matches if m.conflict_accepted), matches[0])
                receipt = self.receipt_repo.get_by_id(match.receipt_id)
            
            # Extract data from receipt
            img_filename = ""
            tipo = ""
            expense = ""
            gl_account = ""
            description = ""
            
            if receipt:
                if receipt.file_path:
                    img_filename = Path(receipt.file_path).name
                
                receipt_type = receipt.receipt_type or ''
                tipo = receipt_type
                description = (receipt.description or '').strip()
                
                if receipt_type in type_map:
                    expense = type_map[receipt_type]['normalized_type'] or ''
                    gl_account = type_map[receipt_type]['gl_account'] or ''
            
            row = {
                'id': idx,
                'Date / Fecha': trans.date.strftime('%d-%m-%Y') if trans.date else '',
                'Tipo': tipo,
                'Expense': expense,
                'GL Account': gl_account,
                'Description / Descripcion': description,
                'Amount (local currency) / Importe (moneda local)': float(trans.amount) if trans.amount else 0.0,
                'Local currency / Moneda local': 'EUR',
                'Payment type / Tipo de pago': 'Corporate Card',
                'Company': 'Roc',
                'Comments / Notas': (trans.description or '').strip(),
                'Img. Filename / Nombre imagen': img_filename,
            }
            export_data.append(row)
        
        # Usar openpyxl para exportar con formato correcto
        self._export_to_excel_openpyxl(export_data, output_path, worker_name=worker.nombre, period_month_year=period.month_year)
        
        logger.info(f"Exported period {period_id} data to {output_path} ({export_type})")
        return str(output_path)
    
    def _detectar_ultima_fila_con_datos(self, worksheet, columna):
        """Detecta la última fila con datos en una columna específica."""
        for row in range(worksheet.max_row, 0, -1):
            cell_value = worksheet.cell(row=row, column=columna).value
            if cell_value is not None and str(cell_value).strip() != "":
                return row
        return None
    
    def _limpiar_estilos_celdas(self, ws, fila_inicio, fila_fin, col_inicio, col_fin):
        """Limpia estilos de un rango de celdas."""
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
    
    def _redimensionar_formato_condicional_tecnico(self, ws, fila_limite):
        """
        Reconstruye el formato condicional extrayendo (Key, Value) del OrderedDict interno.
        Key: Objeto ConditionalFormatting (contiene sqref).
        Value: Lista de objetos Rule.
        """
        logger.info(f"Reajustando reglas de formato condicional hasta la fila {fila_limite}...")
        
        # 1. Extracción Segura de Datos
        if not hasattr(ws.conditional_formatting, '_cf_rules'):
            logger.warning("No se encontraron reglas o estructura incompatible.")
            return

        datos_reglas = list(ws.conditional_formatting._cf_rules.items())
        
        # 2. Reinicio Total
        ws.conditional_formatting = ConditionalFormattingList()
        
        contador_reglas = 0
        
        # 3. Procesamiento y Re-inserción
        for cf_container, lista_reglas in datos_reglas:
            ranges_a_mantener = []
            
            for rango in cf_container.sqref:
                # Caso A: Rango totalmente fuera del límite -> Se descarta
                if rango.min_row > fila_limite:
                    continue
                
                # Caso B: Rango cruza el límite -> Se recorta
                if rango.max_row > fila_limite:
                    rango.max_row = fila_limite
                
                ranges_a_mantener.append(rango)
            
            # Si nos queda algún rango válido después del recorte
            if ranges_a_mantener:
                nuevo_sqref = MultiCellRange(ranges_a_mantener)
                nuevo_sqref_str = str(nuevo_sqref)
                
                for regla in lista_reglas:
                    ws.conditional_formatting.add(nuevo_sqref_str, regla)
                    contador_reglas += 1

        logger.info(f"Proceso técnico completado. Se migraron {contador_reglas} reglas.")

    def _export_to_excel_openpyxl(self, data: list, output_path: Path, worker_name: Optional[str] = None, period_month_year: Optional[str] = None) -> None:
        """
        Export data to Excel using template file (resultado.xlsx) with proper formatting.
        Aplica las técnicas aprendidas en excel_test.py:
        1. Carga plantilla resultado.xlsx
        2. Limpia datos antiguos (filas 8+)
        3. Escribe los nuevos datos generados
        4. Ajusta formato condicional al rango real
        5. Limpia estilos de filas vacías
        6. Elimina filas vacías
        7. Agrega fórmula de suma
        8. Escribe información adicional: nombre trabajador, periodo de fechas, payment type con periodo
        
        Args:
            data: List of dictionaries with transaction data
            output_path: Path to save the Excel file
            worker_name: Optional worker name to display in cell F3
            period_month_year: Optional period (e.g., '12-2025') for formatting date range and payment description
        """
        # Rutas de archivos
        template_path = Path("doc/examples/resultado.xlsx")
        
        if not template_path.exists():
            logger.error(f"Plantilla no encontrada: {template_path}")
            raise FileNotFoundError(f"Plantilla no encontrada: {template_path}")
        
        # Copiar plantilla a destino
        shutil.copy2(template_path, output_path)
        logger.info(f"Plantilla copiada a: {output_path}")
        
        wb = None
        try:
            # Cargar el archivo destino (copia de la plantilla)
            wb = openpyxl.load_workbook(output_path)
            ws = wb.active
            
            # 1. Limpieza de datos antiguos (filas 8 a 1000, columnas 3 a 14)
            logger.info("Limpiando datos antiguos...")
            for row in range(8, 1001):
                for col in range(3, 15):
                    ws.cell(row=row, column=col).value = None
            
            # 2. Escribir nuevos datos generados
            logger.info(f"Escribiendo {len(data)} registros...")
            fila_destino = 8  # Primera fila de datos (después de cabecera)
            
            for row_data in data:
                # Mapeo de columnas según la estructura de resultado.xlsx
                # Columna C(3)=id, D(4)=Date, E(5)=Tipo, F(6)=Expense, G(7)=GL Account,
                # H(8)=Description, I(9)=Amount, J(10)=Currency, K(11)=Payment type,
                # L(12)=Company, M(13)=Comments, N(14)=Img Filename
                
                ws.cell(row=fila_destino, column=3).value = row_data.get('id', '')
                ws.cell(row=fila_destino, column=4).value = row_data.get('Date / Fecha', '')
                ws.cell(row=fila_destino, column=5).value = row_data.get('Tipo', '')
                ws.cell(row=fila_destino, column=6).value = row_data.get('Expense', '')
                ws.cell(row=fila_destino, column=7).value = row_data.get('GL Account', '')
                ws.cell(row=fila_destino, column=8).value = row_data.get('Description / Descripcion', '')
                
                # Amount con formato numérico - asegurar que sea float con punto decimal
                amount_val = row_data.get('Amount (local currency) / Importe (moneda local)', 0.0)
                amount_cell = ws.cell(row=fila_destino, column=9)
                amount_cell.value = float(amount_val) if isinstance(amount_val, (int, float)) else 0.0
                # Forzar formato numérico con 2 decimales y punto como separador
                amount_cell.number_format = '0.00'
                
                ws.cell(row=fila_destino, column=10).value = row_data.get('Local currency / Moneda local', 'EUR')
                ws.cell(row=fila_destino, column=11).value = row_data.get('Payment type / Tipo de pago', 'Corporate Card')
                ws.cell(row=fila_destino, column=12).value = row_data.get('Company', 'Roc')
                ws.cell(row=fila_destino, column=13).value = row_data.get('Comments / Notas', '')
                ws.cell(row=fila_destino, column=14).value = row_data.get('Img. Filename / Nombre imagen', '')
                
                fila_destino += 1
            
            # 3. Escribir información adicional en celdas específicas (ANTES de ajustes de formato)
            # F3: Nombre del trabajador
            if worker_name:
                ws.cell(row=3, column=6).value = worker_name  # Columna F
                logger.info(f"Nombre trabajador escrito en F3: {worker_name}")
            
            # 4. Ajuste final: detectar última fila con datos
            ultima_fila = self._detectar_ultima_fila_con_datos(ws, columna=3)
            
            if ultima_fila:
                logger.info(f"Última fila con datos: {ultima_fila}")
                
                # 5. Redimensionar formato condicional
                self._redimensionar_formato_condicional_tecnico(ws, ultima_fila)
                
                # 6. Limpiar estilos de filas vacías y eliminarlas
                if ultima_fila < 1000:
                    self._limpiar_estilos_celdas(ws, ultima_fila + 1, 1000, 1, 20)
                    ws.delete_rows(ultima_fila + 1, 1000 - ultima_fila)
                    logger.info(f"Eliminadas filas vacías desde {ultima_fila + 1}")
                
                # 7. Agregar fórmula de suma en la fila siguiente
                ws.cell(row=ultima_fila + 1, column=9).value = f"=SUM(I8:I{ultima_fila})"
                logger.info(f"Fórmula de suma agregada en fila {ultima_fila + 1}")
            if data:
                # Extraer fechas de los datos
                fechas = []
                for row_data in data:
                    fecha_str = row_data.get('Date / Fecha', '')
                    if fecha_str:
                        try:
                            # Convertir de DD-MM-YYYY a objeto datetime
                            from datetime import datetime
                            fecha_obj = datetime.strptime(fecha_str, '%d-%m-%Y')
                            fechas.append(fecha_obj)
                        except:
                            pass
                
                if fechas:
                    # E4: Rango de fechas en formato DD/MM/YYYY - DD/MM/YYYY
                    fecha_menor = min(fechas)
                    fecha_mayor = max(fechas)
                    rango_fechas = f"{fecha_menor.strftime('%d/%m/%Y')} - {fecha_mayor.strftime('%d/%m/%Y')}"
                    ws.cell(row=4, column=5).value = rango_fechas  # Columna E
                    logger.info(f"Rango de fechas escrito en E4: {rango_fechas}")
                    
                    # I3: "Corporate Card - Month Year" usando el periodo si está disponible
                    if period_month_year:
                        # period_month_year puede venir en formato '12-2025', 'December-2025', o 'MMYYYY' (e.g., '012026')
                        try:
                            month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                                           'July', 'August', 'September', 'October', 'November', 'December']
                            
                            # Intentar parsear como MM-YYYY o Month-YYYY
                            if '-' in period_month_year:
                                parts = period_month_year.split('-')
                                if len(parts) == 2:
                                    month_num = int(parts[0]) if parts[0].isdigit() else None
                                    year = parts[1]
                                    
                                    if month_num:
                                        month_name = month_names[month_num] if 1 <= month_num <= 12 else parts[0]
                                        payment_text = f"Corporate Card - {month_name} {year}"
                                    else:
                                        # Ya viene con el nombre del mes
                                        payment_text = f"Corporate Card - {parts[0]} {year}"
                                else:
                                    payment_text = f"Corporate Card - {period_month_year}"
                            # Intentar parsear como MMYYYY (e.g., '012026')
                            elif len(period_month_year) == 6 and period_month_year.isdigit():
                                month_num = int(period_month_year[:2])
                                year = period_month_year[2:]
                                month_name = month_names[month_num] if 1 <= month_num <= 12 else period_month_year[:2]
                                payment_text = f"Corporate Card - {month_name} {year}"
                            else:
                                payment_text = f"Corporate Card - {period_month_year}"
                        except:
                            payment_text = f"Corporate Card - {period_month_year}"
                    else:
                        # Usar la fecha mayor para extraer mes y año
                        month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                                       'July', 'August', 'September', 'October', 'November', 'December']
                        month_name = month_names[fecha_mayor.month]
                        payment_text = f"Corporate Card - {month_name} {fecha_mayor.year}"
                    
                    ws.cell(row=3, column=9).value = payment_text  # Columna I
                    logger.info(f"Payment type escrito en I3: {payment_text}")
            
            # Guardar el archivo
            wb.save(output_path)
            logger.info(f"Excel exportado exitosamente: {output_path}")
            
        except Exception as e:
            logger.error(f"Error al exportar con plantilla: {e}")
            raise
        finally:
            if wb:
                wb.close()
