"""Test suite for ReceiptService - TDD approach."""
import pytest
from decimal import Decimal
from datetime import datetime
from pathlib import Path

from src.services.receipt_service import ReceiptService
from src.models.domain import Receipt
from src.repositories.receipt_repository import ReceiptRepository


# ========================================
# TDD CYCLE 1: deduce_receipt_type()
# ========================================

class TestDeduceReceiptType:
    """Test deduce_receipt_type() method."""
    
    def test_deduce_type_taxi_with_matricula(self, mock_config):
        """🔴 RED: Should detect taxi from 'matricula' keyword."""
        service = ReceiptService(mock_config)
        
        extracted_data = {
            'empresa': 'Taxi Barcelona',
            'total': '12,34',
            'matricula': '1234ABC',
            'origen': 'Airport'
        }
        
        result = service.deduce_receipt_type(extracted_data)
        assert result == 'Taxis'
    
    def test_deduce_type_taxi_with_taximetro(self, mock_config):
        """🔴 RED: Should detect taxi from 'taximetro' keyword."""
        service = ReceiptService(mock_config)
        
        extracted_data = {
            'empresa': 'Radio Taxi',
            'taximetro': 'T-1234',
            'importe': '15,50'
        }
        
        result = service.deduce_receipt_type(extracted_data)
        assert result == 'Taxis'
    
    def test_deduce_type_restaurant_with_camarero(self, mock_config):
        """🔴 RED: Should detect restaurant from 'camarero' keyword."""
        service = ReceiptService(mock_config)
        
        extracted_data = {
            'establecimiento': 'Can Culleretes',
            'camarero': 'Juan',
            'total': '45,50'
        }
        
        result = service.deduce_receipt_type(extracted_data)
        assert result == 'Comidas'
    
    def test_deduce_type_restaurant_with_high_amount(self, mock_config):
        """🔴 RED: Should detect restaurant from high total amount."""
        service = ReceiptService(mock_config)
        
        extracted_data = {
            'establecimiento': 'Restaurant',
            'total': '78,90',
            'mesa': '12'
        }
        
        result = service.deduce_receipt_type(extracted_data)
        assert result == 'Comidas'
    
    def test_deduce_type_factura_with_nif(self, mock_config):
        """🔴 RED: Should detect invoice from NIF."""
        service = ReceiptService(mock_config)
        
        extracted_data = {
            'empresa': 'Suministros SA',
            'nif': 'B12345678',
            'total': '250,00'
        }
        
        result = service.deduce_receipt_type(extracted_data)
        assert result == 'Otros'
    
    def test_deduce_type_parking_with_keyword(self, mock_config):
        """🔴 RED: Should detect parking from 'parking' keyword."""
        service = ReceiptService(mock_config)
        
        extracted_data = {
            'establecimiento': 'PARKING SABA',
            'total': '8,00',
            'horas': '2'
        }
        
        result = service.deduce_receipt_type(extracted_data)
        assert result == 'Estacionamiento'
    
    def test_deduce_type_default_ticket(self, mock_config):
        """🔴 RED: Should default to 'ticket' if no patterns match."""
        service = ReceiptService(mock_config)
        
        extracted_data = {
            'tienda': 'Mercadona',
            'total': '23,45'
        }
        
        result = service.deduce_receipt_type(extracted_data)
        assert result == 'Otros'
    
    def test_deduce_type_empty_data(self, mock_config):
        """🔴 RED: Should default to 'ticket' for empty data."""
        service = ReceiptService(mock_config)
        
        result = service.deduce_receipt_type({})
        assert result == 'Otros'


# ========================================
# TDD CYCLE 2: update_receipt_type()
# ========================================

class TestUpdateReceiptType:
    """Test update_receipt_type() with validation."""
    
    def test_update_type_valid_type(self, mock_config, test_db):
        """🔴 RED: Should update receipt type when valid."""
        service = ReceiptService(mock_config)
        service.db = test_db  # Inject test database
        service.repository = ReceiptRepository(test_db)  # Use test DB repository
        
        # Create receipt
        receipt = Receipt(
            file_path='test.jpeg',
            receipt_type='taxis',
            date=datetime(2025, 1, 1),
            amount=Decimal('12.34')
        )
        created = service.repository.create(receipt)
        
        # Update type (simplified - no file rename for now)
        result = service.update_receipt_type_simple(created.id, 'restaurante')
        
        assert result is True
        
        # Verify in database
        updated = service.repository.get_by_id(created.id)
        assert updated.receipt_type == 'restaurante'
    
    def test_update_type_invalid_type(self, mock_config, test_db):
        """🔴 RED: Should reject invalid receipt type."""
        service = ReceiptService(mock_config)
        service.db = test_db
        service.repository = ReceiptRepository(test_db)
        
        receipt = Receipt(
            file_path='test.jpeg',
            receipt_type='taxis',
            date=datetime(2025, 1, 1),
            amount=Decimal('12.34')
        )
        created = service.repository.create(receipt)
        
        result = service.update_receipt_type_simple(created.id, 'INVALID_TYPE')
        
        assert result is False
    
    def test_update_type_nonexistent_receipt(self, mock_config, test_db):
        """🔴 RED: Should return False for non-existent receipt."""
        service = ReceiptService(mock_config)
        service.db = test_db
        service.repository = ReceiptRepository(test_db)
        
        result = service.update_receipt_type_simple(9999, 'taxis')
        
        assert result is False


# ========================================
# TDD CYCLE 3: update_receipt_date() and update_receipt_amount()
# ========================================

class TestUpdateReceiptDate:
    """Test update_receipt_date() method."""
    
    def test_update_date_valid(self, mock_config, test_db):
        """🔴 RED: Should update receipt date."""
        service = ReceiptService(mock_config)
        service.db = test_db
        service.repository = ReceiptRepository(test_db)
        
        receipt = Receipt(
            file_path='test.jpeg',
            receipt_type='taxis',
            date=datetime(2025, 1, 1),
            amount=Decimal('12.34')
        )
        created = service.repository.create(receipt)
        
        # Update date (simplified version)
        new_date = datetime(2025, 1, 15)
        result = service.update_receipt_date_simple(created.id, new_date)
        
        assert result is True
        
        # Verify
        updated = service.repository.get_by_id(created.id)
        assert updated.date.date() == new_date.date()
    
    def test_update_date_nonexistent(self, mock_config, test_db):
        """🔴 RED: Should return False for non-existent receipt."""
        service = ReceiptService(mock_config)
        service.db = test_db
        service.repository = ReceiptRepository(test_db)
        
        result = service.update_receipt_date_simple(9999, datetime(2025, 1, 1))
        
        assert result is False


class TestUpdateReceiptAmount:
    """Test update_receipt_amount() method."""
    
    def test_update_amount_valid(self, mock_config, test_db):
        """🔴 RED: Should update receipt amount."""
        service = ReceiptService(mock_config)
        service.db = test_db
        service.repository = ReceiptRepository(test_db)
        
        receipt = Receipt(
            file_path='test.jpeg',
            receipt_type='taxis',
            date=datetime(2025, 1, 1),
            amount=Decimal('12.34')
        )
        created = service.repository.create(receipt)
        
        # Update amount (simplified version)
        new_amount = Decimal('25.00')
        result = service.update_receipt_amount_simple(created.id, new_amount)
        
        assert result is True
        
        # Verify
        updated = service.repository.get_by_id(created.id)
        assert updated.amount == new_amount
    
    def test_update_amount_nonexistent(self, mock_config, test_db):
        """🔴 RED: Should return False for non-existent receipt."""
        service = ReceiptService(mock_config)
        service.db = test_db
        service.repository = ReceiptRepository(test_db)
        
        result = service.update_receipt_amount_simple(9999, Decimal('10.00'))
        
        assert result is False


# ========================================
# TDD CYCLE 4: update_receipt_description()
# ========================================

class TestUpdateReceiptDescription:
    """Test update_receipt_description() method."""
    
    def test_update_description_valid(self, mock_config, test_db):
        """🔴 RED: Should update receipt description."""
        service = ReceiptService(mock_config)
        service.db = test_db
        service.repository = ReceiptRepository(test_db)
        
        receipt = Receipt(
            file_path='test.jpeg',
            receipt_type='taxis',
            date=datetime(2025, 1, 1),
            amount=Decimal('12.34'),
            description='Old description'
        )
        created = service.repository.create(receipt)
        
        # Update description
        new_desc = 'New updated description'
        result = service.update_receipt_description(created.id, new_desc)
        
        assert result is True
        
        # Verify
        updated = service.repository.get_by_id(created.id)
        assert updated.description == new_desc
    
    def test_update_description_nonexistent(self, mock_config, test_db):
        """🔴 RED: Should return False for non-existent receipt."""
        service = ReceiptService(mock_config)
        service.db = test_db
        service.repository = ReceiptRepository(test_db)
        
        result = service.update_receipt_description(9999, 'Test')
        
        assert result is False
    # assert receipt_type == 'taxis'


def test_deduce_receipt_type_hotel(test_config):
    """Test receipt type deduction for hotel."""
    service = ReceiptService(test_config)
    
    # TODO: Implement when deduce_receipt_type is implemented
    pass


# TODO: Add more tests for:
# - update_receipt_type
# - update_receipt_date  
# - update_receipt_amount
# - rename_receipt_file
# - file deduplication
