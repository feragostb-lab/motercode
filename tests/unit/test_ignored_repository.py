"""Unit tests for IgnoredRepository."""
import pytest
import sqlite3
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.repositories.ignored_repository import IgnoredRepository
from src.models.domain import IgnoredReceipt


class TestIgnoredRepository:
    """Test cases for IgnoredRepository."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database connection."""
        db = MagicMock()
        conn = MagicMock()
        cursor = MagicMock()
        
        conn.cursor.return_value = cursor
        db.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        
        return db, conn, cursor
    
    @pytest.fixture
    def repository(self, mock_db):
        """Create an IgnoredRepository instance with mock database."""
        db, _, _ = mock_db
        return IgnoredRepository(db)
    
    def test_ignore_receipt_success(self, repository, mock_db):
        """Test successfully ignoring a receipt."""
        # Arrange
        _, conn, cursor = mock_db
        cursor.lastrowid = 1
        
        # Act
        result = repository.ignore_receipt(receipt_id=42, reason="Test reason")
        
        # Assert
        cursor.execute.assert_called_once()
        assert cursor.execute.call_args[0][0].strip().startswith('INSERT INTO ignored_receipts')
        assert cursor.execute.call_args[0][1] == (42, "Test reason")
        
        assert result is not None
        assert result.id == 1
        assert result.receipt_id == 42
        assert result.reason == "Test reason"
        assert isinstance(result.ignored_at, datetime)
    
    def test_ignore_receipt_no_reason(self, repository, mock_db):
        """Test ignoring a receipt without a reason."""
        # Arrange
        _, conn, cursor = mock_db
        cursor.lastrowid = 2
        
        # Act
        result = repository.ignore_receipt(receipt_id=42, reason=None)
        
        # Assert
        assert result.receipt_id == 42
        assert result.reason is None
    
    def test_ignore_receipt_already_ignored(self, repository, mock_db):
        """Test ignoring a receipt that's already ignored."""
        # Arrange
        _, conn, cursor = mock_db
        cursor.execute.side_effect = [
            sqlite3.IntegrityError(),  # First call (INSERT) fails
            None,  # Second call (SELECT) succeeds
        ]
        
        # Mock fetchone to return an existing ignored receipt
        cursor.fetchone.return_value = {
            'id': 5,
            'receipt_id': 42,
            'ignored_at': '2026-01-15 10:00:00',
            'reason': 'Original reason'
        }
        
        # Act
        result = repository.ignore_receipt(receipt_id=42, reason="New reason")
        
        # Assert
        assert result is not None
        assert result.id == 5
        assert result.receipt_id == 42
        assert result.reason == 'Original reason'  # Should keep original
    
    def test_unignore_receipt_success(self, repository, mock_db):
        """Test successfully unignoring a receipt."""
        # Arrange
        _, conn, cursor = mock_db
        cursor.rowcount = 1
        
        # Act
        result = repository.unignore_receipt(receipt_id=42)
        
        # Assert
        cursor.execute.assert_called_once()
        assert cursor.execute.call_args[0][0] == 'DELETE FROM ignored_receipts WHERE receipt_id = ?'
        assert cursor.execute.call_args[0][1] == (42,)
        assert result is True
    
    def test_unignore_receipt_not_ignored(self, repository, mock_db):
        """Test unignoring a receipt that wasn't ignored."""
        # Arrange
        _, conn, cursor = mock_db
        cursor.rowcount = 0
        
        # Act
        result = repository.unignore_receipt(receipt_id=42)
        
        # Assert
        assert result is False
    
    def test_is_ignored_true(self, repository, mock_db):
        """Test checking if a receipt is ignored (true case)."""
        # Arrange
        _, conn, cursor = mock_db
        cursor.fetchone.return_value = (1,)  # Found
        
        # Act
        result = repository.is_ignored(receipt_id=42)
        
        # Assert
        cursor.execute.assert_called_once()
        assert 'SELECT 1 FROM ignored_receipts WHERE receipt_id = ?' in cursor.execute.call_args[0][0]
        assert cursor.execute.call_args[0][1] == (42,)
        assert result is True
    
    def test_is_ignored_false(self, repository, mock_db):
        """Test checking if a receipt is ignored (false case)."""
        # Arrange
        _, conn, cursor = mock_db
        cursor.fetchone.return_value = None  # Not found
        
        # Act
        result = repository.is_ignored(receipt_id=42)
        
        # Assert
        assert result is False
    
    def test_get_all_ignored_ids(self, repository, mock_db):
        """Test getting all ignored receipt IDs."""
        # Arrange
        _, conn, cursor = mock_db
        cursor.fetchall.return_value = [
            {'receipt_id': 1},
            {'receipt_id': 5},
            {'receipt_id': 10},
        ]
        
        # Act
        result = repository.get_all_ignored_ids()
        
        # Assert
        cursor.execute.assert_called_once()
        assert 'SELECT receipt_id FROM ignored_receipts' in cursor.execute.call_args[0][0]
        assert result == {1, 5, 10}
        assert isinstance(result, set)
    
    def test_get_all_ignored_ids_empty(self, repository, mock_db):
        """Test getting all ignored receipt IDs when none exist."""
        # Arrange
        _, conn, cursor = mock_db
        cursor.fetchall.return_value = []
        
        # Act
        result = repository.get_all_ignored_ids()
        
        # Assert
        assert result == set()
    
    def test_get_all(self, repository, mock_db):
        """Test getting all ignored receipts."""
        # Arrange
        _, conn, cursor = mock_db
        cursor.fetchall.return_value = [
            {
                'id': 1,
                'receipt_id': 10,
                'ignored_at': '2026-01-15 10:00:00',
                'reason': 'Reason 1'
            },
            {
                'id': 2,
                'receipt_id': 20,
                'ignored_at': '2026-01-16 11:00:00',
                'reason': 'Reason 2'
            },
        ]
        
        # Act
        result = repository.get_all()
        
        # Assert
        cursor.execute.assert_called_once()
        assert 'SELECT * FROM ignored_receipts ORDER BY ignored_at DESC' in cursor.execute.call_args[0][0]
        assert len(result) == 2
        assert result[0].receipt_id == 10
        assert result[0].reason == 'Reason 1'
        assert result[1].receipt_id == 20
        assert result[1].reason == 'Reason 2'
    
    def test_get_all_empty(self, repository, mock_db):
        """Test getting all ignored receipts when none exist."""
        # Arrange
        _, conn, cursor = mock_db
        cursor.fetchall.return_value = []
        
        # Act
        result = repository.get_all()
        
        # Assert
        assert result == []
    
    def test_count(self, repository, mock_db):
        """Test counting ignored receipts."""
        # Arrange
        _, conn, cursor = mock_db
        cursor.fetchone.return_value = (5,)
        
        # Act
        result = repository.count()
        
        # Assert
        cursor.execute.assert_called_once()
        assert 'SELECT COUNT(*) FROM ignored_receipts' in cursor.execute.call_args[0][0]
        assert result == 5
    
    def test_count_zero(self, repository, mock_db):
        """Test counting ignored receipts when none exist."""
        # Arrange
        _, conn, cursor = mock_db
        cursor.fetchone.return_value = (0,)
        
        # Act
        result = repository.count()
        
        # Assert
        assert result == 0
    
    def test_ignore_and_unignore_workflow(self, repository, mock_db):
        """Test complete workflow of ignoring and unignoring."""
        # Arrange
        _, conn, cursor = mock_db
        
        # Act & Assert
        # 1. Receipt not ignored initially
        cursor.fetchone.return_value = None
        assert repository.is_ignored(42) is False
        
        # 2. Ignore the receipt
        cursor.lastrowid = 1
        cursor.fetchone.return_value = None  # Reset for ignore_receipt
        cursor.execute.side_effect = None  # Clear any previous side effects
        ignored = repository.ignore_receipt(42, "Test")
        assert ignored.receipt_id == 42
        
        # 3. Receipt is now ignored
        cursor.fetchone.return_value = (1,)
        assert repository.is_ignored(42) is True
        
        # 4. Unignore the receipt
        cursor.rowcount = 1
        assert repository.unignore_receipt(42) is True
        
        # 5. Receipt not ignored anymore
        cursor.fetchone.return_value = None
        assert repository.is_ignored(42) is False
    
    def test_row_to_model_conversion(self, repository):
        """Test conversion of database row to IgnoredReceipt model."""
        # Arrange
        row = {
            'id': 1,
            'receipt_id': 42,
            'ignored_at': '2026-01-15 10:30:00',
            'reason': 'Test reason'
        }
        
        # Act
        result = repository._row_to_model(row)
        
        # Assert
        assert isinstance(result, IgnoredReceipt)
        assert result.id == 1
        assert result.receipt_id == 42
        assert result.reason == 'Test reason'
        assert isinstance(result.ignored_at, datetime)
    
    def test_model_to_dict_conversion(self, repository):
        """Test conversion of IgnoredReceipt model to dictionary."""
        # Arrange
        model = IgnoredReceipt(
            id=1,
            receipt_id=42,
            ignored_at=datetime(2026, 1, 15, 10, 30),
            reason='Test reason'
        )
        
        # Act
        result = repository._model_to_dict(model)
        
        # Assert
        assert isinstance(result, dict)
        assert result['receipt_id'] == 42
        assert result['reason'] == 'Test reason'
        # Note: ignored_at is not included in dict as it's auto-generated
        assert 'ignored_at' not in result
        assert 'id' not in result
