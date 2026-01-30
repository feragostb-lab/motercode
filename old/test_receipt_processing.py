"""
Test script for receipt processing using VLM OCR.

This script tests the receipt processing pipeline with sample images
and provides detailed logging of the entire process.
"""
import sys
from pathlib import Path
import logging
import time
from datetime import datetime
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import get_config
from src.core.logging import setup_logging
from src.ocr_processor import BackgroundOCRProcessor
from src.services.queue_service import QueueService
from src.services.receipt_service import ReceiptService
from src.utils.file_helpers import get_image_files


class ReceiptProcessingTester:
    """Test harness for receipt processing."""
    
    def __init__(self, test_images_dir: str = "./tests/receipt_test_examples"):
        """
        Initialize the tester.
        
        Args:
            test_images_dir: Directory containing test images
        """
        self.test_dir = Path(test_images_dir)
        self.config = get_config()
        
        # Setup detailed logging
        setup_logging(self.config, app_name="receipt_test", capture_std=True)
        self.logger = logging.getLogger(__name__)
        
        # Initialize services
        self.processor = BackgroundOCRProcessor()
        self.queue_service = QueueService(self.config)
        self.receipt_service = ReceiptService(self.config)
        
        # Test results
        self.results = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'partial': 0,
            'details': []
        }
    
    def setup_test_environment(self):
        """Prepare the testing environment."""
        self.logger.info("=" * 80)
        self.logger.info("SETTING UP TEST ENVIRONMENT")
        self.logger.info("=" * 80)
        
        # Check if test directory exists
        if not self.test_dir.exists():
            self.logger.error(f"Tests directory not found: {self.test_dir}")
            self.logger.info(f"Creating directory: {self.test_dir}")
            self.test_dir.mkdir(parents=True, exist_ok=True)
            self.logger.warning("⚠️  No test images found. Please add receipt images to test directory.")
            return False
        
        # Get test images
        test_images = get_image_files(str(self.test_dir))
        
        if not test_images:
            self.logger.warning(f"⚠️  No images found in {self.test_dir}")
            self.logger.info("Please add test images (jpg, jpeg, png) to the test directory")
            return False
        
        self.logger.info(f"✓ Found {len(test_images)} test images")
        for img in test_images:
            img_path = Path(img)
            size_kb = img_path.stat().st_size / 1024
            self.logger.info(f"  - {img_path.name} ({size_kb:.1f} KB)")
        
        return True
    
    def clear_queue(self):
        """Clear any existing items from the queue."""
        self.logger.info("\nClearing existing queue items...")
        
        stats = self.queue_service.get_queue_stats()
        total_items = sum(stats.values())
        
        if total_items > 0:
            self.logger.info(f"  Found {total_items} existing queue items")
            self.logger.info("  Clearing queue for clean test run...")
            # Clear the queue by deleting all items
            with self.queue_service.repository.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM processing_queue")
                conn.commit()
            self.logger.info("  ✓ Queue cleared")
        else:
            self.logger.info("  ✓ Queue is empty")
    
    def enqueue_test_images(self):
        """Add test images to the processing queue."""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("ENQUEUEING TEST IMAGES")
        self.logger.info("=" * 80)
        
        test_images = get_image_files(str(self.test_dir))
        
        if not test_images:
            self.logger.error("No test images to enqueue")
            return 0
        
        # Remove duplicates (same file path)
        unique_images = list(set(test_images))
        if len(unique_images) < len(test_images):
            self.logger.warning(f"  Removed {len(test_images) - len(unique_images)} duplicate file paths")
        
        self.logger.info(f"Enqueueing {len(unique_images)} unique test images...")
        count = self.queue_service.enqueue_batch(unique_images)
        self.logger.info(f"✓ Enqueued {count} images for processing")
        
        return count
    
    def process_queue(self):
        """Process all queued images."""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("STARTING RECEIPT PROCESSING")
        self.logger.info("=" * 80)
        
        # Startup tasks
        self.processor.startup()
        
        # Get initial queue stats
        stats = self.queue_service.get_queue_stats()
        pending_count = stats.get('pending', 0)
        
        if pending_count == 0:
            self.logger.warning("No pending items in queue")
            return
        
        self.logger.info(f"Processing {pending_count} pending items...")
        self.logger.info(f"VLM Model: {self.config.processor.get('model_path')}")
        self.logger.info(f"Max Tokens: {self.config.processor.get('max_tokens', 512)}")
        self.logger.info(f"Temperature: {self.config.processor.get('temperature', 0.1)}")
        self.logger.info("")
        
        start_time = datetime.now()
        processed_count = 0
        
        # Get active worker and period for processing (validate before starting)
        worker_id, period_id = self.processor._get_active_worker_and_period()
        if not worker_id or not period_id:
            self.logger.error("❌ No active worker/period found")
            self.logger.error("   Please create and activate a period before running tests")
            return
        
        self.logger.info(f"✓ Using active period ID: {period_id}")
        self.logger.info("")
        
        # Process items one by one
        while True:
            item = self.queue_service.get_next_item(period_id)
            if not item:
                break
            
            processed_count += 1
            item_start = datetime.now()
            
            self.logger.info("-" * 80)
            self.logger.info(f"📸 PROCESSING ITEM {processed_count}/{pending_count}")
            self.logger.info(f"   File: {Path(item.file_path).name}")
            self.logger.info(f"   Queue ID: {item.id}")
            self.logger.info("-" * 80)
            
            try:
                # Process the item
                self.queue_service.start_processing(item.id)
                
                # Load and initialize VLM if needed
                if not self.processor._llm:
                    self.logger.info("Loading VLM model (first time)...")
                    self.processor._initialize_model()
                
                # Get active worker and period for processing
                worker_id, period_id = self.processor._get_active_worker_and_period()
                if not worker_id or not period_id:
                    raise ValueError("No active worker/period found. Please create and activate a period before testing.")
                
                # Process using the internal method
                result = self.processor._process_item(item, worker_id, period_id)
                
                item_duration = (datetime.now() - item_start).total_seconds()
                
                # Mark as completed
                self.queue_service.complete_item(item.id)
                
                self.logger.info(f"✅ SUCCESS - Completed in {item_duration:.1f}s")
                self.results['successful'] += 1
                
                # Get the receipt details
                receipts = self.receipt_service.repository.get_all()
                if receipts:
                    latest = receipts[-1]
                    self.logger.info(f"   📊 Receipt Details:")
                    self.logger.info(f"      Type: {latest.receipt_type}")
                    self.logger.info(f"      Date: {latest.date}")
                    self.logger.info(f"      Amount: {latest.amount}")
                    self.logger.info(f"      File: {latest.file_path}")
                
                self.results['details'].append({
                    'file': Path(item.file_path).name,
                    'status': 'success',
                    'duration': item_duration,
                    'receipt_type': latest.receipt_type if receipts else None,
                    'amount': str(latest.amount) if receipts and latest.amount else None
                })
                
            except Exception as e:
                item_duration = (datetime.now() - item_start).total_seconds()
                error_msg = str(e)
                
                self.logger.error(f"❌ FAILED - {error_msg}")
                self.logger.error(f"   Duration: {item_duration:.1f}s")
                
                # Mark as failed
                self.queue_service.fail_item(item.id, error_msg)
                
                self.results['failed'] += 1
                self.results['details'].append({
                    'file': Path(item.file_path).name,
                    'status': 'failed',
                    'duration': item_duration,
                    'error': error_msg
                })
        
        total_duration = (datetime.now() - start_time).total_seconds()
        
        self.logger.info("\n" + "=" * 80)
        self.logger.info("PROCESSING COMPLETE")
        self.logger.info("=" * 80)
        self.logger.info(f"Total time: {total_duration:.1f}s")
        self.logger.info(f"Processed: {processed_count} items")
        self.logger.info(f"Average: {total_duration/processed_count:.1f}s per item" if processed_count > 0 else "N/A")
    
    def generate_summary(self):
        """Generate and display test summary."""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("TEST SUMMARY")
        self.logger.info("=" * 80)
        
        # Get final queue stats
        queue_stats = self.queue_service.get_queue_stats()
        
        self.logger.info(f"\n📊 Queue Statistics:")
        self.logger.info(f"   Completed: {queue_stats.get('completed', 0)}")
        self.logger.info(f"   Failed: {queue_stats.get('failed', 0)}")
        self.logger.info(f"   Pending: {queue_stats.get('pending', 0)}")
        
        # Get receipt statistics
        receipts = self.receipt_service.repository.get_all()
        
        if receipts:
            self.logger.info(f"\n📄 Receipt Statistics:")
            self.logger.info(f"   Total Receipts: {len(receipts)}")
            
            # Count by type
            type_counts = {}
            for receipt in receipts:
                receipt_type = receipt.receipt_type or 'unknown'
                type_counts[receipt_type] = type_counts.get(receipt_type, 0) + 1
            
            self.logger.info(f"   By Type:")
            for rtype, count in sorted(type_counts.items()):
                self.logger.info(f"      - {rtype}: {count}")
        
        # Detailed results
        if self.results['details']:
            self.logger.info(f"\n📋 Detailed Results:")
            for idx, detail in enumerate(self.results['details'], 1):
                status_emoji = "✅" if detail['status'] == 'success' else "❌"
                self.logger.info(f"   {idx}. {status_emoji} {detail['file']}")
                self.logger.info(f"      Duration: {detail['duration']:.1f}s")
                if detail['status'] == 'success':
                    self.logger.info(f"      Type: {detail.get('receipt_type', 'N/A')}")
                    self.logger.info(f"      Amount: {detail.get('amount', 'N/A')}")
                else:
                    self.logger.info(f"      Error: {detail.get('error', 'Unknown')}")
        
        # Success rate
        total = len(self.results['details'])
        if total > 0:
            success_rate = (self.results['successful'] / total) * 100
            self.logger.info(f"\n✨ Success Rate: {success_rate:.1f}% ({self.results['successful']}/{total})")
        
        self.logger.info("\n" + "=" * 80)
    
    def run(self):
        """Run the complete test suite."""
        self.logger.info("\n")
        self.logger.info("╔" + "=" * 78 + "╗")
        self.logger.info("║" + " " * 20 + "RECEIPT PROCESSING TEST SUITE" + " " * 28 + "║")
        self.logger.info("╚" + "=" * 78 + "╝")
        self.logger.info(f"\nTest Directory: {self.test_dir.absolute()}")
        self.logger.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        try:
            # Setup
            if not self.setup_test_environment():
                return
            
            # Clear queue
            self.clear_queue()
            
            # Enqueue test images
            enqueued = self.enqueue_test_images()
            if enqueued == 0:
                return
            
            self.results['total'] = enqueued
            
            # Process
            self.process_queue()
            
            # Summary
            self.generate_summary()
            
        except KeyboardInterrupt:
            self.logger.warning("\n\n⚠️  Test interrupted by user")
        except Exception as e:
            self.logger.error(f"\n\n💥 Test failed with error: {e}", exc_info=True)
        finally:
            # Cleanup
            if self.processor._llm:
                self.logger.info("\nCleaning up VLM model...")
            
            self.logger.info(f"\nEnd Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info("\n" + "=" * 80)
            self.logger.info("TEST COMPLETE")
            self.logger.info("=" * 80 + "\n")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test receipt processing with VLM OCR')
    parser.add_argument(
        '--test-dir',
        default='./tests/receipt_test_examples',
        help='Directory containing test receipt images'
    )
    
    args = parser.parse_args()
    
    # Run tests
    tester = ReceiptProcessingTester(test_images_dir=args.test_dir)
    tester.run()


if __name__ == "__main__":
    main()
