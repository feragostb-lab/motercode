"""Bank matching service - Algorithm for matching receipts to bank transactions."""
import logging
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime
from collections import defaultdict

from ..models.domain import Receipt, BankTransaction, Match, MatchType
from ..repositories.receipt_repository import ReceiptRepository
from ..repositories.bank_repository import BankRepository
from ..repositories.match_repository import MatchRepository
from ..repositories.ignored_repository import IgnoredRepository
from ..core.database import get_database

logger = logging.getLogger(__name__)


class BankMatchingService:
    """Service for matching receipts to bank transactions."""
    
    def __init__(self, config):
        """
        Initialize matching service.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.db = get_database(config.paths.get('database', './receipts.db'))
        self.receipt_repo = ReceiptRepository(self.db)
        self.bank_repo = BankRepository(self.db)
        self.match_repo = MatchRepository(self.db)
        self.ignored_repo = IgnoredRepository(self.db)
        
        # Get matching configuration
        matching_config = config.matching
        self.amount_tolerance = Decimal(str(matching_config.get('amount_tolerance', 0.02)))
        self.date_match_exact = matching_config.get('date_match_exact', True)
    
    def match_receipt_to_transactions(self, receipt: Receipt, 
                                     transactions: List[BankTransaction]) -> Match:
        """
        Find best match for a receipt among bank transactions.
        
        Args:
            receipt: Receipt to match
            transactions: List of bank transactions
            
        Returns:
            Match object with best match result
        """
        if not transactions:
            return Match(
                receipt_id=receipt.id,
                transaction_id=None,
                match_type=MatchType.NONE,
                confidence=0.0,
                is_conflict=False,
            )
        
        # Get unmatched transactions only
        unmatched_ids = {t.id for t in transactions if t.matched_receipt_id is None}
        
        # Find all matches
        matches = []
        for trans in transactions:
            # Skip if already matched (unless it's for checking conflicts)
            if trans.id not in unmatched_ids:
                continue
            
            date_match = self._dates_match(receipt.date, trans.date)
            amount_match = self._amounts_match(receipt.amount, trans.amount)
            
            # Determine match type
            if date_match and amount_match:
                match_type = MatchType.BOTH
            elif amount_match:
                match_type = MatchType.AMOUNT_ONLY
            elif date_match:
                match_type = MatchType.DATE_ONLY
            else:
                continue  # No match
            
            matches.append({
                'transaction_id': trans.id,
                'match_type': match_type,
                'confidence': self._calculate_confidence(match_type)
            })
        
        # Prioritize: both > amount > date
        if matches:
            matches.sort(key=lambda x: (
                x['match_type'] == MatchType.BOTH,
                x['match_type'] == MatchType.AMOUNT_ONLY,
                x['match_type'] == MatchType.DATE_ONLY,
                x['confidence']
            ), reverse=True)
            
            best = matches[0]
            
            return Match(
                receipt_id=receipt.id,
                transaction_id=best['transaction_id'],
                match_type=best['match_type'],
                confidence=best['confidence'],
                is_conflict=False,
            )
        
        # No match found
        return Match(
            receipt_id=receipt.id,
            transaction_id=None,
            match_type=MatchType.NONE,
            confidence=0.0,
            is_conflict=False,
        )
    
    def recalculate_all_matches(self) -> int:
        """
        Recalculate matches for all receipts.
        
        Returns:
            Number of matches created
        """
        # Clear existing matches
        self.match_repo.clear_all()
        
        # Clear all matched_receipt_id from bank transactions
        # This is important because we're recalculating from scratch
        for transaction in self.bank_repo.get_all():
            if transaction.matched_receipt_id is not None:
                self.bank_repo.update_match(transaction.id, None)
                # Also clear any stored receipt type
                self.bank_repo.update_receipt_type(transaction.id, None)
        
        # Get all receipts and transactions
        receipts = self.receipt_repo.get_all()
        transactions = self.bank_repo.get_all()
        
        if not transactions:
            logger.warning("No bank transactions available for matching")
            return 0
        
        # Create matches for each receipt
        created_count = 0
        for receipt in receipts:
            # Skip receipts without date or amount
            if not receipt.date or not receipt.amount:
                continue
            
            match = self.match_receipt_to_transactions(receipt, transactions)
            
            # Only save if there's a match
            if match.transaction_id is not None:
                self.match_repo.create(match)
                
                # Update bank transaction with matched receipt
                self.bank_repo.update_match(match.transaction_id, receipt.id)
                # Persist receipt type on transaction for table visibility
                self.bank_repo.update_receipt_type(match.transaction_id, receipt.receipt_type)
                created_count += 1
        
        # Detect and mark conflicts
        conflicts = self.detect_conflicts()
        if conflicts:
            logger.info(f"Detected {len(conflicts)} conflicts during matching")
        
        logger.info(f"Created {created_count} matches for {len(receipts)} receipts")
        return created_count
    
    def update_match_after_edit(self, receipt_id: int) -> Optional[Match]:
        """
        Recalculate match for a single receipt after editing.
        
        Args:
            receipt_id: Receipt ID
            
        Returns:
            Updated Match object or None
        """
        receipt = self.receipt_repo.get_by_id(receipt_id)
        if not receipt:
            return None
        
        # Delete old match
        self.match_repo.delete_by_receipt_id(receipt_id)
        
        # Find new match
        transactions = self.bank_repo.get_all()
        new_match = self.match_receipt_to_transactions(receipt, transactions)
        
        # Save new match
        if new_match.transaction_id is not None:
            created = self.match_repo.create(new_match)
            # Update stored match and type
            receipt = self.receipt_repo.get_by_id(receipt_id)
            if receipt:
                self.bank_repo.update_match(new_match.transaction_id, receipt.id)
                self.bank_repo.update_receipt_type(new_match.transaction_id, receipt.receipt_type)
            return created
        
        return new_match
    
    def detect_conflicts(self) -> Dict[int, List[int]]:
        """
        Detect conflicts (multiple receipts matching same transaction).
        
        Also detects duplicate receipts (same date and amount).
        
        Returns:
            Dictionary of conflicts: {transaction_id: [receipt_ids]}
        """
        conflicts = {}
        
        # Group by transaction_id
        trans_to_receipts = defaultdict(list)
        
        receipts = self.receipt_repo.get_all()
        for receipt in receipts:
            match = self.match_repo.get_by_receipt_id(receipt.id)
            if match and match.transaction_id:
                trans_to_receipts[match.transaction_id].append(receipt.id)
        
        # Find conflicts (transaction with multiple receipts)
        for trans_id, receipt_ids in trans_to_receipts.items():
            if len(receipt_ids) > 1:
                conflicts[trans_id] = receipt_ids
                
                # Mark as conflict in database
                for receipt_id in receipt_ids:
                    match = self.match_repo.get_by_receipt_id(receipt_id)
                    if match and not match.is_conflict:
                        match.is_conflict = True
                        self.match_repo.update(match)
        
        # Also detect duplicate receipts (same date and amount)
        receipt_groups = defaultdict(list)
        for receipt in receipts:
            if receipt.date and receipt.amount:
                key = (receipt.date.date(), receipt.amount)
                receipt_groups[key].append(receipt.id)
        
        # Mark duplicate receipts as conflicts
        for key, receipt_ids in receipt_groups.items():
            if len(receipt_ids) > 1:
                for receipt_id in receipt_ids:
                    match = self.match_repo.get_by_receipt_id(receipt_id)
                    if match and not match.is_conflict:
                        match.is_conflict = True
                        self.match_repo.update(match)
        
        # Recompute conflict flags considering ignored and accepted receipts
        self.recompute_conflict_flags()
        
        return conflicts
    
    def recompute_conflict_flags(self):
        """
        Recompute is_conflict flags for all matches based on current active receipts.
        Clears the flag when only one active receipt remains, sets it when multiple exist.
        """
        # Get all ignored receipt IDs
        ignored_ids = self.ignored_repo.get_all_ignored_ids()
        
        # Group receipts by transaction_id
        trans_to_active = defaultdict(list)
        all_matches = self.match_repo.get_all()
        
        for match in all_matches:
            # Skip ignored receipts
            if match.receipt_id in ignored_ids:
                continue
            # Skip accepted conflicts (already resolved)
            if match.conflict_accepted:
                continue
            # Only consider matches with a transaction
            if match.transaction_id:
                trans_to_active[match.transaction_id].append(match.receipt_id)
        
        # Update conflict flags based on active count per transaction
        for match in all_matches:
            if match.transaction_id:
                active_count = len(trans_to_active.get(match.transaction_id, []))
                is_active = match.receipt_id in trans_to_active.get(match.transaction_id, [])
                
                # Set conflict if multiple active, clear if single or none
                should_be_conflict = is_active and active_count > 1
                
                if match.is_conflict != should_be_conflict:
                    match.is_conflict = should_be_conflict
                    self.match_repo.update(match)
        
        # Also handle duplicate receipts (same date and amount)
        receipts = self.receipt_repo.get_all()
        date_amount_to_active = defaultdict(list)
        
        for receipt in receipts:
            # Skip ignored
            if receipt.id in ignored_ids:
                continue
            # Skip accepted conflicts
            match = self.match_repo.get_by_receipt_id(receipt.id)
            if match and match.conflict_accepted:
                continue
            # Group by date+amount
            if receipt.date and receipt.amount:
                key = (receipt.date.date(), receipt.amount)
                date_amount_to_active[key].append(receipt.id)
        
        # Update conflict flags for duplicate groups
        for receipt in receipts:
            if receipt.date and receipt.amount:
                key = (receipt.date.date(), receipt.amount)
                active_count = len(date_amount_to_active.get(key, []))
                is_active = receipt.id in date_amount_to_active.get(key, [])
                match = self.match_repo.get_by_receipt_id(receipt.id)
                
                if match:
                    should_be_conflict = is_active and active_count > 1
                    
                    if match.is_conflict != should_be_conflict:
                        match.is_conflict = should_be_conflict
                        self.match_repo.update(match)
    
    def get_conflicting_receipts(self, receipt_id: int) -> List[int]:
        """
        Get list of other receipt IDs that conflict with the given receipt.
        Excludes ignored receipts and accepted conflicts from the conflict list.
        
        Args:
            receipt_id: Receipt ID to check for conflicts
            
        Returns:
            List of conflicting receipt IDs (excluding the given receipt_id, ignored, and accepted)
        """
        conflicting_ids = []
        
        receipt = self.receipt_repo.get_by_id(receipt_id)
        if not receipt:
            return conflicting_ids
        
        match = self.match_repo.get_by_receipt_id(receipt_id)
        if not match or not match.is_conflict:
            return conflicting_ids
        
        # Get all ignored receipt IDs
        ignored_ids = self.ignored_repo.get_all_ignored_ids()
        
        # Check for receipts matching same transaction
        if match.transaction_id:
            all_receipts = self.receipt_repo.get_all()
            for other_receipt in all_receipts:
                if other_receipt.id == receipt_id:
                    continue
                # Skip ignored receipts
                if other_receipt.id in ignored_ids:
                    continue
                other_match = self.match_repo.get_by_receipt_id(other_receipt.id)
                # Skip accepted conflicts (already resolved)
                if other_match and other_match.conflict_accepted:
                    continue
                if other_match and other_match.transaction_id == match.transaction_id:
                    conflicting_ids.append(other_receipt.id)
        
        # Check for duplicate receipts (same date and amount)
        if receipt.date and receipt.amount:
            all_receipts = self.receipt_repo.get_all()
            for other_receipt in all_receipts:
                if other_receipt.id == receipt_id:
                    continue
                # Skip ignored receipts
                if other_receipt.id in ignored_ids:
                    continue
                # Skip accepted conflicts
                other_match = self.match_repo.get_by_receipt_id(other_receipt.id)
                if other_match and other_match.conflict_accepted:
                    continue
                if (other_receipt.date and other_receipt.amount and
                    other_receipt.date.date() == receipt.date.date() and
                    other_receipt.amount == receipt.amount):
                    if other_receipt.id not in conflicting_ids:
                        conflicting_ids.append(other_receipt.id)
        
        return conflicting_ids
    
    def _dates_match(self, date1: Optional[datetime], date2: Optional[datetime]) -> bool:
        """Check if two dates match based on configuration."""
        if not date1 or not date2:
            return False
        
        if self.date_match_exact:
            return date1.date() == date2.date()
        else:
            # Allow ±1 day difference
            diff = abs((date1.date() - date2.date()).days)
            return diff <= 1
    
    def _amounts_match(self, amount1: Optional[Decimal], amount2: Optional[Decimal]) -> bool:
        """
        Check if two amounts match within tolerance percentage.
        
        Args:
            amount1: First amount
            amount2: Second amount
            
        Returns:
            True if amounts match within tolerance
        """
        if not amount1 or not amount2:
            return False
        
        # Calculate percentage difference
        # Use the larger amount as base to avoid division issues
        base = max(abs(amount1), abs(amount2))
        if base == 0:
            return amount1 == amount2
        
        diff = abs(amount1 - amount2)
        percentage_diff = diff / base
        
        return percentage_diff <= self.amount_tolerance
    
    def _calculate_confidence(self, match_type: MatchType) -> float:
        """Calculate confidence score based on match type."""
        confidence_map = {
            MatchType.BOTH: 1.0,
            MatchType.AMOUNT_ONLY: 0.7,
            MatchType.DATE_ONLY: 0.5,
            MatchType.NONE: 0.0,
        }
        return confidence_map.get(match_type, 0.0)
    
    # ===== ROC SKINCARE: Multi-worker CSV upload =====
    
    def upload_csv_for_period(self, worker_id: int, period_id: int, csv_file_path: str) -> int:
        """
        Upload and process CSV for a specific period.
        
        Replaces any previous transactions for this period.
        
        Args:
            worker_id: Worker ID
            period_id: Period ID
            csv_file_path: Path to CSV file to upload
            
        Returns:
            Number of transactions loaded
            
        Raises:
            ValueError: If file doesn't exist or processing fails
        """
        from pathlib import Path
        import pandas as pd
        from ..repositories.period_repository import PeriodRepository
        from ..repositories.worker_repository import WorkerRepository
        from ..utils.file_helpers import get_period_paths
        from ..utils.formatters import parse_date_spanish
        
        # Validate file exists
        if not Path(csv_file_path).exists():
            raise ValueError(f"Archivo CSV no encontrado: {csv_file_path}")
        
        # Get worker and period info
        worker_repo = WorkerRepository(self.db)
        period_repo = PeriodRepository(self.db)
        
        worker = worker_repo.get_by_id(worker_id)
        if not worker:
            raise ValueError(f"Trabajador con ID {worker_id} no existe")
        
        period = period_repo.get_by_id(period_id)
        if not period:
            raise ValueError(f"Periodo con ID {period_id} no existe")
        
        # Generate timestamped filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        paths = get_period_paths(worker.nombre, period.month_year)
        paths['csv'].mkdir(parents=True, exist_ok=True)
        
        new_csv_filename = f"banco_{timestamp}.csv"
        new_csv_path = paths['csv'] / new_csv_filename
        
        # Copy CSV to period directory
        import shutil
        shutil.copy2(csv_file_path, new_csv_path)
        logger.info(f"CSV copied to {new_csv_path}")
        
        # Read and process CSV (assuming Spanish date format dd/mm/yyyy)
        try:
            skiprows = 13 if csv_file_path.endswith('.xlsx') else 0
            df = pd.read_excel(csv_file_path, skiprows=skiprows) if csv_file_path.endswith('.xlsx') else pd.read_csv(csv_file_path)
            
            # Clean column names
            df.columns = ['fecha', 'descripcion', 'metodo', 'importe']
            
            # CRITICAL: Preserve original CSV row number BEFORE filtering
            # For Excel: skiprows=13 means first data row is line 14 (1-indexed in Excel)
            # For CSV: first data row is line 2 (after header)
            df['csv_row_number'] = range(skiprows + 2, skiprows + 2 + len(df))
            
            # Remove rows with no date
            df = df[df['fecha'].notna()].copy()
            
            # Filter out summary rows
            summary_keywords = [
                'MES', 'SITUACIÓN', 'SITUACION', 
                'DICIEMBRE', 'ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO',
                'JUNIO', 'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE'
            ]
            pattern = '|'.join(summary_keywords)
            df = df[~df['fecha'].astype(str).str.upper().str.contains(pattern, na=False)].copy()
            
            # Parse dates - try Spanish format first (dd/mm/yyyy), then other formats
            df['fecha_procesada'] = pd.to_datetime(df['fecha'], format='%d/%m/%Y', errors='coerce')
            if df['fecha_procesada'].isna().all():
                # Try dot separator
                df['fecha_procesada'] = pd.to_datetime(df['fecha'], format='%d.%m.%Y', errors='coerce')
            
            # Remove rows with invalid dates
            df = df[df['fecha_procesada'].notna()].copy()
            
            # Process amounts
            def process_amount(amount):
                if pd.isna(amount):
                    return None
                if isinstance(amount, (int, float)):
                    return Decimal(str(abs(float(amount))))
                amount_str = str(amount).replace(',', '.').replace('-', '').strip()
                try:
                    return Decimal(str(abs(float(amount_str))))
                except:
                    return None
            
            df['importe_procesado'] = df['importe'].apply(process_amount)
            df = df[df['importe_procesado'].notna()].copy()
            
        except Exception as e:
            logger.error(f"Error processing CSV: {e}")
            raise ValueError(f"Error al procesar archivo CSV: {e}")
        
        # Delete previous transactions for this period
        deleted_count = self.bank_repo.clear_by_period(period_id)
        logger.info(f"Deleted {deleted_count} previous transactions for period {period_id}")
        
        # Create transaction objects with explicit IDs from CSV row order
        transactions = []
        upload_date = datetime.now().isoformat()
        
        # CRITICAL: Preserve ORIGINAL CSV row number in csv_row_number field
        # id will be auto-generated to avoid conflicts between periods
        for _, row in df.iterrows():
            transaction = BankTransaction(
                csv_row_number=row['csv_row_number'],  # Preserve original CSV row number
                date=row['fecha_procesada'].to_pydatetime(),
                amount=row['importe_procesado'],
                description=str(row['descripcion']) if pd.notna(row['descripcion']) else None,
                reference=str(row['metodo']) if pd.notna(row['metodo']) else None,
                matched_receipt_id=None
            )
            transactions.append(transaction)
        
        # Bulk insert with worker/period info
        count = self.bank_repo.bulk_create_with_period(
            transactions, 
            worker_id, 
            period_id, 
            str(new_csv_path), 
            upload_date
        )
        
        # Update period with CSV info
        period_repo.update_csv_upload(period_id, str(new_csv_path), upload_date)
        
        logger.info(f"Loaded {count} transactions for period {period_id}")
        
        # Run re-matching for all receipts in this period
        self._rematch_period(period_id)
        
        return count
    
    def _rematch_period(self, period_id: int):
        """
        Re-run matching for all receipts in a period.
        
        Args:
            period_id: Period ID to rematch
        """
        # Get all receipts for this period
        receipts = self.receipt_repo.get_by_period(period_id)
        
        # Get all transactions for this period
        transactions = self.bank_repo.get_by_period(period_id)
        
        logger.info(f"Re-matching {len(receipts)} receipts with {len(transactions)} transactions for period {period_id}")
        
        # Clear existing matches for this period's receipts
        for receipt in receipts:
            self.match_repo.delete_by_receipt_id(receipt.id)
        
        # Perform matching
        for receipt in receipts:
            match = self.match_receipt_to_transactions(receipt, transactions)
            if match:
                self.match_repo.create(match)
        
        logger.info(f"Re-matching completed for period {period_id}")

