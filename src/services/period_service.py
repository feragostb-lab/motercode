"""Service for period management."""
import logging
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..repositories.period_repository import PeriodRepository
from ..repositories.worker_repository import WorkerRepository
from ..repositories.receipt_repository import ReceiptRepository
from ..models.domain import Period, PeriodStatus, PeriodStats
from ..core.database import get_database
from ..utils.file_helpers import get_period_paths

logger = logging.getLogger(__name__)


class PeriodService:
    """Service for managing periods."""
    
    def __init__(self, config):
        """Initialize service."""
        self.config = config
        self.db = get_database(config.paths.get('database', './receipts.db'))
        self.period_repo = PeriodRepository(self.db)
        self.worker_repo = WorkerRepository(self.db)
        self.receipt_repo = ReceiptRepository(self.db)
        self.workers_base_dir = Path('./workers')
    
    def create_period(self, worker_id: int, month_year: str) -> Optional[Period]:
        """
        Create a new period with directory structure.
        
        Args:
            worker_id: Worker ID
            month_year: Period in format "MMYYYY" (e.g., "012026", "022026")
            
        Returns:
            Created period or None if failed
            
        Raises:
            ValueError: If format is invalid or period already exists
        """
        # Validate month_year format
        if not re.match(r'^\d{6}$', month_year):
            raise ValueError("El periodo debe tener formato MMYYYY (ej: 012026)")
        
        month = int(month_year[:2])
        if month < 1 or month > 12:
            raise ValueError("El mes debe estar entre 01 y 12")
        
        # Get worker to build path
        worker = self.worker_repo.get_by_id(worker_id)
        if not worker:
            raise ValueError(f"Trabajador con ID {worker_id} no existe")
        
        # Create period in database
        period = self.period_repo.create(worker_id, month_year)
        
        if period:
            # Create directory structure
            paths = get_period_paths(worker.nombre, month_year)
            paths['img'].mkdir(parents=True, exist_ok=True)
            paths['result'].mkdir(parents=True, exist_ok=True)
            paths['csv'].mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Created period directories for {worker.nombre}/{month_year}")
        
        return period
    
    def get_period(self, period_id: int) -> Optional[Period]:
        """Get period by ID."""
        return self.period_repo.get_by_id(period_id)
    
    def list_periods_by_worker(self, worker_id: int, status: Optional[PeriodStatus] = None) -> List[Period]:
        """
        List periods for a worker.
        
        Args:
            worker_id: Worker ID
            status: Optional filter by status
        """
        return self.period_repo.get_by_worker(worker_id, status)
    
    def list_all_periods(self, status: Optional[PeriodStatus] = None) -> List[Period]:
        """
        List all periods across all workers (for global view).
        
        Args:
            status: Optional filter by status
        """
        return self.period_repo.get_all(status)
    
    def get_active_processing_period(self) -> Optional[Period]:
        """Get the currently active processing period."""
        return self.period_repo.get_active_processing_period()
    
    def set_active_processing_period(self, period_id: int) -> bool:
        """
        Set a period as active for processing.
        
        NOTE: Caller must ensure processor is stopped before calling this.
        
        Args:
            period_id: Period to activate
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If period is closed
        """
        period = self.period_repo.get_by_id(period_id)
        if not period:
            raise ValueError(f"Periodo con ID {period_id} no existe")
        
        if period.status == PeriodStatus.CLOSED:
            raise ValueError("No se puede activar un periodo cerrado para procesamiento")
        
        return self.period_repo.set_processing_active(period_id)
    
    def get_unprocessed_images_count(self, period_id: int) -> int:
        """
        Count images in period's img/ directory that don't have a receipt record.
        
        Args:
            period_id: Period ID
            
        Returns:
            Count of unprocessed images (orphaned files)
        """
        period = self.period_repo.get_by_id(period_id)
        if not period:
            return 0
        
        worker = self.worker_repo.get_by_id(period.worker_id)
        if not worker:
            return 0
        
        # Get period paths
        paths = get_period_paths(worker.nombre, period.month_year)
        img_dir = paths['img']
        
        if not img_dir.exists():
            return 0
        
        # Count image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
        image_files = [f for f in img_dir.iterdir() 
                      if f.is_file() and f.suffix.lower() in image_extensions]
        
        # Get receipts for this period
        # TODO: Implement get_by_period in receipt_repository
        # For now, return file count
        return len(image_files)
    
    def get_period_status_summary(self, period_id: int) -> PeriodStats:
        """
        Get comprehensive status summary for a period.
        
        Args:
            period_id: Period ID
            
        Returns:
            PeriodStats with all information
        """
        period = self.period_repo.get_by_id(period_id)
        if not period:
            raise ValueError(f"Periodo {period_id} no existe")
        
        # TODO: Implement full stats calculation
        # For now return basic stats
        stats = PeriodStats(
            period_id=period_id,
            has_csv=bool(period.csv_file_path),
            csv_upload_date=period.csv_last_upload,
            unprocessed_images=self.get_unprocessed_images_count(period_id)
        )
        
        return stats
    
    def get_global_periods_overview(self) -> List[Dict[str, Any]]:
        """
        Get overview of all periods for all workers.
        
        Returns:
            List of dicts with period info, worker name, and basic stats
        """
        periods = self.period_repo.get_all()
        overview = []
        
        for period in periods:
            worker = self.worker_repo.get_by_id(period.worker_id)
            if not worker:
                continue
            
            # Get basic stats
            unprocessed = self.get_unprocessed_images_count(period.id)
            
            overview.append({
                'period': period,
                'worker_name': worker.nombre,
                'unprocessed_images': unprocessed,
            })
        
        return overview
