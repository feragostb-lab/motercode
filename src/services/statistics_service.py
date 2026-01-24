"""Statistics service - Generate reports and aggregations."""
import logging
from typing import Dict, List, Any
from datetime import datetime
from decimal import Decimal

from ..repositories.receipt_repository import ReceiptRepository
from ..repositories.bank_repository import BankRepository
from ..repositories.match_repository import MatchRepository
from ..repositories.ignored_repository import IgnoredRepository
from ..core.database import get_database

logger = logging.getLogger(__name__)


class StatisticsService:
    """Service for generating statistics and reports."""
    
    def __init__(self, config):
        """
        Initialize statistics service.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.db = get_database(config.paths.get('database', './receipts.db'))
        self.receipt_repo = ReceiptRepository(self.db)
        self.bank_repo = BankRepository(self.db)
        self.match_repo = MatchRepository(self.db)
        self.ignored_repo = IgnoredRepository(self.db)
    
    def get_receipt_statistics(self) -> Dict[str, Any]:
        """
        Get overall receipt statistics.
        
        Returns:
            Dictionary with statistics
        """
        receipts = self.receipt_repo.get_all()
        
        if not receipts:
            return {
                'total_count': 0,
                'by_type': {},
                'success_rate': 0.0,
                'total_amount': Decimal('0.00'),
                'avg_amount': Decimal('0.00'),
                'date_range': None,
            }
        
        # Count by type and sum amounts
        type_stats = {}
        total_amount = Decimal('0.00')
        successful_count = 0
        dates = []
        
        for receipt in receipts:
            # Type breakdown
            receipt_type = receipt.receipt_type or 'unknown'
            if receipt_type not in type_stats:
                type_stats[receipt_type] = {'count': 0, 'total_amount': Decimal('0.00')}
            
            type_stats[receipt_type]['count'] += 1
            if receipt.amount:
                type_stats[receipt_type]['total_amount'] += receipt.amount
                total_amount += receipt.amount
            
            # Success tracking
            if receipt.processing_successful:
                successful_count += 1
            
            # Date range
            if receipt.date:
                dates.append(receipt.date)
        
        # Calculate success rate
        success_rate = (successful_count / len(receipts) * 100) if receipts else 0.0
        
        # Date range
        date_range = None
        if dates:
            date_range = {
                'earliest': min(dates),
                'latest': max(dates)
            }
        
        # Average amount
        avg_amount = total_amount / len(receipts) if receipts else Decimal('0.00')
        
        return {
            'total_count': len(receipts),
            'by_type': type_stats,
            'success_rate': round(success_rate, 2),
            'total_amount': total_amount,
            'avg_amount': avg_amount,
            'date_range': date_range,
            'successful_count': successful_count,
        }
    
    def get_bank_statistics(self) -> Dict[str, Any]:
        """
        Get bank transaction statistics.
        
        Returns:
            Dictionary with statistics
        """
        transactions = self.bank_repo.get_all()
        unmatched = self.bank_repo.get_unmatched()
        
        matched_count = len(transactions) - len(unmatched)
        
        # Calculate amounts
        total_amount = sum(t.amount for t in transactions if t.amount) or Decimal('0.00')
        matched_amount = sum(t.amount for t in transactions if t.amount and t.matched_receipt_id) or Decimal('0.00')
        unmatched_amount = sum(t.amount for t in unmatched if t.amount) or Decimal('0.00')
        
        return {
            'total_transactions': len(transactions),
            'matched_count': matched_count,
            'unmatched_count': len(unmatched),
            'match_rate': round((matched_count / len(transactions) * 100) if transactions else 0.0, 2),
            'total_amount': total_amount,
            'matched_amount': matched_amount,
            'unmatched_amount': unmatched_amount,
        }
    
    def get_matching_statistics(self) -> Dict[str, Any]:
        """
        Get matching statistics.
        
        Returns:
            Dictionary with statistics
        """
        receipts = self.receipt_repo.get_all()
        conflicts = self.match_repo.get_all_conflicts()
        
        # Count matches by type
        match_type_breakdown = {
            'both': 0,
            'amount_only': 0,
            'date_only': 0,
            'none': 0,
        }
        
        total_matches = 0
        conflict_count = 0
        accepted_conflicts = 0
        
        for receipt in receipts:
            match = self.match_repo.get_by_receipt_id(receipt.id)
            if match:
                total_matches += 1
                
                # Count by type
                if match.match_type.value == 'both':
                    match_type_breakdown['both'] += 1
                elif match.match_type.value == 'amount':
                    match_type_breakdown['amount_only'] += 1
                elif match.match_type.value == 'date':
                    match_type_breakdown['date_only'] += 1
                else:
                    match_type_breakdown['none'] += 1
                
                # Count conflicts
                if match.is_conflict:
                    conflict_count += 1
                    if match.conflict_accepted:
                        accepted_conflicts += 1
        
        # Calculate success rate (both + amount_only)
        successful_matches = match_type_breakdown['both'] + match_type_breakdown['amount_only']
        match_success_rate = (successful_matches / total_matches * 100) if total_matches else 0.0
        
        return {
            'total_matches': total_matches,
            'match_type_breakdown': match_type_breakdown,
            'conflicts': conflict_count,
            'accepted_conflicts': accepted_conflicts,
            'unresolved_conflicts': conflict_count - accepted_conflicts,
            'match_success_rate': round(match_success_rate, 2),
        }
    
    def get_breakdown_by_type(self) -> List[Dict[str, Any]]:
        """
        Get receipt breakdown by type.
        
        TODO: Implement from dashboard_gradio.py breakdown_por_tipo()
        - For each receipt type:
          - Count
          - Total amount
          - Average amount
          - Percentage of total
        
        Returns:
            List of type breakdowns
        """
        # TODO: Implement
        return []
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive dashboard summary.
        
        Combines all statistics for dashboard display.
        
        Returns:
            Dictionary with all statistics
        """
        return {
            'receipts': self.get_receipt_statistics(),
            'bank': self.get_bank_statistics(),
            'matching': self.get_matching_statistics(),
            'breakdown': self.get_breakdown_by_type(),
            'ignored_count': self.ignored_repo.count(),
        }
