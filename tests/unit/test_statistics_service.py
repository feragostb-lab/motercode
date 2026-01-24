"""Test suite for StatisticsService - TDD approach."""
import pytest
from decimal import Decimal
from datetime import datetime
from src.services.statistics_service import StatisticsService
from src.models.domain import Receipt, BankTransaction, Match, MatchType, IgnoredReceipt


class TestReceiptStatistics:
    """Test receipt statistics generation."""
    
    def test_empty_statistics(self, test_config):
        """Test statistics with no receipts."""
        service = StatisticsService(test_config)
        stats = service.get_receipt_statistics()
        
        assert stats['total_count'] == 0
        assert stats['by_type'] == {}
        assert stats['success_rate'] == 0.0
        assert stats['total_amount'] == Decimal('0.00')
        assert stats['avg_amount'] == Decimal('0.00')
        assert stats['date_range'] is None
    
    def test_single_receipt_statistics(self, test_config, receipt_repo):
        """Test statistics with one receipt."""
        service = StatisticsService(test_config)
        
        # Create receipt
        receipt = receipt_repo.create(Receipt(
            file_path='result/test.jpg',
            receipt_type='taxis',
            date=datetime(2025, 1, 15),
            amount=Decimal('25.50'),
            processing_successful=True
        ))
        
        stats = service.get_receipt_statistics()
        
        assert stats['total_count'] == 1
        assert stats['successful_count'] == 1
        assert stats['success_rate'] == 100.0
        assert stats['total_amount'] == Decimal('25.50')
        assert stats['avg_amount'] == Decimal('25.50')
        assert 'taxis' in stats['by_type']
        assert stats['by_type']['taxis']['count'] == 1
        assert stats['by_type']['taxis']['total_amount'] == Decimal('25.50')
    
    def test_multiple_receipts_by_type(self, test_config, receipt_repo):
        """Test statistics with multiple receipt types."""
        service = StatisticsService(test_config)
        
        # Create different types
        receipt_repo.create(Receipt(
            file_path='result/taxi1.jpg',
            receipt_type='taxis',
            date=datetime(2025, 1, 1),
            amount=Decimal('10.00'),
            processing_successful=True
        ))
        receipt_repo.create(Receipt(
            file_path='result/taxi2.jpg',
            receipt_type='taxis',
            date=datetime(2025, 1, 2),
            amount=Decimal('20.00'),
            processing_successful=True
        ))
        receipt_repo.create(Receipt(
            file_path='result/meal1.jpg',
            receipt_type='comidas',
            date=datetime(2025, 1, 3),
            amount=Decimal('50.00'),
            processing_successful=True
        ))
        
        stats = service.get_receipt_statistics()
        
        assert stats['total_count'] == 3
        assert stats['total_amount'] == Decimal('80.00')
        assert stats['avg_amount'] == Decimal('80.00') / 3
        assert stats['by_type']['taxis']['count'] == 2
        assert stats['by_type']['taxis']['total_amount'] == Decimal('30.00')
        assert stats['by_type']['comidas']['count'] == 1
        assert stats['by_type']['comidas']['total_amount'] == Decimal('50.00')
    
    def test_success_rate_calculation(self, test_config, receipt_repo):
        """Test success rate with mixed processing results."""
        service = StatisticsService(test_config)
        
        # Create receipts with different success status
        receipt_repo.create(Receipt(
            file_path='result/success1.jpg',
            receipt_type='taxis',
            amount=Decimal('10.00'),
            processing_successful=True
        ))
        receipt_repo.create(Receipt(
            file_path='result/success2.jpg',
            receipt_type='comidas',
            amount=Decimal('20.00'),
            processing_successful=True
        ))
        receipt_repo.create(Receipt(
            file_path='result/failed.jpg',
            receipt_type='taxis',
            amount=Decimal('15.00'),
            processing_successful=False,
            error_message='OCR failed'
        ))
        
        stats = service.get_receipt_statistics()
        
        assert stats['total_count'] == 3
        assert stats['successful_count'] == 2
        assert stats['success_rate'] == 66.67  # 2/3 * 100, rounded to 2 decimals
    
    def test_date_range_calculation(self, test_config, receipt_repo):
        """Test date range calculation."""
        service = StatisticsService(test_config)
        
        # Create receipts with different dates
        receipt_repo.create(Receipt(
            file_path='result/old.jpg',
            receipt_type='taxis',
            date=datetime(2024, 6, 1),
            amount=Decimal('10.00')
        ))
        receipt_repo.create(Receipt(
            file_path='result/recent.jpg',
            receipt_type='comidas',
            date=datetime(2025, 1, 15),
            amount=Decimal('20.00')
        ))
        receipt_repo.create(Receipt(
            file_path='result/newest.jpg',
            receipt_type='taxis',
            date=datetime(2025, 2, 1),
            amount=Decimal('15.00')
        ))
        
        stats = service.get_receipt_statistics()
        
        assert stats['date_range'] is not None
        assert stats['date_range']['earliest'] == datetime(2024, 6, 1)
        assert stats['date_range']['latest'] == datetime(2025, 2, 1)


class TestBankStatistics:
    """Test bank transaction statistics."""
    
    def test_empty_bank_statistics(self, test_config):
        """Test with no bank transactions."""
        service = StatisticsService(test_config)
        stats = service.get_bank_statistics()
        
        assert stats['total_transactions'] == 0
        assert stats['matched_count'] == 0
        assert stats['unmatched_count'] == 0
        assert stats['match_rate'] == 0.0
    
    def test_unmatched_transactions(self, test_config, bank_repo):
        """Test statistics with only unmatched transactions."""
        service = StatisticsService(test_config)
        
        # Create unmatched transactions
        bank_repo.create(BankTransaction(
            date=datetime(2025, 1, 1),
            amount=Decimal('10.00'),
            description='Taxi payment'
        ))
        bank_repo.create(BankTransaction(
            date=datetime(2025, 1, 2),
            amount=Decimal('20.00'),
            description='Restaurant'
        ))
        
        stats = service.get_bank_statistics()
        
        assert stats['total_transactions'] == 2
        assert stats['matched_count'] == 0
        assert stats['unmatched_count'] == 2
        assert stats['match_rate'] == 0.0
        assert stats['total_amount'] == Decimal('30.00')
        assert stats['unmatched_amount'] == Decimal('30.00')
    
    def test_matched_transactions(self, test_config, bank_repo, receipt_repo):
        """Test statistics with matched transactions."""
        service = StatisticsService(test_config)
        
        # Create receipt and transaction
        receipt = receipt_repo.create(Receipt(
            file_path='result/test.jpg',
            receipt_type='taxis',
            date=datetime(2025, 1, 1),
            amount=Decimal('10.00')
        ))
        
        bank_repo.create(BankTransaction(
            date=datetime(2025, 1, 1),
            amount=Decimal('10.00'),
            description='Taxi',
            matched_receipt_id=receipt.id
        ))
        bank_repo.create(BankTransaction(
            date=datetime(2025, 1, 2),
            amount=Decimal('20.00'),
            description='Unmatched'
        ))
        
        stats = service.get_bank_statistics()
        
        assert stats['total_transactions'] == 2
        assert stats['matched_count'] == 1
        assert stats['unmatched_count'] == 1
        assert stats['match_rate'] == 50.0
        assert stats['matched_amount'] == Decimal('10.00')
        assert stats['unmatched_amount'] == Decimal('20.00')


class TestMatchingStatistics:
    """Test matching statistics."""
    
    def test_empty_matching_statistics(self, test_config):
        """Test with no matches."""
        service = StatisticsService(test_config)
        stats = service.get_matching_statistics()
        
        assert stats['total_matches'] == 0
        assert stats['conflicts'] == 0
        assert stats['match_success_rate'] == 0.0
    
    def test_match_type_breakdown(self, test_config, receipt_repo, match_repo):
        """Test match type breakdown."""
        service = StatisticsService(test_config)
        
        # Create receipts with different match types
        r1 = receipt_repo.create(Receipt(
            file_path='result/exact.jpg',
            receipt_type='taxis',
            amount=Decimal('10.00')
        ))
        r2 = receipt_repo.create(Receipt(
            file_path='result/amount_only.jpg',
            receipt_type='comidas',
            amount=Decimal('20.00')
        ))
        r3 = receipt_repo.create(Receipt(
            file_path='result/unmatched.jpg',
            receipt_type='taxis',
            amount=Decimal('30.00')
        ))
        
        # Create matches
        match_repo.create(Match(
            receipt_id=r1.id,
            transaction_id=1,
            match_type=MatchType.BOTH,
            confidence=1.0
        ))
        match_repo.create(Match(
            receipt_id=r2.id,
            transaction_id=2,
            match_type=MatchType.AMOUNT_ONLY,
            confidence=0.8
        ))
        match_repo.create(Match(
            receipt_id=r3.id,
            match_type=MatchType.NONE,
            confidence=0.0
        ))
        
        stats = service.get_matching_statistics()
        
        assert stats['total_matches'] == 3
        assert stats['match_type_breakdown']['both'] == 1
        assert stats['match_type_breakdown']['amount_only'] == 1
        assert stats['match_type_breakdown']['none'] == 1
        assert stats['match_success_rate'] == 66.67  # (1 both + 1 amount) / 3 * 100
    
    def test_conflict_tracking(self, test_config, receipt_repo, match_repo):
        """Test conflict statistics."""
        service = StatisticsService(test_config)
        
        # Create receipts with conflicts
        r1 = receipt_repo.create(Receipt(
            file_path='result/conflict1.jpg',
            receipt_type='taxis',
            amount=Decimal('10.00')
        ))
        r2 = receipt_repo.create(Receipt(
            file_path='result/conflict2.jpg',
            receipt_type='taxis',
            amount=Decimal('10.00')
        ))
        r3 = receipt_repo.create(Receipt(
            file_path='result/normal.jpg',
            receipt_type='comidas',
            amount=Decimal('20.00')
        ))
        
        # Create matches with conflicts
        match_repo.create(Match(
            receipt_id=r1.id,
            transaction_id=1,
            match_type=MatchType.BOTH,
            confidence=1.0,
            is_conflict=True,
            conflict_accepted=False
        ))
        match_repo.create(Match(
            receipt_id=r2.id,
            transaction_id=1,
            match_type=MatchType.BOTH,
            confidence=1.0,
            is_conflict=True,
            conflict_accepted=True
        ))
        match_repo.create(Match(
            receipt_id=r3.id,
            transaction_id=2,
            match_type=MatchType.BOTH,
            confidence=1.0,
            is_conflict=False
        ))
        
        stats = service.get_matching_statistics()
        
        assert stats['total_matches'] == 3
        assert stats['conflicts'] == 2
        assert stats['accepted_conflicts'] == 1
        assert stats['unresolved_conflicts'] == 1


class TestDashboardSummary:
    """Test comprehensive dashboard summary."""
    
    def test_complete_dashboard_summary(self, test_config, receipt_repo, bank_repo, match_repo, ignored_repo):
        """Test full dashboard summary generation."""
        service = StatisticsService(test_config)
        
        # Create sample data
        receipt = receipt_repo.create(Receipt(
            file_path='result/test.jpg',
            receipt_type='taxis',
            date=datetime(2025, 1, 1),
            amount=Decimal('10.00'),
            processing_successful=True
        ))
        
        bank_repo.create(BankTransaction(
            date=datetime(2025, 1, 1),
            amount=Decimal('10.00'),
            matched_receipt_id=receipt.id
        ))
        
        match_repo.create(Match(
            receipt_id=receipt.id,
            transaction_id=1,
            match_type=MatchType.BOTH,
            confidence=1.0
        ))
        
        ignored_repo.ignore_receipt(receipt.id, "Test ignore")
        
        # Get summary
        summary = service.get_dashboard_summary()
        
        # Verify structure
        assert 'receipts' in summary
        assert 'bank' in summary
        assert 'matching' in summary
        assert 'breakdown' in summary
        assert 'ignored_count' in summary
        
        # Verify data
        assert summary['receipts']['total_count'] == 1
        assert summary['bank']['total_transactions'] == 1
        assert summary['matching']['total_matches'] == 1
        assert summary['ignored_count'] == 1
