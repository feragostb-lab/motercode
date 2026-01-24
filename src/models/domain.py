"""Domain models for the receipt processing system."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from decimal import Decimal


class ProcessingStatus(Enum):
    """Status of a processing queue item."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class MatchType(Enum):
    """Type of match between receipt and bank transaction."""
    NONE = "none"
    DATE_ONLY = "date"
    AMOUNT_ONLY = "amount"
    BOTH = "both"


@dataclass
class Receipt:
    """Represents a processed receipt."""
    id: Optional[int] = None
    file_path: str = ""
    original_filename: str = ""
    receipt_type: str = ""
    date: Optional[datetime] = None
    amount: Optional[Decimal] = None
    description: str = ""
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    processing_successful: bool = True
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert receipt to dictionary."""
        return {
            'id': self.id,
            'file_path': self.file_path,
            'original_filename': self.original_filename,
            'receipt_type': self.receipt_type,
            'date': self.date.isoformat() if self.date else None,
            'amount': str(self.amount) if self.amount else None,
            'description': self.description,
            'extracted_data': self.extracted_data,
            'processing_successful': self.processing_successful,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class BankTransaction:
    """Represents a bank transaction from Excel."""
    id: Optional[int] = None
    date: Optional[datetime] = None
    amount: Optional[Decimal] = None
    description: str = ""
    reference: str = ""
    receipt_type: str = ""
    matched_receipt_id: Optional[int] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert bank transaction to dictionary."""
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'amount': str(self.amount) if self.amount else None,
            'description': self.description,
            'reference': self.reference,
            'receipt_type': self.receipt_type,
            'matched_receipt_id': self.matched_receipt_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class Match:
    """Represents a match between a receipt and bank transaction."""
    id: Optional[int] = None
    receipt_id: int = 0
    transaction_id: Optional[int] = None
    match_type: MatchType = MatchType.NONE
    confidence: float = 0.0
    is_conflict: bool = False
    conflict_accepted: bool = False
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert match to dictionary."""
        return {
            'id': self.id,
            'receipt_id': self.receipt_id,
            'transaction_id': self.transaction_id,
            'match_type': self.match_type.value if self.match_type else None,
            'confidence': self.confidence,
            'is_conflict': self.is_conflict,
            'conflict_accepted': self.conflict_accepted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class ProcessingQueueItem:
    """Represents an item in the processing queue."""
    id: Optional[int] = None
    file_path: str = ""
    status: ProcessingStatus = ProcessingStatus.PENDING
    attempts: int = 0
    last_error: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert queue item to dictionary."""
        return {
            'id': self.id,
            'file_path': self.file_path,
            'status': self.status.value if self.status else None,
            'attempts': self.attempts,
            'last_error': self.last_error,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
        }


@dataclass
class ProcessorState:
    """Represents the current state of the processor."""
    id: int = 1  # Singleton
    is_running: bool = False
    is_paused: bool = False
    paused_at: Optional[datetime] = None
    last_processed_file: Optional[str] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert processor state to dictionary."""
        return {
            'id': self.id,
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'paused_at': self.paused_at.isoformat() if self.paused_at else None,
            'last_processed_file': self.last_processed_file,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class IgnoredReceipt:
    """Represents a receipt that has been marked as ignored."""
    id: Optional[int] = None
    receipt_id: int = 0
    ignored_at: Optional[datetime] = None
    reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ignored receipt to dictionary."""
        return {
            'id': self.id,
            'receipt_id': self.receipt_id,
            'ignored_at': self.ignored_at.isoformat() if self.ignored_at else None,
            'reason': self.reason,
        }
