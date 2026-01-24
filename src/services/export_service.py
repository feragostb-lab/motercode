"""Export service - Export data to Excel/CSV."""
import logging
from pathlib import Path
from typing import Optional
import pandas as pd
from datetime import datetime

from ..repositories.receipt_repository import ReceiptRepository
from ..repositories.bank_repository import BankRepository
from ..repositories.match_repository import MatchRepository
from ..core.database import get_database

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting data."""
    
    def __init__(self, config):
        """
        Initialize export service.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.db = get_database(config.paths.get('database', './receipts.db'))
        self.receipt_repo = ReceiptRepository(self.db)
        self.bank_repo = BankRepository(self.db)
        self.match_repo = MatchRepository(self.db)
        self.export_dir = Path(config.paths.get('exports_dir', './exports'))
        
        # Ensure export directory exists
        self.export_dir.mkdir(parents=True, exist_ok=True)
    
    def export_receipts_with_matches_to_excel(self, filename: Optional[str] = None) -> str:
        """
        Export receipts with their bank matches to Excel.
        
        Args:
            filename: Optional filename (auto-generated if None)
            
        Returns:
            Path to exported file
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"receipts_export_{timestamp}.xlsx"
        
        output_path = self.export_dir / filename
        
        # Get all data
        receipts = self.receipt_repo.get_all()
        
        # Build export data
        export_data = []
        for receipt in receipts:
            # Get match info
            match = self.match_repo.get_by_receipt_id(receipt.id)
            
            # Get bank transaction if matched
            bank_trans = None
            if match and match.transaction_id:
                bank_trans = self.bank_repo.get_by_id(match.transaction_id)
            
            row = {
                'Receipt ID': receipt.id,
                'Receipt Date': receipt.date.strftime('%Y-%m-%d') if receipt.date else '',
                'Receipt Amount': float(receipt.amount) if receipt.amount else 0.0,
                'Receipt Type': receipt.receipt_type or '',
                'Receipt Description': receipt.description or '',
                'File Path': receipt.file_path,
                'Processing Success': receipt.processing_successful,
                'Match Type': match.match_type.value if match else 'none',
                'Match Confidence': float(match.confidence) if match else 0.0,
                'Is Conflict': match.is_conflict if match else False,
                'Conflict Accepted': match.conflict_accepted if match else False,
                'Bank Date': bank_trans.date.strftime('%Y-%m-%d') if bank_trans and bank_trans.date else '',
                'Bank Amount': float(bank_trans.amount) if bank_trans and bank_trans.amount else 0.0,
                'Bank Description': bank_trans.description if bank_trans else '',
                'Bank Reference': bank_trans.reference if bank_trans else '',
            }
            export_data.append(row)
        
        # Create DataFrame and export
        df = pd.DataFrame(export_data)
        df.to_excel(output_path, index=False, engine='openpyxl')
        
        logger.info(f"Exported {len(export_data)} receipts to {output_path}")
        return str(output_path)
    
    def export_receipts_with_matches_to_csv(self, filename: Optional[str] = None) -> str:
        """
        Export receipts with their bank matches to CSV.
        
        Args:
            filename: Optional filename (auto-generated if None)
            
        Returns:
            Path to exported file
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"receipts_export_{timestamp}.csv"
        
        output_path = self.export_dir / filename
        
        # Get all data (same as Excel export)
        receipts = self.receipt_repo.get_all()
        
        export_data = []
        for receipt in receipts:
            match = self.match_repo.get_by_receipt_id(receipt.id)
            bank_trans = None
            if match and match.transaction_id:
                bank_trans = self.bank_repo.get_by_id(match.transaction_id)
            
            row = {
                'Receipt ID': receipt.id,
                'Receipt Date': receipt.date.strftime('%Y-%m-%d') if receipt.date else '',
                'Receipt Amount': float(receipt.amount) if receipt.amount else 0.0,
                'Receipt Type': receipt.receipt_type or '',
                'Receipt Description': receipt.description or '',
                'File Path': receipt.file_path,
                'Processing Success': receipt.processing_successful,
                'Match Type': match.match_type.value if match else 'none',
                'Match Confidence': float(match.confidence) if match else 0.0,
                'Is Conflict': match.is_conflict if match else False,
                'Bank Date': bank_trans.date.strftime('%Y-%m-%d') if bank_trans and bank_trans.date else '',
                'Bank Amount': float(bank_trans.amount) if bank_trans and bank_trans.amount else 0.0,
                'Bank Description': bank_trans.description if bank_trans else '',
            }
            export_data.append(row)
        
        df = pd.DataFrame(export_data)
        df.to_csv(output_path, index=False, encoding='utf-8')
        
        logger.info(f"Exported {len(export_data)} receipts to {output_path}")
        return str(output_path)
    
    def export_unmatched_transactions(self, format: str = 'excel') -> str:
        """
        Export only unmatched bank transactions.
        
        Args:
            format: 'excel' or 'csv'
            
        Returns:
            Path to exported file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = 'xlsx' if format == 'excel' else 'csv'
        filename = f"unmatched_transactions_{timestamp}.{ext}"
        output_path = self.export_dir / filename
        
        # TODO: Implement
        transactions = self.bank_repo.get_unmatched()
        
        # Convert to DataFrame
        df = pd.DataFrame([t.to_dict() for t in transactions])
        
        if format == 'excel':
            df.to_excel(output_path, index=False)
        else:
            df.to_csv(output_path, index=False, encoding='utf-8')
        
        logger.info(f"Exported unmatched transactions to {output_path}")
        return str(output_path)
