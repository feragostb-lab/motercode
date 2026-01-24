"""Pytest configuration and shared fixtures."""
import pytest
import sqlite3
from pathlib import Path
import tempfile
import shutil

from src.core.database import Database
from src.core.config import Config
from src.models.domain import Receipt, BankTransaction, ProcessingQueueItem
from src.repositories.receipt_repository import ReceiptRepository
from src.repositories.bank_repository import BankRepository
from src.repositories.queue_repository import QueueRepository
from src.repositories.match_repository import MatchRepository
from src.repositories.ignored_repository import IgnoredRepository
from datetime import datetime
from decimal import Decimal


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)


@pytest.fixture
def test_db(temp_dir):
    """Create in-memory test database with schema."""
    db_path = temp_dir / 'test.db'
    db = Database(str(db_path))
    # Database __init__ automatically creates tables via _ensure_database_exists()
    yield db
    db_path.unlink(missing_ok=True)


@pytest.fixture
def test_config(temp_dir, test_db):
    """Create test configuration with initialized database."""
    db_path = str(temp_dir / 'test.db')
    config = Config()
    config.set('paths.database', db_path)
    config.set('paths.output_dir', str(temp_dir / 'output'))
    config.set('paths.temp_dir', str(temp_dir / 'temp'))
    config.set('paths.backups_dir', str(temp_dir / 'backups'))
    config.set('paths.exports_dir', str(temp_dir / 'exports'))
    
    # Reset global database instance to use our test db
    import src.core.database
    src.core.database._database = test_db
    
    return config


@pytest.fixture
def receipt_repo(test_db):
    """Create receipt repository for testing."""
    return ReceiptRepository(test_db)


@pytest.fixture
def bank_repo(test_db):
    """Create bank repository for testing."""
    return BankRepository(test_db)


@pytest.fixture
def queue_repo(test_db):
    """Create queue repository for testing."""
    return QueueRepository(test_db)


@pytest.fixture
def match_repo(test_db):
    """Create match repository for testing."""
    return MatchRepository(test_db)


@pytest.fixture
def ignored_repo(test_db):
    """Create ignored repository for testing."""
    return IgnoredRepository(test_db)


@pytest.fixture
def sample_receipt():
    """Create sample receipt for testing."""
    return Receipt(
        file_path='result/250101_1234_taxis.jpeg',
        original_filename='taxi_receipt.jpeg',
        receipt_type='taxis',
        date=datetime(2025, 1, 1),
        amount=Decimal('12.34'),
        extracted_data={
            'empresa': 'Taxi Barcelona',
            'total': '12,34',
            'fecha': '01/01/2025',
            'matricula': '1234ABC'
        },
        processing_successful=True,
    )


@pytest.fixture
def sample_transaction():
    """Create sample bank transaction for testing."""
    return BankTransaction(
        date=datetime(2025, 1, 1),
        amount=Decimal('12.34'),
        description='TAXI BARCELONA',
        reference='TXN123',
    )


@pytest.fixture
def sample_queue_item():
    """Create sample queue item for testing."""
    return ProcessingQueueItem(
        file_path='img/receipt001.jpeg',
    )


@pytest.fixture
def sample_receipts():
    """Create list of sample receipts for testing."""
    return [
        Receipt(
            id=1,
            file_path='result/250101_1234_taxis.jpeg',
            original_filename='taxi1.jpeg',
            receipt_type='taxis',
            date=datetime(2025, 1, 1),
            amount=Decimal('12.34'),
            description='Taxi Barcelona',
            extracted_data={'matricula': '1234ABC', 'origen': 'Airport'},
            processing_successful=True,
        ),
        Receipt(
            id=2,
            file_path='result/250102_5678_restaurante.jpeg',
            original_filename='restaurant1.jpeg',
            receipt_type='restaurante',
            date=datetime(2025, 1, 2),
            amount=Decimal('45.50'),
            description='Restaurant Can Culleretes',
            extracted_data={'camarero': 'Juan', 'total': '45,50'},
            processing_successful=True,
        ),
        Receipt(
            id=3,
            file_path='result/250103_9012_factura.jpeg',
            original_filename='invoice1.jpeg',
            receipt_type='factura',
            date=datetime(2025, 1, 3),
            amount=Decimal('120.00'),
            description='Office supplies',
            extracted_data={'nif': 'B12345678', 'total': '120,00'},
            processing_successful=True,
        ),
    ]


@pytest.fixture
def sample_bank_transactions():
    """Create list of sample bank transactions for testing."""
    return [
        BankTransaction(
            id=1,
            date=datetime(2025, 1, 1),
            amount=Decimal('12.34'),
            description='TAXI BARCELONA',
            reference='TXN001',
        ),
        BankTransaction(
            id=2,
            date=datetime(2025, 1, 2),
            amount=Decimal('45.50'),
            description='CAN CULLERETES REST',
            reference='TXN002',
        ),
        BankTransaction(
            id=3,
            date=datetime(2025, 1, 3),
            amount=Decimal('120.00'),
            description='OFFICE DEPOT',
            reference='TXN003',
        ),
        BankTransaction(
            id=4,
            date=datetime(2025, 1, 4),
            amount=Decimal('25.00'),
            description='SUPERMARKET',
            reference='TXN004',
        ),
    ]


@pytest.fixture
def mock_config():
    """Create mock configuration for testing."""
    config = Config()
    config.set('receipt_types', ['taxis', 'restaurante', 'factura', 'ticket', 'recibo', 'parking'])
    config.set('matching.date_tolerance_days', 2)
    config.set('matching.amount_tolerance_percent', 0.02)
    config.set('paths.database', ':memory:')
    config.set('paths.output_dir', '/tmp/output')
    config.set('paths.temp_dir', '/tmp/temp')
    config.set('paths.backups_dir', '/tmp/backups')
    config.set('paths.exports_dir', '/tmp/exports')
    return config
