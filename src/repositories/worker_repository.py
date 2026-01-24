"""Repository for worker management."""
import logging
from typing import List, Optional
import sqlite3

from .base import BaseRepository
from ..models.domain import Worker
from ..utils.formatters import parse_datetime

logger = logging.getLogger(__name__)


class WorkerRepository(BaseRepository):
    """Repository for managing workers."""
    
    def _row_to_model(self, row) -> Worker:
        """Convert database row to Worker model."""
        return Worker(
            id=row['id'],
            nombre=row['nombre'],
            activo=bool(row['activo']),
            created_at=parse_datetime(row['created_at']) if row['created_at'] else None
        )
    
    def _model_to_dict(self, worker: Worker) -> dict:
        """Convert Worker model to dictionary for database."""
        return {
            'nombre': worker.nombre,
            'activo': int(worker.activo)
        }
    
    def create(self, nombre: str) -> Optional[Worker]:
        """
        Create a new worker.
        
        Args:
            nombre: Worker name (alphanumeric only)
            
        Returns:
            Created worker or None if failed
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO workers (nombre, activo) VALUES (?, ?)',
                    (nombre, 1)
                )
                worker_id = cursor.lastrowid
                
                # Retrieve created worker
                cursor.execute('SELECT * FROM workers WHERE id = ?', (worker_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_model(row)
                return None
                
        except sqlite3.IntegrityError as e:
            logger.error(f"Worker name already exists: {nombre}")
            raise ValueError(f"El trabajador '{nombre}' ya existe (ignorando mayúsculas/minúsculas)")
        except Exception as e:
            logger.error(f"Error creating worker: {e}")
            return None
    
    def get_by_id(self, worker_id: int) -> Optional[Worker]:
        """Get worker by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM workers WHERE id = ?', (worker_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_model(row)
            return None
    
    def get_by_nombre(self, nombre: str) -> Optional[Worker]:
        """Get worker by name (case-insensitive)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM workers WHERE LOWER(nombre) = LOWER(?)',
                (nombre,)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_model(row)
            return None
    
    def get_all(self, active_only: bool = False) -> List[Worker]:
        """
        Get all workers.
        
        Args:
            active_only: If True, return only active workers
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            if active_only:
                cursor.execute('SELECT * FROM workers WHERE activo = 1 ORDER BY nombre')
            else:
                cursor.execute('SELECT * FROM workers ORDER BY nombre')
            
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def deactivate(self, worker_id: int) -> bool:
        """Deactivate a worker (soft delete)."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE workers SET activo = 0 WHERE id = ?',
                    (worker_id,)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deactivating worker: {e}")
            return False
    
    def activate(self, worker_id: int) -> bool:
        """Activate a worker."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE workers SET activo = 1 WHERE id = ?',
                    (worker_id,)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error activating worker: {e}")
            return False
    

