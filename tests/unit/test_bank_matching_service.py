"""Unit tests for BankMatchingService - TDD approach (Día 2)."""
import pytest
from datetime import datetime
from decimal import Decimal

from src.services.bank_matching_service import BankMatchingService
from src.models.domain import Receipt, BankTransaction, Match, MatchType
from src.repositories.receipt_repository import ReceiptRepository
from src.repositories.bank_repository import BankRepository
from src.repositories.match_repository import MatchRepository
from src.repositories.ignored_repository import IgnoredRepository


# ========================================
# TDD CYCLE 1: Exact Match Algorithm
# ========================================

class TestExactMatching:
    """Test exact match detection (date + amount)."""
    
    def test_exact_match_date_and_amount(self, mock_config, test_db):
        """🔴 RED: Should create exact match when date and amount match."""
        service = BankMatchingService(mock_config)
        service.db = test_db
        service.receipt_repo = ReceiptRepository(test_db)
        service.bank_repo = BankRepository(test_db)
        service.match_repo = MatchRepository(test_db)
        service.ignored_repo = IgnoredRepository(test_db)
        
        # Create receipt
        receipt = Receipt(
            file_path='test.jpg',
            receipt_type='taxis',
            date=datetime(2025, 1, 15),
            amount=Decimal('12.34')
        )
        receipt = service.receipt_repo.create(receipt)
        
        # Create matching transaction
        transaction = BankTransaction(
            date=datetime(2025, 1, 15),
            amount=Decimal('12.34'),
            description='TAXI BARCELONA',
            reference='TXN001'
        )
        transaction = service.bank_repo.create(transaction)
        
        # Test matching
        match = service.match_receipt_to_transactions(receipt, [transaction])
        
        assert match is not None
        assert match.receipt_id == receipt.id
        assert match.transaction_id == transaction.id
        assert match.match_type == MatchType.BOTH
        assert match.confidence == 1.0
    
    def test_exact_match_with_tolerance(self, mock_config, test_db):
        """🔴 RED: Should match within amount tolerance (2%)."""
        service = BankMatchingService(mock_config)
        service.db = test_db
        service.receipt_repo = ReceiptRepository(test_db)
        service.bank_repo = BankRepository(test_db)
        service.match_repo = MatchRepository(test_db)
        service.ignored_repo = IgnoredRepository(test_db)
        
        # Receipt: 100.00
        receipt = Receipt(
            file_path='test.jpg',
            receipt_type='restaurante',
            date=datetime(2025, 1, 15),
            amount=Decimal('100.00')
        )
        receipt = service.receipt_repo.create(receipt)
        
        # Transaction: 101.50 (1.5% difference - within 2% tolerance)
        transaction = BankTransaction(
            date=datetime(2025, 1, 15),
            amount=Decimal('101.50'),
            description='RESTAURANT',
            reference='TXN002'
        )
        transaction = service.bank_repo.create(transaction)
        
        match = service.match_receipt_to_transactions(receipt, [transaction])
        
        assert match.transaction_id == transaction.id
        assert match.match_type == MatchType.BOTH
    
    def test_no_match_outside_tolerance(self, mock_config, test_db):
        """🔴 RED: Should match DATE_ONLY if dates match but amount is outside tolerance."""
        service = BankMatchingService(mock_config)
        service.db = test_db
        service.receipt_repo = ReceiptRepository(test_db)
        service.bank_repo = BankRepository(test_db)
        
        # Receipt: 100.00
        receipt = Receipt(
            file_path='test.jpg',
            receipt_type='factura',
            date=datetime(2025, 1, 15),
            amount=Decimal('100.00')
        )
        receipt = service.receipt_repo.create(receipt)
        
        # Transaction: 105.00 (5% difference - outside 2% tolerance)
        # But same date, so should match DATE_ONLY
        transaction = BankTransaction(
            date=datetime(2025, 1, 15),
            amount=Decimal('105.00'),
            description='INVOICE PAYMENT',
            reference='TXN003'
        )
        transaction = service.bank_repo.create(transaction)
        
        match = service.match_receipt_to_transactions(receipt, [transaction])
        
        # Should match by date only (not by both)
        assert match.transaction_id == transaction.id
        assert match.match_type == MatchType.DATE_ONLY
        assert match.confidence == 0.5


# ========================================
# TDD CYCLE 2: Recalculate All Matches
# ========================================

class TestRecalculateMatches:
    """Test recalculate_all_matches() functionality."""
    
    def test_recalculate_creates_new_matches(self, mock_config, test_db):
        """🔴 RED: Should create new matches for all receipts."""
        service = BankMatchingService(mock_config)
        service.db = test_db
        service.receipt_repo = ReceiptRepository(test_db)
        service.bank_repo = BankRepository(test_db)
        service.match_repo = MatchRepository(test_db)
        service.ignored_repo = IgnoredRepository(test_db)
        
        # Create 3 receipts
        r1 = service.receipt_repo.create(Receipt(
            file_path='r1.jpg',
            receipt_type='taxis',
            date=datetime(2025, 1, 15),
            amount=Decimal('12.34')
        ))
        
        r2 = service.receipt_repo.create(Receipt(
            file_path='r2.jpg',
            receipt_type='restaurante',
            date=datetime(2025, 1, 16),
            amount=Decimal('45.00')
        ))
        
        r3 = service.receipt_repo.create(Receipt(
            file_path='r3.jpg',
            receipt_type='parking',
            date=datetime(2025, 1, 17),
            amount=Decimal('8.00')
        ))
        
        # Create 3 matching transactions
        t1 = service.bank_repo.create(BankTransaction(
            date=datetime(2025, 1, 15),
            amount=Decimal('12.34'),
            description='TAXI',
            reference='TXN001'
        ))
        
        t2 = service.bank_repo.create(BankTransaction(
            date=datetime(2025, 1, 16),
            amount=Decimal('45.00'),
            description='RESTAURANT',
            reference='TXN002'
        ))
        
        t3 = service.bank_repo.create(BankTransaction(
            date=datetime(2025, 1, 17),
            amount=Decimal('8.00'),
            description='PARKING',
            reference='TXN003'
        ))
        
        # Recalculate
        count = service.recalculate_all_matches()
        
        assert count == 3
        
        # Verify all matches created
        all_matches = service.match_repo.get_all()
        assert len(all_matches) == 3
    
    def test_recalculate_returns_count(self, mock_config, test_db):
        """🔴 RED: Should return number of matches created."""
        service = BankMatchingService(mock_config)
        service.db = test_db
        service.receipt_repo = ReceiptRepository(test_db)
        service.bank_repo = BankRepository(test_db)
        service.match_repo = MatchRepository(test_db)
        service.ignored_repo = IgnoredRepository(test_db)
        
        # Create 2 receipts, 1 transaction (only 1 can match)
        service.receipt_repo.create(Receipt(
            file_path='r1.jpg',
            receipt_type='taxis',
            date=datetime(2025, 1, 15),
            amount=Decimal('12.34')
        ))
        
        service.receipt_repo.create(Receipt(
            file_path='r2.jpg',
            receipt_type='restaurante',
            date=datetime(2025, 1, 16),
            amount=Decimal('45.00')
        ))
        
        service.bank_repo.create(BankTransaction(
            date=datetime(2025, 1, 15),
            amount=Decimal('12.34'),
            description='TAXI',
            reference='TXN001'
        ))
        
        count = service.recalculate_all_matches()
        
        assert count == 1  # Only first receipt matched
