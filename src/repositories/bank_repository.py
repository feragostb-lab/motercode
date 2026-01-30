"""Bank transaction repository."""
import sqlite3
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import pandas as pd

from .base import BaseRepository
from ..models.domain import BankTransaction


class BankRepository(BaseRepository[BankTransaction]):
    """Repository for bank transaction data access."""
    
    def _row_to_model(self, row: sqlite3.Row) -> BankTransaction:
        """Convert database row to BankTransaction model."""
        return BankTransaction(
            id=row['id'],
            date=self._parse_datetime(row['date']),
            amount=Decimal(row['amount']) if row['amount'] else None,
            description=row['description'],
            reference=row['reference'],
            receipt_type=row['receipt_type'] if 'receipt_type' in row.keys() else "",
            matched_receipt_id=row['matched_receipt_id'],
            csv_row_number=row['csv_row_number'] if 'csv_row_number' in row.keys() else None,
            created_at=self._parse_datetime(row['created_at']),
        )
    
    def _model_to_dict(self, model: BankTransaction) -> dict:
        """Convert model to dictionary."""
        return {
            'date': self._format_datetime(model.date),
            'amount': str(model.amount) if model.amount else None,
            'description': model.description,
            'reference': model.reference,
            'receipt_type': model.receipt_type,
            'matched_receipt_id': model.matched_receipt_id,
        }
    
    def create(self, transaction: BankTransaction) -> BankTransaction:
        """Create a new bank transaction."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            data = self._model_to_dict(transaction)
            
            cursor.execute('''
                INSERT INTO bank_transactions 
                (date, amount, description, reference, receipt_type, matched_receipt_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (data['date'], data['amount'], data['description'], 
                  data['reference'], data['receipt_type'], data['matched_receipt_id']))
            
            transaction.id = cursor.lastrowid
            return transaction
    
    def get_by_id(self, transaction_id: int) -> Optional[BankTransaction]:
        """Get transaction by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM bank_transactions WHERE id = ?', (transaction_id,))
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None
    
    def get_all(self) -> List[BankTransaction]:
        """Get all bank transactions."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM bank_transactions ORDER BY id ASC')
            return [self._row_to_model(row) for row in cursor.fetchall()]
    
    def get_unmatched(self) -> List[BankTransaction]:
        """Get transactions without a matched receipt."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM bank_transactions 
                WHERE matched_receipt_id IS NULL
                ORDER BY date DESC
            ''')
            return [self._row_to_model(row) for row in cursor.fetchall()]
    
    def update_match(self, transaction_id: int, receipt_id: Optional[int]) -> bool:
        """Update matched receipt for a transaction."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE bank_transactions 
                SET matched_receipt_id = ?
                WHERE id = ?
            ''', (receipt_id, transaction_id))
            return cursor.rowcount > 0

    def update_receipt_type(self, transaction_id: int, receipt_type: Optional[str]) -> bool:
        """Update receipt_type for a transaction."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE bank_transactions 
                SET receipt_type = ?
                WHERE id = ?
            ''', (receipt_type, transaction_id))
            return cursor.rowcount > 0
    
    def clear_all(self) -> int:
        """Clear all bank transactions (for re-import)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM bank_transactions')
            return cursor.rowcount
    
    def bulk_create(self, transactions: List[BankTransaction]) -> int:
        """Bulk insert transactions (more efficient for Excel import)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            data_list = [(
                self._format_datetime(t.date),
                str(t.amount) if t.amount else None,
                t.description,
                t.reference,
                t.receipt_type,
                t.matched_receipt_id
            ) for t in transactions]
            
            cursor.executemany('''
                INSERT INTO bank_transactions 
                (date, amount, description, reference, receipt_type, matched_receipt_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', data_list)
            
            return cursor.rowcount
    
    def load_from_excel(self, excel_path: str, skip_rows: int = 13) -> int:
        """
        Load bank transactions from Excel file.
        
        Args:
            excel_path: Path to Excel file
            skip_rows: Number of header rows to skip (default: 13)
            
        Returns:
            Number of transactions loaded
        """
        # Read Excel file
        df = pd.read_excel(excel_path, skiprows=skip_rows)
        
        # Clean column names
        df.columns = ['fecha', 'descripcion', 'metodo', 'importe']
        
        # Remove rows with no date
        df = df[df['fecha'].notna()].copy()
        
        # Filter out summary rows (containing month names or totals)
        summary_keywords = [
            'MES', 'SITUACIÓN', 'SITUACION', 
            'DICIEMBRE', 'ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO',
            'JUNIO', 'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE'
        ]
        pattern = '|'.join(summary_keywords)
        df = df[~df['fecha'].astype(str).str.upper().str.contains(pattern, na=False)].copy()
        
        # Parse dates
        df['fecha_procesada'] = pd.to_datetime(df['fecha'], format='%d.%m.%Y', errors='coerce')
        
        # Remove rows with invalid dates
        df = df[df['fecha_procesada'].notna()].copy()
        
        # Process amounts (convert to positive Decimal)
        def process_amount(amount):
            if pd.isna(amount):
                return None
            if isinstance(amount, (int, float)):
                return Decimal(str(abs(float(amount))))
            # Clean string and convert
            amount_str = str(amount).replace(',', '.').replace('-', '').strip()
            try:
                return Decimal(str(abs(float(amount_str))))
            except:
                return None
        
        df['importe_procesado'] = df['importe'].apply(process_amount)
        
        # Remove rows with invalid amounts
        df = df[df['importe_procesado'].notna()].copy()
        
        # Clear existing transactions
        self.clear_all()
        
        # Create transaction objects
        transactions = []
        for _, row in df.iterrows():
            transaction = BankTransaction(
                date=row['fecha_procesada'].to_pydatetime(),
                amount=row['importe_procesado'],
                description=str(row['descripcion']) if pd.notna(row['descripcion']) else None,
                reference=str(row['metodo']) if pd.notna(row['metodo']) else None,
                matched_receipt_id=None
            )
            transactions.append(transaction)
        
        # Bulk insert
        count = self.bulk_create(transactions)
        return count
    
    # ===== ROC SKINCARE: Multi-worker methods =====
    
    def get_by_period(self, period_id: int) -> List[BankTransaction]:
        """Get all bank transactions for a period."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM bank_transactions WHERE period_id = ? ORDER BY date DESC',
                (period_id,)
            )
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def get_by_worker(self, worker_id: int) -> List[BankTransaction]:
        """Get all bank transactions for a worker."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM bank_transactions WHERE worker_id = ? ORDER BY date DESC',
                (worker_id,)
            )
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def clear_by_period(self, period_id: int) -> int:
        """Clear all bank transactions for a specific period."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM bank_transactions WHERE period_id = ?', (period_id,))
            return cursor.rowcount
    
    def bulk_create_with_period(self, transactions: List[BankTransaction], 
                                worker_id: int, period_id: int, 
                                csv_file_path: str, csv_upload_date: str) -> int:
        """
        Bulk insert transactions with worker/period info (for CSV import).
        
        CRITICAL: Preserves original CSV row numbers in csv_row_number field.
        id is auto-generated to avoid conflicts between periods.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            data_list = [(
                self._format_datetime(t.date),
                str(t.amount) if t.amount else None,
                t.description,
                t.reference,
                t.receipt_type,
                t.matched_receipt_id,
                worker_id,
                period_id,
                csv_upload_date,
                csv_file_path,
                t.csv_row_number  # Preserve original CSV row number
            ) for t in transactions]
            
            cursor.executemany('''
                INSERT INTO bank_transactions 
                (date, amount, description, reference, receipt_type, matched_receipt_id,
                 worker_id, period_id, csv_upload_date, csv_file_path, csv_row_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', data_list)
            
            return cursor.rowcount

