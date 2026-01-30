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


class PeriodStatus(Enum):
    """Estado de un periodo."""
    ACTIVE = "active"
    CLOSED = "closed"


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
    worker_id: Optional[int] = None
    period_id: Optional[int] = None
    
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
            'worker_id': self.worker_id,
            'period_id': self.period_id,
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
    csv_row_number: Optional[int] = None  # Original row number in CSV/Excel file
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
            'csv_row_number': self.csv_row_number,
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
    period_id: Optional[int] = None
    
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
            'period_id': self.period_id,
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


@dataclass
class Worker:
    """Representa un trabajador."""
    id: Optional[int] = None
    nombre: str = ""
    activo: bool = True
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert worker to dictionary."""
        return {
            'id': self.id,
            'nombre': self.nombre,
            'activo': self.activo,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class Period:
    """Representa un periodo mensual de un trabajador."""
    id: Optional[int] = None
    worker_id: int = 0
    month_year: str = ""  # Formato: "MMYYYY"
    status: PeriodStatus = PeriodStatus.ACTIVE
    is_processing_active: bool = False
    csv_last_upload: Optional[datetime] = None
    csv_file_path: Optional[str] = None
    closed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert period to dictionary."""
        return {
            'id': self.id,
            'worker_id': self.worker_id,
            'month_year': self.month_year,
            'status': self.status.value if self.status else None,
            'is_processing_active': self.is_processing_active,
            'csv_last_upload': self.csv_last_upload.isoformat() if self.csv_last_upload else None,
            'csv_file_path': self.csv_file_path,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class PeriodClosure:
    """Representa un cierre de periodo."""
    id: Optional[int] = None
    period_id: int = 0
    closure_date: Optional[datetime] = None
    export_path: str = ""
    reopened_at: Optional[datetime] = None
    reopen_reason: Optional[str] = None
    stats_snapshot: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert period closure to dictionary."""
        return {
            'id': self.id,
            'period_id': self.period_id,
            'closure_date': self.closure_date.isoformat() if self.closure_date else None,
            'export_path': self.export_path,
            'reopened_at': self.reopened_at.isoformat() if self.reopened_at else None,
            'reopen_reason': self.reopen_reason,
            'stats_snapshot': self.stats_snapshot,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class PeriodStats:
    """Estadísticas de un periodo."""
    period_id: int = 0
    total_receipts: int = 0
    processed_receipts: int = 0
    matched_receipts: int = 0
    unmatched_receipts: int = 0
    conflict_receipts: int = 0
    conflicts: int = 0
    total_transactions: int = 0
    matched_transactions: int = 0
    unmatched_transactions: int = 0
    unprocessed_images: int = 0
    has_csv: bool = False
    csv_upload_date: Optional[datetime] = None
    can_close: bool = False
    blocking_reasons: list = field(default_factory=list)


@dataclass
class FieldDefinition:
    """Definition of a field for OCR extraction."""
    key: str
    required: str  # "yes" or "no"
    question: str
    field_type: str  # "text", "number", "date", "boolean"
    help_text: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'key': self.key,
            'required': self.required,
            'question': self.question,
            'field_type': self.field_type,
            'help_text': self.help_text
        }


@dataclass
class ReceiptTypeDefinition:
    """Configuration for a receipt type with detection rules."""
    name: str
    enabled: bool
    direct_indicator: Dict[str, Any]  # {field_key, question, weight}
    auxiliary_fields: Dict[str, Dict[str, Any]]  # {field_key: {question, weight, type, help}}
    keyword_weights: Dict[str, int]  # {keyword: weight}
    normalized_type: str = ""  # Normalized type name
    gl_account: str = ""  # GL Account number (xxxxxxxx format)
    
    def calculate_max_score(self) -> int:
        """Calculate maximum possible score for this type."""
        # Direct indicator weight
        max_score = self.direct_indicator.get('weight', 0)
        
        # Sum of all auxiliary field weights
        for field_config in self.auxiliary_fields.values():
            max_score += field_config.get('weight', 0)
        
        # Sum of all keyword weights
        for keyword_weight in self.keyword_weights.values():
            max_score += keyword_weight
        
        return max_score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'enabled': self.enabled,
            'direct_indicator': self.direct_indicator,
            'auxiliary_fields': self.auxiliary_fields,
            'keyword_weights': self.keyword_weights,
            'normalized_type': self.normalized_type,
            'gl_account': self.gl_account,
            'max_score': self.calculate_max_score()
        }


@dataclass
class TypeScoreDetail:
    """Detailed scoring information for a receipt type."""
    type_name: str
    total_score: int
    max_score: int
    primary_score: int
    secondary_score: int
    tertiary_score: int
    matched_fields: list  # [{field: str, weight: int, tier: str}]
    has_test_samples: bool = False
    avg_confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'type_name': self.type_name,
            'total_score': self.total_score,
            'max_score': self.max_score,
            'primary_score': self.primary_score,
            'secondary_score': self.secondary_score,
            'tertiary_score': self.tertiary_score,
            'matched_fields': self.matched_fields,
            'has_test_samples': self.has_test_samples,
            'avg_confidence': self.avg_confidence,
            'confidence_percentage': (self.total_score / self.max_score * 100) if self.max_score > 0 else 0
        }
