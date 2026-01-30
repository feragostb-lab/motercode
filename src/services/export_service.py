"""Export service - Export data to Excel/CSV."""
import logging
from pathlib import Path
from typing import Optional
import pandas as pd
from datetime import datetime

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
        Campos: id, Date/Fecha, Tipo, Expense, GL Account, Description/Descripcion, 
                Amount (local currency)/Importe (moneda local), Local currency/Moneda local,
                Comments/Notas, Img. Filename/Nombre imagen
        
        Args:
            format: 'excel' or 'csv'
            
        Returns:
            Path to exported file
        """
        from ..services.config_service import ConfigService
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = 'xlsx' if format == 'excel' else 'csv'
        filename = f"all_transactions_complete_{timestamp}.{ext}"
        output_path = self.export_dir / filename
        
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
            
            if receipt:
                if receipt.file_path:
                    img_filename = Path(receipt.file_path).name
                
                # Get normalized type and GL account from type definition
                receipt_type = receipt.receipt_type or ''
                tipo = receipt_type  # Tipo en castellano (original)
                
                if receipt_type in type_map:
                    expense = type_map[receipt_type]['normalized_type'] or ''
                    gl_account = type_map[receipt_type]['gl_account'] or ''
            
            row = {
                'id': idx,  # Número de orden
                'Date / Fecha': trans.date.strftime('%d-%m-%Y') if trans.date else '',
                'Tipo': tipo,  # Tipo en castellano
                'Expense': expense,  # Normalized type
                'GL Account': gl_account,
                'Description / Descripcion': receipt.description if receipt else '',
                'Amount (local currency) / Importe (moneda local)': float(trans.amount) if trans.amount else 0.0,
                'Local currency / Moneda local': 'EUR',  # Asumiendo EUR como moneda local
                'Comments / Notas': trans.description or '',  # DESCRIPCIÓN del CSV bancario
                'Img. Filename / Nombre imagen': img_filename,
            }
            export_data.append(row)
        
        # Create DataFrame and export
        df = pd.DataFrame(export_data)
        
        if format == 'excel':
            df.to_excel(output_path, index=False)
        else:
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
        Export all data for a specific period.
        
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
        
        # Get all data for this period
        receipts = self.receipt_repo.get_by_period(period_id)
        transactions = self.bank_repo.get_by_period(period_id)
        
        # Build receipts export data with Spanish formatting
        receipts_data = []
        for receipt in receipts:
            match = self.match_repo.get_by_receipt_id(receipt.id)
            bank_trans = None
            if match and match.transaction_id:
                bank_trans = self.bank_repo.get_by_id(match.transaction_id)
            
            row = {
                'ID Recibo': receipt.id,
                'Fecha Recibo': format_date_spanish(receipt.date) if receipt.date else '',
                'Importe Recibo': float(receipt.amount) if receipt.amount else 0.0,
                'Tipo': receipt.receipt_type or '',
                'Descripción': receipt.description or '',
                'Archivo': receipt.file_path,
                'Procesado': 'Sí' if receipt.processing_successful else 'No',
                'Tipo Match': match.match_type.value if match else 'sin_match',
                'Confianza': f"{float(match.confidence):.0%}" if match else '0%',
                'Conflicto': 'Sí' if (match and match.is_conflict) else 'No',
                'Fecha Banco': format_date_spanish(bank_trans.date) if (bank_trans and bank_trans.date) else '',
                'Importe Banco': float(bank_trans.amount) if (bank_trans and bank_trans.amount) else 0.0,
                'Descripción Banco': bank_trans.description if bank_trans else '',
                'Referencia Banco': bank_trans.reference if bank_trans else '',
            }
            receipts_data.append(row)
        
        # Build transactions export data
        transactions_data = []
        for trans in transactions:
            # Check if this transaction is matched to any receipt
            match = self.match_repo.get_by_transaction_id(trans.id)
            receipt = None
            if match:
                receipt = self.receipt_repo.get_by_id(match.receipt_id)
            
            row = {
                'ID Transacción': trans.id,
                'Fecha': format_date_spanish(trans.date) if trans.date else '',
                'Importe': float(trans.amount) if trans.amount else 0.0,
                'Descripción': trans.description or '',
                'Referencia': trans.reference or '',
                'Matched': 'Sí' if match else 'No',
                'ID Recibo Match': receipt.id if receipt else '',
                'Tipo Match': match.match_type.value if match else '',
            }
            transactions_data.append(row)
        
        # Create Excel file with multiple sheets
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Summary sheet
            summary_stats = period_repo.get_period_stats(period_id)
            summary_data = {
                'Información': [
                    'Trabajador',
                    'Periodo',
                    'Estado',
                    'Tipo Exportación',
                    'Fecha Exportación',
                    '',
                    'Total Recibos',
                    'Recibos Procesados',
                    'Recibos Pendientes',
                    'Recibos con Match',
                    'Recibos sin Match',
                    'Conflictos',
                    '',
                    'Total Transacciones',
                    'Transacciones Matched',
                    'Transacciones sin Match',
                    '',
                    'Última Carga CSV',
                ],
                'Valor': [
                    worker.nombre,
                    period.month_year,
                    period.status.value,
                    'Cierre Final' if export_type == 'closure' else 'Temporal',
                    format_datetime_spanish(datetime.now()),
                    '',
                    summary_stats.total_receipts if summary_stats else 0,
                    summary_stats.processed_receipts if summary_stats else 0,
                    summary_stats.pending_receipts if summary_stats else 0,
                    summary_stats.matched_receipts if summary_stats else 0,
                    summary_stats.unmatched_receipts if summary_stats else 0,
                    summary_stats.conflicts if summary_stats else 0,
                    '',
                    summary_stats.total_transactions if summary_stats else 0,
                    summary_stats.matched_transactions if summary_stats else 0,
                    summary_stats.unmatched_transactions if summary_stats else 0,
                    '',
                    format_datetime_spanish(period.csv_last_upload) if period.csv_last_upload else 'N/A',
                ]
            }
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='Resumen', index=False)
            
            # Receipts sheet
            df_receipts = pd.DataFrame(receipts_data)
            df_receipts.to_excel(writer, sheet_name='Recibos', index=False)
            
            # Transactions sheet
            df_transactions = pd.DataFrame(transactions_data)
            df_transactions.to_excel(writer, sheet_name='Transacciones Banco', index=False)
            
            # Unmatched receipts sheet
            unmatched_receipts = [r for r in receipts_data if r['Tipo Match'] in ['sin_match', 'none']]
            df_unmatched = pd.DataFrame(unmatched_receipts)
            df_unmatched.to_excel(writer, sheet_name='Recibos sin Match', index=False)
        
        logger.info(f"Exported period {period_id} data to {output_path} ({export_type})")
        return str(output_path)
