"""Queue service - Orchestrates processing queue with retry logic."""
import logging
from typing import Optional
from datetime import datetime, timedelta

from ..models.domain import ProcessingQueueItem, ProcessingStatus
from ..repositories.queue_repository import QueueRepository
from ..core.database import get_database

logger = logging.getLogger(__name__)


class QueueService:
    """Service for managing processing queue."""
    
    def __init__(self, config):
        """
        Initialize queue service.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.db = get_database(config.paths.get('database', './receipts.db'))
        self.repository = QueueRepository(self.db)
        
        # Get queue configuration
        queue_config = config.queue
        self.max_attempts = queue_config.get('max_attempts', 3)
        self.retry_backoff_base = queue_config.get('retry_backoff_base_minutes', 2)
        self.warning_threshold = queue_config.get('warning_threshold', 300)
    
    def enqueue_file(self, file_path: str) -> ProcessingQueueItem:
        """
        Add file to processing queue.
        
        Args:
            file_path: Path to file
            
        Returns:
            Queue item
        """
        return self.repository.enqueue(file_path)
    
    def enqueue_batch(self, file_paths: list) -> int:
        """
        Add multiple files to queue.
        
        Args:
            file_paths: List of file paths
            
        Returns:
            Number of files enqueued
        """
        count = 0
        for file_path in file_paths:
            try:
                self.repository.enqueue(file_path)
                count += 1
            except Exception as e:
                logger.error(f"Failed to enqueue {file_path}: {e}")
        
        return count
    
    def get_next_item(self) -> Optional[ProcessingQueueItem]:
        """
        Get next pending item from queue (FIFO).
        
        Returns:
            Next queue item or None if queue empty
        """
        return self.repository.get_next_pending()
    
    def start_processing(self, item_id: int) -> bool:
        """
        Mark item as processing.
        
        Args:
            item_id: Queue item ID
            
        Returns:
            True if successful
        """
        return self.repository.mark_processing(item_id)
    
    def complete_item(self, item_id: int) -> bool:
        """
        Mark item as completed.
        
        Args:
            item_id: Queue item ID
            
        Returns:
            True if successful
        """
        return self.repository.mark_completed(item_id)
    
    def fail_item(self, item_id: int, error_message: str) -> bool:
        """
        Handle item failure with retry logic.
        
        Args:
            item_id: Queue item ID
            error_message: Error description
            
        Returns:
            True if should retry, False if permanently failed
        """
        # Get current item to check attempts
        item = self.repository.get_by_id(item_id)
        if not item:
            logger.error(f"Item {item_id} not found")
            return False
        
        # Mark as failed (increments attempts)
        self.repository.mark_failed(item_id, error_message)
        
        # Check if should retry
        new_attempts = item.attempts + 1
        
        if new_attempts < self.max_attempts:
            # Calculate exponential backoff delay
            backoff_minutes = self.retry_backoff_base ** new_attempts
            logger.info(f"Item {item_id} failed (attempt {new_attempts}/{self.max_attempts}). "
                       f"Will retry after {backoff_minutes} minutes")
            return True  # Will retry
        else:
            # Permanently failed
            logger.error(f"Item {item_id} permanently failed after {new_attempts} attempts: {error_message}")
            return False
    
    def auto_reset_interrupted(self) -> int:
        """
        Reset interrupted items to pending (for crash recovery).
        
        Returns:
            Number of items reset
        """
        return self.repository.auto_reset_interrupted()
    
    def get_queue_stats(self) -> dict:
        """
        Get queue statistics.
        
        Returns:
            Dictionary with stats
        """
        stats = self.repository.get_stats()
        stats['warning'] = stats.get('pending', 0) > self.warning_threshold
        stats['warning_threshold'] = self.warning_threshold
        return stats
    
    def should_warn_large_queue(self) -> bool:
        """Check if pending items exceed warning threshold."""
        pending_count = self.repository.get_pending_count()
        return pending_count > self.warning_threshold
    
    def clear_completed_items(self) -> int:
        """
        Remove completed items from queue.
        
        Returns:
            Number of items removed
        """
        return self.repository.clear_completed()
