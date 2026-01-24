"""Repository for period management."""
import logging
from typing import List, Optional
import sqlite3

from .base import BaseRepository
from ..models.domain import Period, PeriodStatus
from ..utils.formatters import parse_datetime

logger = logging.getLogger(__name__)


class PeriodRepository(BaseRepository):
    """Repository for managing periods."""
    
    def _row_to_model(self, row) -> Period:
        """Convert database row to Period model."""
        return Period(
            id=row['id'],
            worker_id=row['worker_id'],
            month_year=row['month_year'],
            status=PeriodStatus(row['status']) if row['status'] else PeriodStatus.ACTIVE,
            is_processing_active=bool(row['is_processing_active']),
            csv_last_upload=parse_datetime(row['csv_last_upload']) if row['csv_last_upload'] else None,
            csv_file_path=row['csv_file_path'],
            closed_at=parse_datetime(row['closed_at']) if row['closed_at'] else None,
            created_at=parse_datetime(row['created_at']) if row['created_at'] else None
        )
    
    def _model_to_dict(self, period: Period) -> dict:
        """Convert Period model to dictionary for database."""
        return {
            'worker_id': period.worker_id,
            'month_year': period.month_year,
            'status': period.status.value,
            'is_processing_active': int(period.is_processing_active)
        }
    
    def create(self, worker_id: int, month_year: str) -> Optional[Period]:
        """
        Create a new period.
        
        Args:
            worker_id: Worker ID
            month_year: Period in format "MMYYYY"
            
        Returns:
            Created period or None if failed
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''INSERT INTO periods (worker_id, month_year, status, is_processing_active)
                       VALUES (?, ?, ?, ?)''',
                    (worker_id, month_year, PeriodStatus.ACTIVE.value, 0)
                )
                period_id = cursor.lastrowid
                
                cursor.execute('SELECT * FROM periods WHERE id = ?', (period_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_model(row)
                return None
                
        except sqlite3.IntegrityError as e:
            logger.error(f"Period already exists: worker_id={worker_id}, month_year={month_year}")
            raise ValueError(f"El periodo {month_year} ya existe para este trabajador")
        except Exception as e:
            logger.error(f"Error creating period: {e}")
            return None
    
    def get_by_id(self, period_id: int) -> Optional[Period]:
        """Get period by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM periods WHERE id = ?', (period_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_model(row)
            return None
    
    def get_by_worker_and_month(self, worker_id: int, month_year: str) -> Optional[Period]:
        """Get period by worker and month_year."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM periods WHERE worker_id = ? AND month_year = ?',
                (worker_id, month_year)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_model(row)
            return None
    
    def get_by_worker(self, worker_id: int, status: Optional[PeriodStatus] = None) -> List[Period]:
        """
        Get all periods for a worker.
        
        Args:
            worker_id: Worker ID
            status: Optional filter by status
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            if status:
                cursor.execute(
                    'SELECT * FROM periods WHERE worker_id = ? AND status = ? ORDER BY month_year DESC',
                    (worker_id, status.value)
                )
            else:
                cursor.execute(
                    'SELECT * FROM periods WHERE worker_id = ? ORDER BY month_year DESC',
                    (worker_id,)
                )
            
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def get_all(self, status: Optional[PeriodStatus] = None) -> List[Period]:
        """
        Get all periods across all workers.
        
        Args:
            status: Optional filter by status
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            if status:
                cursor.execute(
                    'SELECT * FROM periods WHERE status = ? ORDER BY month_year DESC',
                    (status.value,)
                )
            else:
                cursor.execute('SELECT * FROM periods ORDER BY month_year DESC')
            
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def get_active_processing_period(self) -> Optional[Period]:
        """Get the currently active processing period (only one can exist)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM periods WHERE is_processing_active = 1')
            row = cursor.fetchone()
            
            if row:
                return self._row_to_model(row)
            return None
    
    def set_processing_active(self, period_id: int) -> bool:
        """
        Set a period as active for processing (deactivates all others).
        
        Args:
            period_id: Period to activate
            
        Returns:
            True if successful
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Deactivate all periods
                cursor.execute('UPDATE periods SET is_processing_active = 0')
                
                # Activate the selected period
                cursor.execute(
                    'UPDATE periods SET is_processing_active = 1 WHERE id = ?',
                    (period_id,)
                )
                
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error setting processing active period: {e}")
            return False
    
    def update_csv_upload(self, period_id: int, csv_file_path: str, upload_date: str) -> bool:
        """Update CSV upload information."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''UPDATE periods 
                       SET csv_last_upload = ?, csv_file_path = ?
                       WHERE id = ?''',
                    (upload_date, csv_file_path, period_id)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating CSV upload: {e}")
            return False
    
    def close_period(self, period_id: int, closed_at: str) -> bool:
        """Mark period as closed."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''UPDATE periods 
                       SET status = ?, closed_at = ?, is_processing_active = 0
                       WHERE id = ?''',
                    (PeriodStatus.CLOSED.value, closed_at, period_id)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error closing period: {e}")
            return False
    
    def reopen_period(self, period_id: int) -> bool:
        """Reopen a closed period."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''UPDATE periods 
                       SET status = ?, closed_at = NULL
                       WHERE id = ?''',
                    (PeriodStatus.ACTIVE.value, period_id)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error reopening period: {e}")
            return False
    

