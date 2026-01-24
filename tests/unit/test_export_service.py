"""Test suite for ExportService - TDD approach."""
import pytest
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import pandas as pd
from src.services.export_service import ExportService
from src.models.domain import Receipt, BankTransaction, Match, MatchType


class TestExportService:
    """Test export service functionality."""
    
    def test_service_initialization(self, test_config):
        """Test service initializes correctly."""
        service = ExportService(test_config)
        
        assert service is not None
        assert service.export_dir.exists()
    
    def test_export_receipts_to_excel(self, test_config, receipt_repo, match_repo, bank_repo):
        """Test exporting receipts with matches to Excel."""
        service = ExportService(test_config)
        
        # Create test data
        receipt = receipt_repo.create(Receipt(
            file_path='result/test.jpg',
            receipt_type='taxis',
            date=datetime(2025, 1, 1),
            amount=Decimal('10.00'),
            description='Test taxi',
            processing_successful=True
        ))
        
        bank_trans = bank_repo.create(BankTransaction(
            date=datetime(2025, 1, 1),
            amount=Decimal('10.00'),
            description='TAXI PAYMENT'
        ))
        
        match_repo.create(Match(
            receipt_id=receipt.id,
            transaction_id=bank_trans.id,
            match_type=MatchType.BOTH,
            confidence=1.0
        ))
        
        # Export to Excel
        output_path = service.export_receipts_with_matches_to_excel('test_export.xlsx')
        
        # Verify file exists
        assert Path(output_path).exists()
        
        # Read and verify content
        df = pd.read_excel(output_path, engine='openpyxl')
        
        assert len(df) == 1
        assert df.iloc[0]['Receipt ID'] == receipt.id
        assert df.iloc[0]['Receipt Amount'] == 10.0
        assert df.iloc[0]['Receipt Type'] == 'taxis'
        assert df.iloc[0]['Match Type'] == 'both'
        assert df.iloc[0]['Match Confidence'] == 1.0
        assert df.iloc[0]['Bank Amount'] == 10.0
        
        # Cleanup
        Path(output_path).unlink()
    
    def test_export_receipts_to_csv(self, test_config, receipt_repo):
        """Test exporting receipts to CSV."""
        service = ExportService(test_config)
        
        # Create test receipt
        receipt_repo.create(Receipt(
            file_path='result/test.jpg',
            receipt_type='comidas',
            date=datetime(2025, 1, 15),
            amount=Decimal('25.50'),
            description='Restaurant meal',
            processing_successful=True
        ))
        
        # Export to CSV
        output_path = service.export_receipts_with_matches_to_csv('test_export.csv')
        
        # Verify file exists
        assert Path(output_path).exists()
        
        # Read and verify content
        df = pd.read_csv(output_path)
        
        assert len(df) == 1
        assert df.iloc[0]['Receipt Amount'] == 25.50
        assert df.iloc[0]['Receipt Type'] == 'comidas'
        assert df.iloc[0]['Match Type'] == 'none'
        
        # Cleanup
        Path(output_path).unlink()
    
    def test_export_auto_filename(self, test_config, receipt_repo):
        """Test auto-generated filename."""
        service = ExportService(test_config)
        
        receipt_repo.create(Receipt(
            file_path='result/test.jpg',
            receipt_type='taxis',
            amount=Decimal('10.00')
        ))
        
        # Export without filename
        output_path = service.export_receipts_with_matches_to_excel()
        
        # Verify file exists with timestamp
        assert Path(output_path).exists()
        assert 'receipts_export_' in output_path
        assert output_path.endswith('.xlsx')
        
        # Cleanup
        Path(output_path).unlink()
    
    def test_export_empty_receipts(self, test_config):
        """Test exporting with no receipts."""
        service = ExportService(test_config)
        
        output_path = service.export_receipts_with_matches_to_excel('empty_export.xlsx')
        
        # Verify file exists
        assert Path(output_path).exists()
        
        # Read and verify empty
        df = pd.read_excel(output_path, engine='openpyxl')
        assert len(df) == 0
        
        # Cleanup
        Path(output_path).unlink()
    
    def test_export_multiple_receipts(self, test_config, receipt_repo, bank_repo, match_repo):
        """Test exporting multiple receipts with various match states."""
        service = ExportService(test_config)
        
        # Create multiple receipts
        r1 = receipt_repo.create(Receipt(
            file_path='result/matched.jpg',
            receipt_type='taxis',
            date=datetime(2025, 1, 1),
            amount=Decimal('10.00')
        ))
        
        r2 = receipt_repo.create(Receipt(
            file_path='result/unmatched.jpg',
            receipt_type='comidas',
            date=datetime(2025, 1, 2),
            amount=Decimal('20.00')
        ))
        
        r3 = receipt_repo.create(Receipt(
            file_path='result/conflict.jpg',
            receipt_type='taxis',
            date=datetime(2025, 1, 3),
            amount=Decimal('15.00')
        ))
        
        # Create bank transactions
        b1 = bank_repo.create(BankTransaction(
            date=datetime(2025, 1, 1),
            amount=Decimal('10.00'),
            description='TAXI'
        ))
        
        # Create matches
        match_repo.create(Match(
            receipt_id=r1.id,
            transaction_id=b1.id,
            match_type=MatchType.BOTH,
            confidence=1.0
        ))
        
        match_repo.create(Match(
            receipt_id=r3.id,
            transaction_id=b1.id,
            match_type=MatchType.BOTH,
            confidence=0.9,
            is_conflict=True
        ))
        
        # Export
        output_path = service.export_receipts_with_matches_to_csv('multiple_export.csv')
        
        # Verify
        df = pd.read_csv(output_path)
        
        assert len(df) == 3
        
        # Check matched receipt
        matched_row = df[df['Receipt ID'] == r1.id].iloc[0]
        assert matched_row['Match Type'] == 'both'
        assert matched_row['Bank Amount'] == 10.0
        
        # Check unmatched receipt
        unmatched_row = df[df['Receipt ID'] == r2.id].iloc[0]
        assert unmatched_row['Match Type'] == 'none'
        assert pd.isna(unmatched_row['Bank Amount']) or unmatched_row['Bank Amount'] == 0.0
        
        # Check conflict
        conflict_row = df[df['Receipt ID'] == r3.id].iloc[0]
        assert conflict_row['Is Conflict'] == True
        
        # Cleanup
        Path(output_path).unlink()
    
    def test_export_with_special_characters(self, test_config, receipt_repo):
        """Test exporting with special characters in descriptions."""
        service = ExportService(test_config)
        
        receipt_repo.create(Receipt(
            file_path='result/special.jpg',
            receipt_type='comidas',
            description='Café "René" - €20.50 (IVA incl.)',
            amount=Decimal('20.50')
        ))
        
        output_path = service.export_receipts_with_matches_to_csv('special_chars.csv')
        
        # Verify file and content
        df = pd.read_csv(output_path)
        assert len(df) == 1
        assert 'Café' in df.iloc[0]['Receipt Description']
        
        # Cleanup
        Path(output_path).unlink()
