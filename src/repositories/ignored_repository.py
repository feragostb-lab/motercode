"""Ignored receipts repository."""
import sqlite3
from typing import List, Optional, Set
from datetime import datetime

from .base import BaseRepository
from ..models.domain import IgnoredReceipt


class IgnoredRepository(BaseRepository[IgnoredReceipt]):
    """Repository for ignored receipts."""
    
    def _row_to_model(self, row: sqlite3.Row) -> IgnoredReceipt:
        """Convert database row to IgnoredReceipt model."""
        return IgnoredReceipt(
            id=row['id'],
            receipt_id=row['receipt_id'],
            ignored_at=self._parse_datetime(row['ignored_at']),
            reason=row['reason'],
        )
    
    def _model_to_dict(self, model: IgnoredReceipt) -> dict:
        """Convert model to dictionary."""
        return {
            'receipt_id': model.receipt_id,
            'reason': model.reason,
        }
    
    def ignore_receipt(self, receipt_id: int, reason: Optional[str] = None) -> IgnoredReceipt:
        """Mark a receipt as ignored."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO ignored_receipts (receipt_id, reason)
                    VALUES (?, ?)
                ''', (receipt_id, reason))
                
                return IgnoredReceipt(
                    id=cursor.lastrowid,
                    receipt_id=receipt_id,
                    ignored_at=datetime.now(),
                    reason=reason,
                )
            except sqlite3.IntegrityError:
                # Already ignored
                cursor.execute('SELECT * FROM ignored_receipts WHERE receipt_id = ?', (receipt_id,))
                row = cursor.fetchone()
                return self._row_to_model(row) if row else None
    
    def unignore_receipt(self, receipt_id: int) -> bool:
        """Remove ignored status from a receipt."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM ignored_receipts WHERE receipt_id = ?', (receipt_id,))
            return cursor.rowcount > 0
    
    def is_ignored(self, receipt_id: int) -> bool:
        """Check if receipt is ignored."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM ignored_receipts WHERE receipt_id = ? LIMIT 1', (receipt_id,))
            return cursor.fetchone() is not None
    
    def get_all_ignored_ids(self) -> Set[int]:
        """Get set of all ignored receipt IDs."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT receipt_id FROM ignored_receipts')
            return {row['receipt_id'] for row in cursor.fetchall()}
    
    def get_all(self) -> List[IgnoredReceipt]:
        """Get all ignored receipts."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM ignored_receipts ORDER BY ignored_at DESC')
            return [self._row_to_model(row) for row in cursor.fetchall()]
    
    def count(self) -> int:
        """Get count of ignored receipts."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM ignored_receipts')
            return cursor.fetchone()[0]
