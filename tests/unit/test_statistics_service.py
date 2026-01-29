"""Unit tests for StatisticsService."""
import pytest
from decimal import Decimal
from datetime import datetime, date
from src.services.statistics_service import StatisticsService
from src.models.domain import Receipt, BankTransaction, Match, MatchType, ProcessingStatus
from src.core.config import get_config
from src.repositories.receipt_repository import ReceiptRepository
from src.repositories.bank_repository import BankRepository
from src.repositories.match_repository import MatchRepository
from src.repositories.ignored_repository import IgnoredRepository


@pytest.fixture
def stats_service(test_config):
    """Create a StatisticsService with temporary database."""
    return StatisticsService(test_config)


@pytest.fixture
def sample_receipts(stats_service):
    """Create sample receipts for testing."""
    repo = stats_service.receipt_repo
    
    receipts = [
        Receipt(
            id=1,
            file_path="taxi1.jpg",
            receipt_type="taxis",
            date=date(2026, 1, 15),
            amount=Decimal("25.50"),
            processing_successful=True
        ),
        Receipt(
            id=2,
            file_path="comida1.jpg",
            receipt_type="comidas",
            date=date(2026, 1, 16),
            amount=Decimal("45.00"),
            processing_successful=True
        ),
        Receipt(
            id=3,
            file_path="hotel1.jpg",
            receipt_type="hoteles",
            date=date(2026, 1, 17),
            amount=Decimal("120.00"),
            processing_successful=True
        ),
        Receipt(
            id=4,
            file_path="taxi2.jpg",
            receipt_type="taxis",
            date=date(2026, 1, 18),
            amount=Decimal("18.30"),
            processing_successful=True
        ),
        Receipt(
            id=5,
            file_path="failed.jpg",
            receipt_type="otros",
            date=None,
            amount=None,
            processing_successful=False
        ),
    ]
    
    for receipt in receipts:
        repo.create(receipt)
    
    return receipts


@pytest.fixture
def sample_bank_transactions(stats_service):
    """Create sample bank transactions for testing."""
    repo = stats_service.bank_repo
    
    transactions = [
        BankTransaction(
            id=1,
            date=date(2026, 1, 15),
            amount=Decimal("25.50"),
            description="TAXI SERVICE",
            matched_receipt_id=1  # Matched
        ),
        BankTransaction(
            id=2,
            date=date(2026, 1, 16),
            amount=Decimal("45.00"),
            description="RESTAURANT",
            matched_receipt_id=2  # Matched
        ),
        BankTransaction(
            id=3,
            date=date(2026, 1, 17),
            amount=Decimal("120.00"),
            description="HOTEL",
            matched_receipt_id=None  # Unmatched
        ),
        BankTransaction(
            id=4,
            date=date(2026, 1, 20),
            amount=Decimal("75.00"),
            description="UNKNOWN",
            matched_receipt_id=None  # Unmatched
        ),
    ]
    
    for transaction in transactions:
        repo.create(transaction)
    
    return transactions


@pytest.fixture
def sample_matches(stats_service, sample_receipts, sample_bank_transactions):
    """Create sample matches for testing."""
    repo = stats_service.match_repo
    
    matches = [
        Match(
            id=1,
            receipt_id=1,
            transaction_id=1,
            match_type=MatchType.BOTH,
            is_conflict=False,
            conflict_accepted=False
        ),
        Match(
            id=2,
            receipt_id=2,
            transaction_id=2,
            match_type=MatchType.AMOUNT_ONLY,
            is_conflict=False,
            conflict_accepted=False
        ),
        Match(
            id=3,
            receipt_id=3,
            transaction_id=3,
            match_type=MatchType.BOTH,
            is_conflict=True,
            conflict_accepted=True  # Conflict accepted
        ),
        Match(
            id=4,
            receipt_id=4,
            transaction_id=3,
            match_type=MatchType.BOTH,
            is_conflict=True,
            conflict_accepted=False  # Conflict unresolved
        ),
    ]
    
    for match in matches:
        repo.create(match)
    
    return matches


@pytest.fixture
def sample_ignored(stats_service, sample_receipts):
    """Create sample ignored receipts."""
    repo = stats_service.ignored_repo
    
    # Ignore receipt 5
    ignored = repo.ignore_receipt(receipt_id=5, reason="Test ignore")
    
    return [ignored]


class TestReceiptStatistics:
    """Test receipt statistics."""
    
    def test_total_count(self, stats_service, sample_receipts):
        """Test total receipt count."""
        stats = stats_service.get_receipt_statistics()
        assert stats['total_count'] == 5
    
    def test_total_amount(self, stats_service, sample_receipts):
        """Test total amount calculation."""
        stats = stats_service.get_receipt_statistics()
        expected = Decimal("25.50") + Decimal("45.00") + Decimal("120.00") + Decimal("18.30")
        assert stats['total_amount'] == expected
    
    def test_avg_amount(self, stats_service, sample_receipts):
        """Test average amount calculation."""
        stats = stats_service.get_receipt_statistics()
        total = Decimal("25.50") + Decimal("45.00") + Decimal("120.00") + Decimal("18.30")
        expected = total / 5  # Divided by all receipts, including failed
        assert stats['avg_amount'] == expected
    
    def test_success_rate(self, stats_service, sample_receipts):
        """Test success rate calculation."""
        stats = stats_service.get_receipt_statistics()
        # 4 successful out of 5
        assert stats['success_rate'] == 80.0
    
    def test_by_type_breakdown(self, stats_service, sample_receipts):
        """Test breakdown by receipt type."""
        stats = stats_service.get_receipt_statistics()
        by_type = stats['by_type']
        
        assert 'taxis' in by_type
        assert by_type['taxis']['count'] == 2
        assert by_type['taxis']['total_amount'] == Decimal("25.50") + Decimal("18.30")
        
        assert 'comidas' in by_type
        assert by_type['comidas']['count'] == 1
        assert by_type['comidas']['total_amount'] == Decimal("45.00")
        
        assert 'hoteles' in by_type
        assert by_type['hoteles']['count'] == 1
        assert by_type['hoteles']['total_amount'] == Decimal("120.00")
        
        assert 'otros' in by_type
        assert by_type['otros']['count'] == 1
        assert by_type['otros']['total_amount'] == Decimal("0.00")  # Failed receipt has no amount
    
    def test_date_range(self, stats_service, sample_receipts):
        """Test date range calculation."""
        stats = stats_service.get_receipt_statistics()
        date_range = stats['date_range']
        
        assert date_range is not None
        # Compare dates only (service might return datetime)
        assert date_range['earliest'].date() == date(2026, 1, 15) if hasattr(date_range['earliest'], 'date') else date_range['earliest'] == date(2026, 1, 15)
        assert date_range['latest'].date() == date(2026, 1, 18) if hasattr(date_range['latest'], 'date') else date_range['latest'] == date(2026, 1, 18)
    
    def test_empty_receipts(self, stats_service):
        """Test statistics with no receipts."""
        stats = stats_service.get_receipt_statistics()
        
        assert stats['total_count'] == 0
        assert stats['by_type'] == {}
        assert stats['success_rate'] == 0.0
        assert stats['total_amount'] == Decimal('0.00')
        assert stats['avg_amount'] == Decimal('0.00')
        assert stats['date_range'] is None


class TestBankStatistics:
    """Test bank transaction statistics."""
    
    def test_total_transactions(self, stats_service, sample_bank_transactions):
        """Test total bank transactions count."""
        stats = stats_service.get_bank_statistics()
        assert stats['total_transactions'] == 4
    
    def test_matched_count(self, stats_service, sample_bank_transactions):
        """Test matched transactions count."""
        stats = stats_service.get_bank_statistics()
        # 2 transactions are matched (ids 1 and 2)
        assert stats['matched_count'] == 2
    
    def test_unmatched_count(self, stats_service, sample_bank_transactions):
        """Test unmatched transactions count."""
        stats = stats_service.get_bank_statistics()
        # 2 transactions are unmatched (ids 3 and 4)
        assert stats['unmatched_count'] == 2
    
    def test_match_rate(self, stats_service, sample_bank_transactions):
        """Test match rate calculation."""
        stats = stats_service.get_bank_statistics()
        # 2 matched out of 4 = 50%
        assert stats['match_rate'] == 50.0
    
    def test_total_amount(self, stats_service, sample_bank_transactions):
        """Test total amount calculation."""
        stats = stats_service.get_bank_statistics()
        expected = Decimal("25.50") + Decimal("45.00") + Decimal("120.00") + Decimal("75.00")
        assert stats['total_amount'] == expected
    
    def test_matched_amount(self, stats_service, sample_bank_transactions):
        """Test matched amount calculation."""
        stats = stats_service.get_bank_statistics()
        expected = Decimal("25.50") + Decimal("45.00")  # Only matched transactions
        assert stats['matched_amount'] == expected
    
    def test_unmatched_amount(self, stats_service, sample_bank_transactions):
        """Test unmatched amount calculation."""
        stats = stats_service.get_bank_statistics()
        expected = Decimal("120.00") + Decimal("75.00")  # Only unmatched transactions
        assert stats['unmatched_amount'] == expected
    
    def test_empty_transactions(self, stats_service):
        """Test statistics with no transactions."""
        stats = stats_service.get_bank_statistics()
        
        assert stats['total_transactions'] == 0
        assert stats['matched_count'] == 0
        assert stats['unmatched_count'] == 0
        assert stats['match_rate'] == 0.0


class TestMatchingStatistics:
    """Test matching statistics."""
    
    def test_total_matches(self, stats_service, sample_matches):
        """Test total matches count."""
        stats = stats_service.get_matching_statistics()
        assert stats['total_matches'] == 4
    
    def test_match_type_breakdown(self, stats_service, sample_matches):
        """Test match type breakdown."""
        stats = stats_service.get_matching_statistics()
        breakdown = stats['match_type_breakdown']
        
        assert breakdown['both'] == 3  # Matches 1, 3, 4
        assert breakdown['amount_only'] == 1  # Match 2
        assert breakdown['date_only'] == 0
        assert breakdown['none'] == 0
    
    def test_conflicts_count(self, stats_service, sample_matches):
        """Test conflicts count."""
        stats = stats_service.get_matching_statistics()
        # Matches 3 and 4 are conflicts
        assert stats['conflicts'] == 2
    
    def test_accepted_conflicts(self, stats_service, sample_matches):
        """Test accepted conflicts count."""
        stats = stats_service.get_matching_statistics()
        # Only match 3 has conflict_accepted=True
        assert stats['accepted_conflicts'] == 1
    
    def test_unresolved_conflicts(self, stats_service, sample_matches):
        """Test unresolved conflicts count."""
        stats = stats_service.get_matching_statistics()
        # Match 4 is unresolved conflict
        assert stats['unresolved_conflicts'] == 1
    
    def test_match_success_rate(self, stats_service, sample_matches):
        """Test match success rate."""
        stats = stats_service.get_matching_statistics()
        # both (3) + amount_only (1) = 4 successful out of 4 total = 100%
        assert stats['match_success_rate'] == 100.0
    
    def test_empty_matches(self, stats_service):
        """Test statistics with no matches."""
        stats = stats_service.get_matching_statistics()
        
        assert stats['total_matches'] == 0
        assert stats['conflicts'] == 0
        assert stats['accepted_conflicts'] == 0
        assert stats['unresolved_conflicts'] == 0
        assert stats['match_success_rate'] == 0.0


class TestDashboardSummary:
    """Test comprehensive dashboard summary."""
    
    def test_summary_structure(self, stats_service, sample_receipts, 
                              sample_bank_transactions, sample_matches, sample_ignored):
        """Test that summary contains all required sections."""
        summary = stats_service.get_dashboard_summary()
        
        assert 'receipts' in summary
        assert 'bank' in summary
        assert 'matching' in summary
        assert 'breakdown' in summary
        assert 'ignored_count' in summary
    
    def test_ignored_count(self, stats_service, sample_receipts, sample_ignored):
        """Test ignored receipts count."""
        summary = stats_service.get_dashboard_summary()
        assert summary['ignored_count'] == 1
    
    def test_all_stats_present(self, stats_service, sample_receipts,
                               sample_bank_transactions, sample_matches):
        """Test that all statistics are correctly populated."""
        summary = stats_service.get_dashboard_summary()
        
        # Receipt stats
        assert summary['receipts']['total_count'] == 5
        assert summary['receipts']['success_rate'] == 80.0
        
        # Bank stats
        assert summary['bank']['total_transactions'] == 4
        assert summary['bank']['matched_count'] == 2
        assert summary['bank']['unmatched_count'] == 2
        
        # Matching stats
        assert summary['matching']['total_matches'] == 4
        assert summary['matching']['conflicts'] == 2
        assert summary['matching']['accepted_conflicts'] == 1


class TestExpectedDashboardValues:
    """Test specific values that should appear in the dashboard."""
    
    def test_matched_should_exist(self, stats_service, sample_matches):
        """Verify 'matched' data appears in statistics (user reported missing)."""
        stats = stats_service.get_matching_statistics()
        assert stats['total_matches'] > 0, "Should have matched receipts"
    
    def test_ignored_should_exist(self, stats_service, sample_ignored):
        """Verify 'ignored' count appears in statistics (user reported missing)."""
        summary = stats_service.get_dashboard_summary()
        assert summary['ignored_count'] > 0, "Should have ignored receipts"
    
    def test_conflicts_accepted_should_exist(self, stats_service, sample_matches):
        """Verify 'conflicts accepted' appears in statistics (user reported missing)."""
        stats = stats_service.get_matching_statistics()
        assert stats['accepted_conflicts'] > 0, "Should have accepted conflicts"
    
    def test_match_distribution_should_exist(self, stats_service, sample_matches):
        """Verify match distribution data exists (user reported 'No match data available')."""
        stats = stats_service.get_matching_statistics()
        breakdown = stats['match_type_breakdown']
        
        assert breakdown is not None, "Match type breakdown should exist"
        assert 'both' in breakdown
        assert 'amount_only' in breakdown
        assert 'date_only' in breakdown
        assert 'none' in breakdown
        
        # Should have at least some matches
        total = sum(breakdown.values())
        assert total > 0, "Should have match distribution data"
    
    def test_detailed_breakdown_should_have_data(self, stats_service, sample_receipts):
        """Verify detailed breakdown by type has data (user reported issues)."""
        stats = stats_service.get_receipt_statistics()
        by_type = stats['by_type']
        
        assert by_type is not None, "Breakdown by type should exist"
        assert len(by_type) > 0, "Should have receipt types"
        
        # Check that each type has required fields
        for receipt_type, data in by_type.items():
            assert 'count' in data, f"Type {receipt_type} should have count"
            assert 'total_amount' in data, f"Type {receipt_type} should have total_amount"
