"""Test suite for repositories."""
import pytest
from decimal import Decimal
from datetime import datetime

from src.models.domain import Receipt, ProcessingStatus


def test_receipt_repository_create(receipt_repo, sample_receipt):
    """Test creating a receipt."""
    created = receipt_repo.create(sample_receipt)
    
    assert created.id is not None
    assert created.file_path == sample_receipt.file_path
    assert created.amount == sample_receipt.amount


def test_receipt_repository_get_by_id(receipt_repo, sample_receipt):
    """Test retrieving receipt by ID."""
    created = receipt_repo.create(sample_receipt)
    retrieved = receipt_repo.get_by_id(created.id)
    
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.receipt_type == created.receipt_type


def test_receipt_repository_update(receipt_repo, sample_receipt):
    """Test updating a receipt."""
    created = receipt_repo.create(sample_receipt)
    
    # Update amount
    created.amount = Decimal('99.99')
    updated = receipt_repo.update(created)
    
    assert updated is True
    
    # Verify update
    retrieved = receipt_repo.get_by_id(created.id)
    assert retrieved.amount == Decimal('99.99')


def test_receipt_repository_delete(receipt_repo, sample_receipt):
    """Test deleting a receipt."""
    created = receipt_repo.create(sample_receipt)
    deleted = receipt_repo.delete(created.id)
    
    assert deleted is True
    
    # Verify deletion
    retrieved = receipt_repo.get_by_id(created.id)
    assert retrieved is None


def test_receipt_repository_get_by_type(receipt_repo):
    """Test filtering receipts by type."""
    # Create multiple receipts
    taxi1 = Receipt(file_path='taxi1.jpg', receipt_type='taxis', 
                    date=datetime.now(), amount=Decimal('10.00'))
    taxi2 = Receipt(file_path='taxi2.jpg', receipt_type='taxis',
                    date=datetime.now(), amount=Decimal('15.00'))
    hotel = Receipt(file_path='hotel.jpg', receipt_type='hoteles',
                   date=datetime.now(), amount=Decimal('100.00'))
    
    receipt_repo.create(taxi1)
    receipt_repo.create(taxi2)
    receipt_repo.create(hotel)
    
    # Get taxis only
    taxis = receipt_repo.get_by_type('taxis')
    
    assert len(taxis) == 2
    assert all(r.receipt_type == 'taxis' for r in taxis)


def test_queue_repository_enqueue(queue_repo):
    """Test enqueueing items."""
    item = queue_repo.enqueue('img/test.jpeg')
    
    assert item.id is not None
    assert item.file_path == 'img/test.jpeg'
    assert item.status == ProcessingStatus.PENDING


def test_queue_repository_get_next_pending(queue_repo):
    """Test FIFO order."""
    queue_repo.enqueue('img/first.jpeg')
    queue_repo.enqueue('img/second.jpeg')
    
    next_item = queue_repo.get_next_pending()
    
    assert next_item.file_path == 'img/first.jpeg'


def test_queue_repository_mark_completed(queue_repo):
    """Test marking item as completed."""
    item = queue_repo.enqueue('img/test.jpeg')
    queue_repo.mark_processing(item.id)
    queue_repo.mark_completed(item.id)
    
    # Should not appear in next pending
    next_item = queue_repo.get_next_pending()
    assert next_item is None


def test_queue_repository_auto_reset(queue_repo):
    """Test auto-reset interrupted items."""
    item = queue_repo.enqueue('img/test.jpeg')
    queue_repo.mark_processing(item.id)
    
    # Simulate crash - item stays in 'processing' state
    # Auto-reset should fix this
    reset_count = queue_repo.auto_reset_interrupted()
    
    assert reset_count == 1
    
    # Item should be pending again
    next_item = queue_repo.get_next_pending()
    assert next_item.file_path == 'img/test.jpeg'


# TODO: Add tests for:
# - BankRepository
# - MatchRepository
# - IgnoredRepository
