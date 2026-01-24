"""Service for worker management."""
import logging
import re
from pathlib import Path
from typing import List, Optional

from ..repositories.worker_repository import WorkerRepository
from ..models.domain import Worker
from ..core.database import get_database

logger = logging.getLogger(__name__)


class WorkerService:
    """Service for managing workers."""
    
    def __init__(self, config):
        """Initialize service."""
        self.config = config
        self.db = get_database(config.paths.get('database', './receipts.db'))
        self.repository = WorkerRepository(self.db)
        self.workers_base_dir = Path('./workers')
        self.workers_base_dir.mkdir(exist_ok=True)
    
    def create_worker(self, nombre: str) -> Optional[Worker]:
        """
        Create a new worker with directory structure.
        
        Args:
            nombre: Worker name (alphanumeric only)
            
        Returns:
            Created worker or None if failed
            
        Raises:
            ValueError: If name is invalid or already exists
        """
        # Validate name format (alphanumeric only)
        if not re.match(r'^[a-zA-Z0-9]+$', nombre):
            raise ValueError("El nombre debe contener solo letras y números (sin espacios ni caracteres especiales)")
        
        # Create worker in database
        worker = self.repository.create(nombre)
        
        if worker:
            # Create base directory structure
            worker_dir = self.workers_base_dir / nombre
            worker_dir.mkdir(exist_ok=True)
            logger.info(f"Created worker directory: {worker_dir}")
        
        return worker
    
    def get_worker(self, worker_id: int) -> Optional[Worker]:
        """Get worker by ID."""
        return self.repository.get_by_id(worker_id)
    
    def get_worker_by_name(self, nombre: str) -> Optional[Worker]:
        """Get worker by name (case-insensitive)."""
        return self.repository.get_by_nombre(nombre)
    
    def list_workers(self, active_only: bool = False) -> List[Worker]:
        """
        List all workers.
        
        Args:
            active_only: If True, return only active workers
        """
        return self.repository.get_all(active_only=active_only)
    
    def get_all_workers(self, include_inactive: bool = False) -> List[Worker]:
        """
        Get all workers (alias for list_workers with inverted parameter).
        
        Args:
            include_inactive: If True, include inactive workers
        """
        return self.repository.get_all(active_only=not include_inactive)
    
    def deactivate_worker(self, worker_id: int) -> bool:
        """Deactivate a worker (soft delete)."""
        return self.repository.deactivate(worker_id)
    
    def activate_worker(self, worker_id: int) -> bool:
        """Activate a worker."""
        return self.repository.activate(worker_id)
