"""Receipt repository for database operations."""
import sqlite3
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

from .base import BaseRepository
from ..models.domain import Receipt


class ReceiptRepository(BaseRepository[Receipt]):
    """Repository for receipt data access."""
    
    def _row_to_model(self, row: sqlite3.Row) -> Receipt:
        """Convert database row to Receipt model."""
        # Handle description field with fallback for old databases
        try:
            description = row['description'] or ''
        except (KeyError, IndexError):
            description = ''
        
        # Deserialize extracted_data
        extracted_data = self._deserialize_json_field(row['extracted_data']) or {}
        
        # If description is empty, try to use 'empresa' from extracted_data
        if not description and extracted_data:
            description = extracted_data.get('empresa', '') or ''
        
        # Handle worker_id and period_id with fallback for old databases
        try:
            worker_id = row['worker_id']
        except (KeyError, IndexError):
            worker_id = None
        
        try:
            period_id = row['period_id']
        except (KeyError, IndexError):
            period_id = None
        
        return Receipt(
            id=row['id'],
            file_path=row['file_path'],
            original_filename=row['original_filename'],
            receipt_type=row['receipt_type'],
            date=self._parse_datetime(row['date']),
            amount=Decimal(row['amount']) if row['amount'] else None,
            description=description,
            extracted_data=extracted_data,
            processing_successful=bool(row['processing_successful']),
            error_message=row['error_message'],
            created_at=self._parse_datetime(row['created_at']),
            updated_at=self._parse_datetime(row['updated_at']),
            worker_id=worker_id,
            period_id=period_id,
        )
    
    def _model_to_dict(self, model: Receipt) -> dict:
        """Convert Receipt model to dictionary."""
        return {
            'file_path': model.file_path,
            'original_filename': model.original_filename,
            'receipt_type': model.receipt_type,
            'date': self._format_datetime(model.date),
            'amount': str(model.amount) if model.amount else None,
            'description': model.description or '',
            'extracted_data': self._serialize_json_field(model.extracted_data),
            'processing_successful': int(model.processing_successful),
            'error_message': model.error_message,
            'updated_at': datetime.now().isoformat(),
        }
    
    def create(self, receipt: Receipt) -> Receipt:
        """Create a new receipt."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            data = self._model_to_dict(receipt)
            
            cursor.execute('''
                INSERT INTO receipts 
                (file_path, original_filename, receipt_type, date, amount, description,
                 extracted_data, processing_successful, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['file_path'], data['original_filename'], data['receipt_type'],
                data['date'], data['amount'], data['description'],
                data['extracted_data'], data['processing_successful'], data['error_message']
            ))
            
            receipt.id = cursor.lastrowid
            return receipt
    
    def get_by_id(self, receipt_id: int) -> Optional[Receipt]:
        """Get receipt by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,))
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None
    
    def get_by_file_path(self, file_path: str) -> Optional[Receipt]:
        """Get receipt by file path."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM receipts WHERE file_path = ?', (file_path,))
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None
    
    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[Receipt]:
        """Get all receipts."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # query = 'SELECT * FROM receipts ORDER BY created_at DESC'
            query = 'SELECT * FROM receipts ORDER BY date ASC'
            if limit:
                query += f' LIMIT {limit} OFFSET {offset}'
            cursor.execute(query)
            return [self._row_to_model(row) for row in cursor.fetchall()]
    
    def update(self, receipt: Receipt) -> bool:
        """Update existing receipt."""
        if not receipt.id:
            return False
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            data = self._model_to_dict(receipt)
            
            cursor.execute('''
                UPDATE receipts SET
                    file_path = ?, original_filename = ?, receipt_type = ?,
                    date = ?, amount = ?, description = ?, extracted_data = ?,
                    processing_successful = ?, error_message = ?, updated_at = ?
                WHERE id = ?
            ''', (
                data['file_path'], data['original_filename'], data['receipt_type'],
                data['date'], data['amount'], data['description'], data['extracted_data'],
                data['processing_successful'], data['error_message'],
                data['updated_at'], receipt.id
            ))
            
            return cursor.rowcount > 0
    
    def delete(self, receipt_id: int) -> bool:
        """Delete receipt by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM receipts WHERE id = ?', (receipt_id,))
            return cursor.rowcount > 0
    
    def get_by_type(self, receipt_type: str) -> List[Receipt]:
        """Get receipts by type."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM receipts WHERE receipt_type = ? ORDER BY date DESC',
                (receipt_type,)
            )
            return [self._row_to_model(row) for row in cursor.fetchall()]
    
    def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Receipt]:
        """Get receipts within date range."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM receipts 
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC
            ''', (start_date.isoformat(), end_date.isoformat()))
            return [self._row_to_model(row) for row in cursor.fetchall()]
    
    def count(self) -> int:
        """Get total count of receipts."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM receipts')
            return cursor.fetchone()[0]
    
    def update_file_path(self, receipt_id: int, new_path: str) -> bool:
        """Update file path for a receipt."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE receipts SET file_path = ?, updated_at = ?
                WHERE id = ?
            ''', (new_path, datetime.now().isoformat(), receipt_id))
            return cursor.rowcount > 0
    
    # ===== ROC SKINCARE: Multi-worker methods =====
    
    def get_by_period(self, period_id: int) -> List[Receipt]:
        """Get all receipts for a period."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM receipts WHERE period_id = ? ORDER BY created_at DESC',
                (period_id,)
            )
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def get_by_worker(self, worker_id: int) -> List[Receipt]:
        """Get all receipts for a worker."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM receipts WHERE worker_id = ? ORDER BY created_at DESC',
                (worker_id,)
            )
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def update_worker_and_period(self, receipt_id: int, worker_id: int, period_id: int) -> bool:
        """Update worker_id and period_id for a receipt."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE receipts SET worker_id = ?, period_id = ?, updated_at = ?
                WHERE id = ?
            ''', (worker_id, period_id, datetime.now().isoformat(), receipt_id))
            return cursor.rowcount > 0

