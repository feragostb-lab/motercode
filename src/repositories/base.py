"""Base repository with common CRUD operations."""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List
import sqlite3
import json
from datetime import datetime

T = TypeVar('T')


class BaseRepository(Generic[T], ABC):
    """Base repository for database operations."""
    
    def __init__(self, db):
        """
        Initialize repository.
        
        Args:
            db: Database instance
        """
        self.db = db
    
    @abstractmethod
    def _row_to_model(self, row: sqlite3.Row) -> T:
        """Convert database row to model instance."""
        pass
    
    @abstractmethod
    def _model_to_dict(self, model: T) -> dict:
        """Convert model instance to dictionary for database."""
        pass
    
    def _serialize_json_field(self, value) -> Optional[str]:
        """Serialize Python object to JSON string."""
        if value is None:
            return None
        return json.dumps(value, default=str)
    
    def _deserialize_json_field(self, value: Optional[str]) -> Optional[dict]:
        """Deserialize JSON string to Python object."""
        if not value:
            return None
        try:
            return json.loads(value)
        except:
            return None
    
    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        """Parse ISO format datetime string."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except:
            return None
    
    def _format_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Format datetime to ISO string."""
        if value is None:
            return None
        return value.isoformat()
