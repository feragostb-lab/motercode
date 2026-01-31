"""Service for period closure and reopening."""
import logging
import shutil
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from zipfile import ZipFile

from ..repositories.period_repository import PeriodRepository
from ..repositories.worker_repository import WorkerRepository
from ..repositories.receipt_repository import ReceiptRepository
from ..repositories.match_repository import MatchRepository
from ..repositories.bank_repository import BankRepository
from ..models.domain import Period, PeriodStatus, PeriodStats
from ..core.database import get_database
from ..utils.file_helpers import get_period_paths
from ..utils.formatters import format_datetime_spanish

logger = logging.getLogger(__name__)


class PeriodClosureService:
    """Service for closing and reopening periods."""
    
    def __init__(self, config):
        """Initialize service."""
        self.config = config
        self.db = get_database(config.paths.get('database', './receipts.db'))
        self.period_repo = PeriodRepository(self.db)
        self.worker_repo = WorkerRepository(self.db)
        self.receipt_repo = ReceiptRepository(self.db)
        self.match_repo = MatchRepository(self.db)
        self.bank_repo = BankRepository(self.db)
    
    def validate_closure(self, period_id: int) -> Dict[str, Any]:
        """
        Validate if period can be closed.
        
        Args:
            period_id: Period to validate
            
        Returns:
            Dict with:
                - can_close: bool
                - blocking_reasons: List[str] with reasons if can't close
                - stats: Dict with period statistics
        """
        period = self.period_repo.get_by_id(period_id)
        if not period:
            return {
                'can_close': False,
                'blocking_reasons': ['Periodo no existe'],
                'stats': {}
            }
        
        blocking_reasons = []
        
        # 1. Check CSV uploaded (MANDATORY - no force allowed)
        if not period.csv_file_path or not period.csv_last_upload:
            blocking_reasons.append('No se ha cargado ningún archivo CSV bancario')
        
        # TODO: Implement full validation
        # 2. Check all receipts processed (processing_successful = 1)
        # 3. Check all receipts matched (no NONE matches)
        # 4. Check no unresolved conflicts (is_conflict = 0 OR conflict_accepted = 1)
        
        stats = {
            'total_receipts': 0,
            'processed_receipts': 0,
            'matched_receipts': 0,
            'conflict_receipts': 0,
            'has_csv': bool(period.csv_file_path),
            'csv_upload_date': period.csv_last_upload
        }
        
        return {
            'can_close': len(blocking_reasons) == 0,
            'blocking_reasons': blocking_reasons,
            'stats': stats
        }
    
    def close_period(self, period_id: int) -> Optional[str]:
        """
        Close a period and generate export ZIP.
        
        VALIDATION: Must have CSV + 100% processed + 100% matched + no conflicts
        
        Args:
            period_id: Period to close
            
        Returns:
            Path to generated ZIP file, or None if failed
            
        Raises:
            ValueError: If validation fails
        """
        # Validate
        validation = self.validate_closure(period_id)
        if not validation['can_close']:
            reasons = "\n".join(validation['blocking_reasons'])
            raise ValueError(f"No se puede cerrar el periodo:\n{reasons}")
        
        period = self.period_repo.get_by_id(period_id)
        if not period:
            raise ValueError(f"Periodo {period_id} no existe")
        
        worker = self.worker_repo.get_by_id(period.worker_id)
        if not worker:
            raise ValueError("Trabajador no encontrado")
        
        # Generate export Excel using ExportService
        export_path = self.export_period_data(period_id, export_type='closure')
        
        # Create ZIP with result/ images + CSV + Excel
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        paths = get_period_paths(worker.nombre, period.month_year)
        zip_filename = f"closure_{timestamp}.zip"
        zip_path = paths['base'] / zip_filename
        
        try:
            with ZipFile(zip_path, 'w') as zipf:
                # Add all files from result/
                if paths['result'].exists():
                    for file in paths['result'].iterdir():
                        if file.is_file():
                            zipf.write(file, arcname=f"result/{file.name}")
                
                # Add last CSV
                if period.csv_file_path and Path(period.csv_file_path).exists():
                    csv_path = Path(period.csv_file_path)
                    zipf.write(csv_path, arcname=f"csv/{csv_path.name}")
                
                # Add generated Excel export
                if Path(export_path).exists():
                    zipf.write(export_path, arcname=f"export/{Path(export_path).name}")
            
            logger.info(f"Created closure ZIP: {zip_path}")
            
        except Exception as e:
            logger.error(f"Error creating closure ZIP: {e}")
            raise ValueError(f"Error al crear archivo ZIP de cierre: {e}")
        
        # Mark period as closed
        closed_at = datetime.now().isoformat()
        self.period_repo.close_period(period_id, closed_at)
        
        # Save closure record
        # TODO: Insert into period_closures table
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO period_closures 
                   (period_id, closure_date, export_path, stats_snapshot)
                   VALUES (?, ?, ?, ?)''',
                (period_id, closed_at, str(zip_path), json.dumps(validation['stats']))
            )
        
        logger.info(f"Period {period_id} closed successfully: {zip_path}")
        return str(zip_path)
    
    def reopen_period(self, period_id: int, reason: str) -> bool:
        """
        Reopen a closed period.
        
        NOTE: Requires double confirmation from UI
        
        Args:
            period_id: Period to reopen
            reason: Mandatory reason for reopening
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If period is not closed or reason is empty
        """
        if not reason or not reason.strip():
            raise ValueError("Debe proporcionar una razón para reabrir el periodo")
        
        period = self.period_repo.get_by_id(period_id)
        if not period:
            raise ValueError(f"Periodo {period_id} no existe")
        
        if period.status != PeriodStatus.CLOSED:
            raise ValueError("Solo se pueden reabrir periodos cerrados")
        
        worker = self.worker_repo.get_by_id(period.worker_id)
        if not worker:
            raise ValueError("Trabajador no encontrado")
        
        # Find existing closure ZIP
        paths = get_period_paths(worker.nombre, period.month_year)
        closure_zips = list(paths['base'].glob('closure_*.zip'))
        
        # Rename existing ZIP if found
        if closure_zips:
            for old_zip in closure_zips:
                if '_reopened_' not in old_zip.name:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    new_name = old_zip.stem + f"_reopened_{timestamp}.zip"
                    new_path = old_zip.parent / new_name
                    try:
                        old_zip.rename(new_path)
                        logger.info(f"Renamed closure ZIP: {new_path}")
                    except Exception as e:
                        logger.warning(f"Could not rename ZIP: {e}")
        
        # Reopen period in database
        success = self.period_repo.reopen_period(period_id)
        
        if success:
            # Update closure record
            reopened_at = datetime.now().isoformat()
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''UPDATE period_closures 
                       SET reopened_at = ?, reopen_reason = ?
                       WHERE period_id = ? 
                       ORDER BY closure_date DESC 
                       LIMIT 1''',
                    (reopened_at, reason, period_id)
                )
            
            logger.info(f"Period {period_id} reopened. Reason: {reason}")
        
        return success
    
    def export_period_data(self, period_id: int, export_type: str = 'temporal') -> str:
        """
        Export period data to Excel usando export_service.
        
        Args:
            period_id: Period to export
            export_type: 'temporal' or 'closure'
            
        Returns:
            Path to generated Excel file
        """
        from ..services.export_service import ExportService
        
        # Usar ExportService que ahora tiene el formato correcto con openpyxl
        export_service = ExportService(self.config)
        return export_service.export_period_data(period_id, export_type=export_type)
