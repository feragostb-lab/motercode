"""Match repository for receipt-bank transaction matches."""
import sqlite3
from typing import List, Optional
from datetime import datetime

from .base import BaseRepository
from ..models.domain import Match, MatchType


class MatchRepository(BaseRepository[Match]):
    """Repository for match data access."""
    
    def _row_to_model(self, row: sqlite3.Row) -> Match:
        """Convert database row to Match model."""
        return Match(
            id=row['id'],
            receipt_id=row['receipt_id'],
            transaction_id=row['transaction_id'],
            match_type=MatchType(row['match_type']) if row['match_type'] else MatchType.NONE,
            confidence=row['confidence'],
            is_conflict=bool(row['is_conflict']),
            conflict_accepted=bool(row['conflict_accepted']),
            created_at=self._parse_datetime(row['created_at']),
        )
    
    def _model_to_dict(self, model: Match) -> dict:
        """Convert model to dictionary."""
        return {
            'receipt_id': model.receipt_id,
            'transaction_id': model.transaction_id,
            'match_type': model.match_type.value if model.match_type else None,
            'confidence': model.confidence,
            'is_conflict': int(model.is_conflict),
            'conflict_accepted': int(model.conflict_accepted),
        }
    
    def create(self, match: Match) -> Match:
        """Create a new match."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            data = self._model_to_dict(match)
            
            cursor.execute('''
                INSERT INTO matches 
                (receipt_id, transaction_id, match_type, confidence, is_conflict, conflict_accepted)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (data['receipt_id'], data['transaction_id'], data['match_type'],
                  data['confidence'], data['is_conflict'], data['conflict_accepted']))
            
            match.id = cursor.lastrowid
            return match
    
    def get_all(self) -> List[Match]:
        """Get all matches."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM matches')
            return [self._row_to_model(row) for row in cursor.fetchall()]
    
    def get_by_receipt_id(self, receipt_id: int) -> Optional[Match]:
        """Get match for a receipt."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM matches WHERE receipt_id = ?', (receipt_id,))
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None
    
    def get_by_transaction_id(self, transaction_id: int) -> List[Match]:
        """Get all matches for a transaction (may have conflicts)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM matches WHERE transaction_id = ?', (transaction_id,))
            return [self._row_to_model(row) for row in cursor.fetchall()]
    
    def update(self, match: Match) -> bool:
        """Update existing match."""
        if not match.id:
            return False
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            data = self._model_to_dict(match)
            
            cursor.execute('''
                UPDATE matches SET
                    receipt_id = ?, transaction_id = ?, match_type = ?,
                    confidence = ?, is_conflict = ?, conflict_accepted = ?
                WHERE id = ?
            ''', (data['receipt_id'], data['transaction_id'], data['match_type'],
                  data['confidence'], data['is_conflict'], data['conflict_accepted'],
                  match.id))
            
            return cursor.rowcount > 0
    
    def delete_by_receipt_id(self, receipt_id: int) -> bool:
        """Delete match for a receipt."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM matches WHERE receipt_id = ?', (receipt_id,))
            return cursor.rowcount > 0
    
    def accept_conflict(self, receipt_id: int) -> bool:
        """Mark conflict as accepted for a receipt."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE matches 
                SET conflict_accepted = 1
                WHERE receipt_id = ?
            ''', (receipt_id,))
            return cursor.rowcount > 0
    
    def get_all_conflicts(self) -> List[Match]:
        """Get all matches that are conflicts."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM matches WHERE is_conflict = 1')
            return [self._row_to_model(row) for row in cursor.fetchall()]
    
    def clear_all(self) -> int:
        """Clear all matches (for recalculation)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM matches')
            return cursor.rowcount
