"""Processing queue repository."""
import sqlite3
from typing import List, Optional
from datetime import datetime

from .base import BaseRepository
from ..models.domain import ProcessingQueueItem, ProcessingStatus


class QueueRepository(BaseRepository[ProcessingQueueItem]):
    """Repository for processing queue operations."""
    
    def _row_to_model(self, row: sqlite3.Row) -> ProcessingQueueItem:
        """Convert database row to ProcessingQueueItem model."""
        period_id = row['period_id'] if 'period_id' in row.keys() else None
        return ProcessingQueueItem(
            id=row['id'],
            file_path=row['file_path'],
            status=ProcessingStatus(row['status']),
            attempts=row['attempts'],
            last_error=row['last_error'],
            created_at=self._parse_datetime(row['created_at']),
            started_at=self._parse_datetime(row['started_at']),
            processed_at=self._parse_datetime(row['processed_at']),
            period_id=period_id,
        )
    
    def _model_to_dict(self, model: ProcessingQueueItem) -> dict:
        """Convert model to dictionary."""
        return {
            'file_path': model.file_path,
            'status': model.status.value,
            'attempts': model.attempts,
            'last_error': model.last_error,
            'started_at': self._format_datetime(model.started_at),
            'processed_at': self._format_datetime(model.processed_at),
        }
    
    def enqueue(self, file_path: str, period_id: Optional[int] = None) -> ProcessingQueueItem:
        """Add file to processing queue."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO processing_queue (file_path, status, attempts, period_id)
                    VALUES (?, 'pending', 0, ?)
                ''', (file_path, period_id))
                
                item = ProcessingQueueItem(
                    id=cursor.lastrowid,
                    file_path=file_path,
                    status=ProcessingStatus.PENDING,
                    attempts=0,
                    period_id=period_id,
                )
                return item
            except sqlite3.IntegrityError:
                # File already in queue
                cursor.execute('SELECT * FROM processing_queue WHERE file_path = ?', (file_path,))
                row = cursor.fetchone()
                return self._row_to_model(row) if row else None
    
    def get_next_pending(self, period_id: Optional[int] = None) -> Optional[ProcessingQueueItem]:
        """Get next pending item from queue (FIFO)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT * FROM processing_queue 
                WHERE status = 'pending'
            '''
            params: list = []
            if period_id is not None:
                query += ' AND period_id = ?'
                params.append(period_id)
            query += '''
                ORDER BY created_at ASC
                LIMIT 1
            '''
            cursor.execute(query, params)
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None
    
    def get_by_id(self, item_id: int) -> Optional[ProcessingQueueItem]:
        """Get queue item by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM processing_queue WHERE id = ?', (item_id,))
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None
    
    def mark_processing(self, item_id: int) -> bool:
        """Mark item as processing."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE processing_queue 
                SET status = 'processing', started_at = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), item_id))
            return cursor.rowcount > 0
    
    def mark_completed(self, item_id: int) -> bool:
        """Mark item as completed."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE processing_queue 
                SET status = 'completed', processed_at = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), item_id))
            return cursor.rowcount > 0
    
    def mark_failed(self, item_id: int, error_message: str) -> bool:
        """Mark item as failed and increment attempts."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE processing_queue 
                SET status = 'failed', attempts = attempts + 1,
                    last_error = ?, processed_at = ?
                WHERE id = ?
            ''', (error_message, datetime.now().isoformat(), item_id))
            return cursor.rowcount > 0
    
    def mark_interrupted(self, item_id: int) -> bool:
        """Mark item as interrupted (will be auto-reset to pending on next start)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE processing_queue 
                SET status = 'interrupted'
                WHERE id = ?
            ''', (item_id,))
            return cursor.rowcount > 0
    
    def reset_to_pending(self, item_id: int) -> bool:
        """Reset item back to pending status for retry."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE processing_queue 
                SET status = 'pending', started_at = NULL
                WHERE id = ?
            ''', (item_id,))
            return cursor.rowcount > 0
    
    def auto_reset_interrupted(self) -> int:
        """Reset all 'processing' items to 'pending' (recovery from crash)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE processing_queue 
                SET status = 'pending', started_at = NULL
                WHERE status = 'processing' OR status = 'interrupted'
            ''')
            count = cursor.rowcount
            if count > 0:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Auto-reset {count} interrupted items to pending")
            return count
    
    def get_pending_count(self, period_id: Optional[int] = None) -> int:
        """Get count of pending items."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT COUNT(*) FROM processing_queue WHERE status = 'pending'"
            params: list = []
            if period_id is not None:
                query += " AND period_id = ?"
                params.append(period_id)
            cursor.execute(query, params)
            return cursor.fetchone()[0]
    
    def get_stats(self, period_id: Optional[int] = None) -> dict:
        """Get queue statistics."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT 
                    status,
                    COUNT(*) as count
                FROM processing_queue
            '''
            params: list = []
            if period_id is not None:
                query += ' WHERE period_id = ?'
                params.append(period_id)
            query += '''
                GROUP BY status
            '''
            cursor.execute(query, params)
            stats = {row['status']: row['count'] for row in cursor.fetchall()}
            
            # Ensure all statuses are present
            for status in ['pending', 'processing', 'completed', 'failed']:
                if status not in stats:
                    stats[status] = 0
            
            return stats
    
    def clear_completed(self) -> int:
        """Remove completed items from queue."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM processing_queue WHERE status = 'completed'")
            return cursor.rowcount
    
    def get_failed_items(self) -> List[ProcessingQueueItem]:
        """Get all failed items."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM processing_queue 
                WHERE status = 'failed'
                ORDER BY processed_at DESC
            ''')
            return [self._row_to_model(row) for row in cursor.fetchall()]
