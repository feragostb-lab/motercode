"""Test suite for QueueService."""
import pytest
from src.services.queue_service import QueueService
from src.models.domain import ProcessingStatus


def test_queue_service_initialization(test_config):
    """Test service initialization."""
    service = QueueService(test_config)
    assert service is not None
    assert service.max_attempts == 3


def test_enqueue_file(test_config):
    """Test enqueueing a file."""
    service = QueueService(test_config)
    
    item = service.enqueue_file('img/test.jpeg')
    
    assert item is not None
    assert item.file_path == 'img/test.jpeg'
    assert item.status == ProcessingStatus.PENDING
    assert item.attempts == 0


def test_enqueue_batch(test_config):
    """Test batch enqueueing."""
    service = QueueService(test_config)
    
    files = ['img/test1.jpeg', 'img/test2.jpeg', 'img/test3.jpeg']
    count = service.enqueue_batch(files)
    
    assert count == 3


def test_get_next_item_fifo(test_config):
    """Test FIFO queue order."""
    service = QueueService(test_config)
    
    # Enqueue multiple files
    service.enqueue_file('img/first.jpeg')
    service.enqueue_file('img/second.jpeg')
    service.enqueue_file('img/third.jpeg')
    
    # Get items in FIFO order
    item1 = service.get_next_item()
    assert item1.file_path == 'img/first.jpeg'
    
    service.start_processing(item1.id)
    service.complete_item(item1.id)
    
    item2 = service.get_next_item()
    assert item2.file_path == 'img/second.jpeg'


def test_auto_reset_interrupted(test_config, queue_repo):
    """Test auto-reset of interrupted items."""
    service = QueueService(test_config)
    
    # Create item and mark as processing (simulating interruption)
    item = queue_repo.enqueue('img/interrupted.jpeg')
    queue_repo.mark_processing(item.id)
    
    # Auto-reset
    reset_count = service.auto_reset_interrupted()
    
    assert reset_count == 1
    
    # Item should be back to pending
    next_item = service.get_next_item()
    assert next_item.file_path == 'img/interrupted.jpeg'
    assert next_item.status == ProcessingStatus.PENDING


def test_queue_stats(test_config):
    """Test queue statistics."""
    service = QueueService(test_config)
    
    # Add various items
    service.enqueue_file('img/pending1.jpeg')
    service.enqueue_file('img/pending2.jpeg')
    
    item = service.enqueue_file('img/processing.jpeg')
    service.start_processing(item.id)
    
    stats = service.get_queue_stats()
    
    assert stats['pending'] == 2
    assert stats['processing'] == 1
    assert stats['completed'] == 0


def test_large_queue_warning(test_config):
    """Test warning for large queue."""
    service = QueueService(test_config)
    service.warning_threshold = 5
    
    # Enqueue 6 items (above threshold)
    for i in range(6):
        service.enqueue_file(f'img/file{i}.jpeg')
    
    assert service.should_warn_large_queue() is True


# TODO: Implement retry logic test when fail_item is implemented
def test_retry_logic():
    """Test exponential backoff retry logic."""
    pass
