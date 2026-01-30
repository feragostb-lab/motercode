"""Receipt service - Business logic for receipt management."""
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
import shutil
import os

from ..models.domain import Receipt, TypeScoreDetail
from ..repositories.receipt_repository import ReceiptRepository
from ..utils.formatters import generar_nombre_archivo, deduplicar_nombre_archivo
from ..core.database import get_database
from ..services.config_service import ConfigService

logger = logging.getLogger(__name__)


class ReceiptService:
    """Service for receipt business logic."""
    
    def __init__(self, config):
        """
        Initialize receipt service.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.db = get_database(config.paths.get('database', './receipts.db'))
        self.repository = ReceiptRepository(self.db)
        # output_dir is now determined dynamically based on active worker/period
        self.config_service = ConfigService()
        
        # Cached scoring rules (invalidated on config reload)
        self._cached_scoring_rules: Optional[Dict[str, Any]] = None
    
    def create_receipt(self, receipt: Receipt) -> Receipt:
        """
        Create a new receipt.
        
        Args:
            receipt: Receipt model
            
        Returns:
            Created receipt with ID
        """
        return self.repository.create(receipt)
    
    def get_receipt_by_id(self, receipt_id: int) -> Optional[Receipt]:
        """Get receipt by ID."""
        return self.repository.get_by_id(receipt_id)
    
    def get_all_receipts(self) -> List[Receipt]:
        """Get all receipts."""
        return self.repository.get_all()
    
    def update_receipt_type(self, receipt_id: int, new_type: str) -> bool:
        """
        Update receipt type and rename file accordingly.
        
        Args:
            receipt_id: Receipt ID
            new_type: New receipt type
            
        Returns:
            True if successful, False otherwise
        """
        receipt = self.repository.get_by_id(receipt_id)
        if not receipt:
            logger.error(f"Receipt {receipt_id} not found")
            return False
        
        # If type hasn't changed, nothing to do
        if receipt.receipt_type == new_type:
            return True
        
        # Get old file path
        old_path = Path(receipt.file_path)
        if not old_path.exists():
            logger.error(f"File {receipt.file_path} not found")
            return False
        
        # Generate new filename with new type
        extension = old_path.suffix
        new_name = generar_nombre_archivo(
            receipt.date,
            receipt.amount,
            new_type,
            extension=""
        )
        new_name = f"{new_name}{extension}"
        
        # Check for duplicates and deduplicate
        existing_files = self.get_existing_filenames(str(old_path.parent))
        new_name = deduplicar_nombre_archivo(new_name, existing_files)
        
        # Rename physical file
        new_path = old_path.parent / new_name
        try:
            old_path.rename(new_path)
            
            # Update database
            receipt.receipt_type = new_type
            receipt.file_path = str(new_path)
            return self.repository.update(receipt)
            
        except Exception as e:
            logger.error(f"Error renaming file: {e}")
            # Try to revert if possible
            if new_path.exists() and not old_path.exists():
                try:
                    new_path.rename(old_path)
                except:
                    pass
            return False
    
    def update_receipt_date(self, receipt_id: int, new_date: datetime) -> bool:
        """
        Update receipt date and rename file accordingly.
        
        Args:
            receipt_id: Receipt ID
            new_date: New date (can be datetime or date object)
            
        Returns:
            True if successful, False otherwise
        """
        receipt = self.repository.get_by_id(receipt_id)
        if not receipt:
            logger.error(f"Receipt {receipt_id} not found")
            return False
        
        # Convert to date for comparison if needed
        from datetime import date as date_type
        new_date_obj = new_date if isinstance(new_date, date_type) and not isinstance(new_date, datetime) else (new_date.date() if isinstance(new_date, datetime) else new_date)
        receipt_date_obj = receipt.date.date() if isinstance(receipt.date, datetime) else receipt.date
        
        # If date hasn't changed, nothing to do
        if receipt.date and receipt_date_obj == new_date_obj:
            return True
        
        # Get old file path
        old_path = Path(receipt.file_path)
        if not old_path.exists():
            logger.error(f"File {receipt.file_path} not found")
            return False
        
        # Generate new filename with new date
        # Convert date to datetime if needed
        from datetime import date as date_type
        date_for_filename = datetime.combine(new_date, datetime.min.time()) if isinstance(new_date, date_type) and not isinstance(new_date, datetime) else new_date
        
        extension = old_path.suffix
        new_name = generar_nombre_archivo(
            date_for_filename,
            receipt.amount,
            receipt.receipt_type,
            extension=""
        )
        new_name = f"{new_name}{extension}"
        
        # Check for duplicates and deduplicate
        existing_files = self.get_existing_filenames(str(old_path.parent))
        new_name = deduplicar_nombre_archivo(new_name, existing_files)
        
        # Rename physical file
        new_path = old_path.parent / new_name
        try:
            old_path.rename(new_path)
            
            # Update database (convert to datetime if needed)
            receipt.date = date_for_filename
            receipt.file_path = str(new_path)
            return self.repository.update(receipt)
            
        except Exception as e:
            logger.error(f"Error renaming file: {e}")
            # Try to revert if possible
            if new_path.exists() and not old_path.exists():
                try:
                    new_path.rename(old_path)
                except:
                    pass
            return False
    
    def update_receipt_amount(self, receipt_id: int, new_amount: Decimal) -> bool:
        """
        Update receipt amount and rename file accordingly.
        
        Args:
            receipt_id: Receipt ID
            new_amount: New amount
            
        Returns:
            True if successful, False otherwise
        """
        receipt = self.repository.get_by_id(receipt_id)
        if not receipt:
            logger.error(f"Receipt {receipt_id} not found")
            return False
        
        # If amount hasn't changed, nothing to do
        if receipt.amount == new_amount:
            return True
        
        # Get old file path
        old_path = Path(receipt.file_path)
        if not old_path.exists():
            logger.error(f"File {receipt.file_path} not found")
            return False
        
        # Generate new filename with new amount
        extension = old_path.suffix
        new_name = generar_nombre_archivo(
            receipt.date,
            new_amount,
            receipt.receipt_type,
            extension=""
        )
        new_name = f"{new_name}{extension}"
        
        # Check for duplicates and deduplicate
        existing_files = self.get_existing_filenames(str(old_path.parent))
        new_name = deduplicar_nombre_archivo(new_name, existing_files)
        
        # Rename physical file
        new_path = old_path.parent / new_name
        try:
            old_path.rename(new_path)
            
            # Update database
            receipt.amount = new_amount
            receipt.file_path = str(new_path)
            return self.repository.update(receipt)
            
        except Exception as e:
            logger.error(f"Error renaming file: {e}")
            # Try to revert if possible
            if new_path.exists() and not old_path.exists():
                try:
                    new_path.rename(old_path)
                except:
                    pass
            return False
    
    def update_receipt_description(self, receipt_id: int, new_description: str) -> bool:
        """
        Update receipt description.
        
        Args:
            receipt_id: Receipt ID
            new_description: New description text
            
        Returns:
            True if successful, False otherwise
        """
        receipt = self.repository.get_by_id(receipt_id)
        if not receipt:
            logger.error(f"Receipt {receipt_id} not found")
            return False
        
        # Update description
        receipt.description = new_description
        return self.repository.update(receipt)
    
    def _compile_scoring_rules(self) -> Dict[str, Any]:
        """
        Compile scoring rules from configuration for caching.
        
        Returns:
            Dictionary of compiled scoring rules per type
        """
        enabled_types = self.config_service.get_enabled_type_definitions()
        
        scoring_rules = {}
        for type_def in enabled_types:
            scoring_rules[type_def.name] = {
                'direct_indicator': type_def.direct_indicator,
                'auxiliary_fields': type_def.auxiliary_fields,
                'keyword_weights': type_def.keyword_weights,
                'max_score': type_def.calculate_max_score()
            }
        
        logger.info(f"Compiled scoring rules for {len(scoring_rules)} enabled types")
        return scoring_rules
    
    def invalidate_scoring_cache(self):
        """Invalidate cached scoring rules (call after config reload)."""
        self._cached_scoring_rules = None
        logger.info("Scoring rules cache invalidated")
    
    def deduce_receipt_type(self, extracted_data: Dict[str, Any]) -> str:
        """
        Deduce receipt type from extracted data using config-driven scoring.
        Uses cached scoring rules for performance - invalidated on config reload.
        
        Args:
            extracted_data: Dictionary with extracted OCR data
            
        Returns:
            Deduced receipt type name or 'Otros'
        """
        if not extracted_data:
            return 'Otros'
        
        # Ensure scoring rules are compiled and cached
        if self._cached_scoring_rules is None:
            self._cached_scoring_rules = self._compile_scoring_rules()
        
        # Convert all keys to lowercase for case-insensitive matching
        data_lower = {k.lower(): v for k, v in extracted_data.items() if v}
        
        # Calculate scores for all types
        type_scores = {}
        
        for type_name, rules in self._cached_scoring_rules.items():
            score = 0
            
            # PRIMARY SCORE: Direct indicator field presence
            direct_indicator = rules.get('direct_indicator', {})
            if direct_indicator:
                field_key = direct_indicator.get('field_key', '').lower()
                weight = direct_indicator.get('weight', 0)
                if field_key in data_lower:
                    score += weight
            
            # SECONDARY SCORE: Auxiliary field presence
            auxiliary_fields = rules.get('auxiliary_fields', {})
            for field_key, field_config in auxiliary_fields.items():
                if field_key.lower() in data_lower:
                    score += field_config.get('weight', 0)
            
            # TERTIARY SCORE: Keyword matching in extracted field keys
            keyword_weights = rules.get('keyword_weights', {})
            for keyword, weight in keyword_weights.items():
                keyword_lower = keyword.lower()
                # Check if keyword appears in any extracted field key
                if any(keyword_lower in key for key in data_lower.keys()):
                    score += weight
            
            type_scores[type_name] = score
        
        # Find type with highest score
        if type_scores:
            max_score = max(type_scores.values())
            if max_score > 0:
                # Get all types with max score (tie-breaking by YAML order)
                for type_name in self._cached_scoring_rules.keys():
                    if type_scores.get(type_name, 0) == max_score:
                        logger.debug(f"Deduced type '{type_name}' with score {max_score}")
                        logger.debug(f"All scores: {type_scores}")
                        return type_name
        
        # Fallback: Check for generic invoice indicators
        if 'nif' in data_lower or 'cif' in data_lower or 'numero_factura' in data_lower:
            logger.debug("No type match, falling back to 'Otros' (found invoice indicators)")
            return 'Otros'
        
        # Last resort: text-based keyword search in values
        all_text = ' '.join(str(v).lower() for v in data_lower.values() if v)
        
        # Try to match against keyword_weights from all types
        for type_name, rules in self._cached_scoring_rules.items():
            keyword_weights = rules.get('keyword_weights', {})
            for keyword in keyword_weights.keys():
                if keyword.lower() in all_text:
                    logger.debug(f"Text fallback matched type '{type_name}' via keyword '{keyword}'")
                    return type_name
        
        logger.debug(f"No type match found, defaulting to 'Otros'. Scores: {type_scores}")
        return 'Otros'
    
    def calculate_type_scores_detailed(self, extracted_data: Dict[str, Any]) -> Dict[str, TypeScoreDetail]:
        """
        Calculate detailed scoring breakdown for all types.
        Used for live preview in admin UI.
        
        Args:
            extracted_data: Dictionary with extracted OCR data
            
        Returns:
            Dictionary mapping type name to TypeScoreDetail object
        """
        if not extracted_data:
            return {}
        
        # Ensure scoring rules are compiled and cached
        if self._cached_scoring_rules is None:
            self._cached_scoring_rules = self._compile_scoring_rules()
        
        # Convert all keys to lowercase for case-insensitive matching
        data_lower = {k.lower(): v for k, v in extracted_data.items() if v}
        
        detailed_scores = {}
        
        for type_name, rules in self._cached_scoring_rules.items():
            primary_score = 0
            secondary_score = 0
            tertiary_score = 0
            matched_fields = []
            
            # PRIMARY: Direct indicator
            direct_indicator = rules.get('direct_indicator', {})
            if direct_indicator:
                field_key = direct_indicator.get('field_key', '').lower()
                weight = direct_indicator.get('weight', 0)
                if field_key in data_lower:
                    primary_score += weight
                    matched_fields.append({
                        'field': field_key,
                        'weight': weight,
                        'tier': 'PRIMARY'
                    })
            
            # SECONDARY: Auxiliary fields
            auxiliary_fields = rules.get('auxiliary_fields', {})
            for field_key, field_config in auxiliary_fields.items():
                if field_key.lower() in data_lower:
                    weight = field_config.get('weight', 0)
                    secondary_score += weight
                    matched_fields.append({
                        'field': field_key,
                        'weight': weight,
                        'tier': 'SECONDARY'
                    })
            
            # TERTIARY: Keywords
            keyword_weights = rules.get('keyword_weights', {})
            for keyword, weight in keyword_weights.items():
                keyword_lower = keyword.lower()
                if any(keyword_lower in key for key in data_lower.keys()):
                    tertiary_score += weight
                    matched_fields.append({
                        'field': f"keyword:{keyword}",
                        'weight': weight,
                        'tier': 'TERTIARY'
                    })
            
            total_score = primary_score + secondary_score + tertiary_score
            max_score = rules.get('max_score', 0)
            
            detail = TypeScoreDetail(
                type_name=type_name,
                total_score=total_score,
                max_score=max_score,
                primary_score=primary_score,
                secondary_score=secondary_score,
                tertiary_score=tertiary_score,
                matched_fields=matched_fields,
                has_test_samples=False,  # Will be set by admin UI
                avg_confidence=0.0  # Will be calculated by admin UI
            )
            
            detailed_scores[type_name] = detail
        
        return detailed_scores
    
    def update_receipt_type_simple(self, receipt_id: int, new_type: str) -> bool:
        """
        Update receipt type (simplified version without file renaming).
        
        Args:
            receipt_id: Receipt ID
            new_type: New receipt type
            
        Returns:
            True if successful, False otherwise
        """
        receipt = self.repository.get_by_id(receipt_id)
        if not receipt:
            logger.error(f"Receipt {receipt_id} not found")
            return False
        
        # Validate type
        valid_types = self.config.receipt_types
        if new_type not in valid_types:
            logger.error(f"Invalid receipt type: {new_type}")
            return False
        
        # Update receipt
        receipt.receipt_type = new_type
        return self.repository.update(receipt)
    
    def update_receipt_date_simple(self, receipt_id: int, new_date: datetime) -> bool:
        """
        Update receipt date (simplified version without file renaming).
        
        Args:
            receipt_id: Receipt ID
            new_date: New date
            
        Returns:
            True if successful, False otherwise
        """
        receipt = self.repository.get_by_id(receipt_id)
        if not receipt:
            logger.error(f"Receipt {receipt_id} not found")
            return False
        
        receipt.date = new_date
        return self.repository.update(receipt)
    
    def update_receipt_amount_simple(self, receipt_id: int, new_amount: Decimal) -> bool:
        """
        Update receipt amount (simplified version without file renaming).
        
        Args:
            receipt_id: Receipt ID
            new_amount: New amount
            
        Returns:
            True if successful, False otherwise
        """
        receipt = self.repository.get_by_id(receipt_id)
        if not receipt:
            logger.error(f"Receipt {receipt_id} not found")
            return False
        
        receipt.amount = new_amount
        return self.repository.update(receipt)
    
    def update_receipt_description(self, receipt_id: int, new_description: str) -> bool:
        """
        Update receipt description.
        
        Args:
            receipt_id: Receipt ID
            new_description: New description
            
        Returns:
            True if successful, False otherwise
        """
        receipt = self.repository.get_by_id(receipt_id)
        if not receipt:
            logger.error(f"Receipt {receipt_id} not found")
            return False
        
        receipt.description = new_description
        return self.repository.update(receipt)
    
    def rename_receipt_file(self, receipt: Receipt, new_filename: str) -> bool:
        """
        Rename physical receipt file and update database.
        
        Args:
            receipt: Receipt model
            new_filename: New filename
            
        Returns:
            True if successful, False otherwise
        """
        try:
            old_path = Path(receipt.file_path)
            new_path = old_path.parent / new_filename
            
            if old_path.exists():
                shutil.move(str(old_path), str(new_path))
                receipt.file_path = str(new_path)
                return self.repository.update(receipt)
            return False
            
        except Exception as e:
            logger.error(f"Error renaming file: {e}")
            return False
    
    def get_existing_filenames(self, directory: str) -> List[str]:
        """
        Get list of existing filenames in directory.
        
        Args:
            directory: Directory path
            
        Returns:
            List of filenames
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            return []
        return [f.name for f in dir_path.iterdir() if f.is_file()]
