"""Migration script - Convert existing JSON data to SQLite database."""
import json
import logging
from pathlib import Path
from decimal import Decimal
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import get_config
from src.core.database import get_database
from src.repositories.receipt_repository import ReceiptRepository
from src.repositories.ignored_repository import IgnoredRepository
from src.models.domain import Receipt
from src.utils.formatters import normalizar_fecha, normalizar_monto

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_receipts(config, receipt_repo: ReceiptRepository):
    """
    Migrate receipts from historial_procesamiento.json to database.
    
    Args:
        config: Configuration object
        receipt_repo: Receipt repository
        
    Returns:
        Number of receipts migrated
    """
    json_file = Path('result/historial_procesamiento.json')
    
    if not json_file.exists():
        logger.warning(f"JSON file not found: {json_file}")
        return 0
    
    logger.info(f"Loading receipts from {json_file}...")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    migrated_count = 0
    
    for item in data:
        try:
            # Extract data from JSON structure
            # TODO: Map JSON structure to Receipt model
            # Sample JSON structure:
            # {
            #     "archivo_original": "original.jpeg",
            #     "archivo_resultado": "241225_1234_taxis.jpeg",
            #     "tipo_deducido": "taxis",
            #     "datos_extraidos": {...},
            #     "procesado_exitoso": true,
            #     "error": null
            # }
            
            extracted_data = item.get('datos_extraidos', {})
            
            # Parse date
            fecha_str = extracted_data.get('fecha', '')
            fecha = normalizar_fecha(fecha_str)
            
            # Parse amount
            total_str = extracted_data.get('total', '')
            total = normalizar_monto(total_str)
            
            # Create receipt model
            receipt = Receipt(
                file_path=f"result/{item.get('arquivo_resultado', '')}",
                original_filename=item.get('archivo_original', ''),
                receipt_type=item.get('tipo_deducido', 'otros'),
                date=fecha,
                amount=total,
                extracted_data=extracted_data,
                processing_successful=item.get('procesado_exitoso', True),
                error_message=item.get('error'),
                processing_time=0.0
            )
            
            # Insert into database
            receipt_repo.create(receipt)
            migrated_count += 1
            
        except Exception as e:
            logger.error(f"Error migrating receipt {item.get('archivo_original')}: {e}")
    
    logger.info(f"Migrated {migrated_count} receipts")
    return migrated_count


def migrate_ignored_receipts(config, receipt_repo: ReceiptRepository, 
                             ignored_repo: IgnoredRepository):
    """
    Migrate ignored receipts from recibos_ignorados.json.
    
    Args:
        config: Configuration object
        receipt_repo: Receipt repository
        ignored_repo: Ignored repository
        
    Returns:
        Number of ignored receipts migrated
    """
    json_file = Path('result/recibos_ignorados.json')
    
    if not json_file.exists():
        logger.info("No ignored receipts file found")
        return 0
    
    logger.info(f"Loading ignored receipts from {json_file}...")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    ignored_filenames = set(data.get('ignorados', []))
    migrated_count = 0
    
    # Get all receipts and mark matching ones as ignored
    all_receipts = receipt_repo.get_all()
    
    for receipt in all_receipts:
        filename = Path(receipt.file_path).name
        if filename in ignored_filenames:
            ignored_repo.ignore_receipt(receipt.id, reason="Migrated from JSON")
            migrated_count += 1
    
    logger.info(f"Migrated {migrated_count} ignored receipts")
    return migrated_count


def migrate_accepted_conflicts(config, receipt_repo: ReceiptRepository):
    """
    Migrate accepted conflicts from conflictos_aceptados.json.
    
    Args:
        config: Configuration object
        receipt_repo: Receipt repository
        
    Returns:
        Number of conflicts migrated
    """
    json_file = Path('result/conflictos_aceptados.json')
    
    if not json_file.exists():
        logger.info("No accepted conflicts file found")
        return 0
    
    logger.info(f"Loading accepted conflicts from {json_file}...")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    accepted_filenames = set(data.get('conflictos_aceptados', []))
    
    # Import here to avoid circular dependency
    from src.repositories.match_repository import MatchRepository
    db = get_database(config.paths.get('database', './receipts.db'))
    match_repo = MatchRepository(db)
    
    migrated_count = 0
    
    # Get all receipts and mark matching conflicts as accepted
    all_receipts = receipt_repo.get_all()
    
    for receipt in all_receipts:
        filename = Path(receipt.file_path).name
        if filename in accepted_filenames:
            # Get match for this receipt
            match = match_repo.get_by_receipt_id(receipt.id)
            if match and match.is_conflict:
                # Accept the conflict
                match_repo.accept_conflict(receipt.id)
                migrated_count += 1
    
    logger.info(f"Migrated {migrated_count} accepted conflicts")
    return migrated_count


def migrate_bank_transactions(config):
    """
    Migrate bank transactions from Excel file.
    
    Args:
        config: Configuration object
        
    Returns:
        Number of transactions migrated
    """
    bank_excel = config.paths.get('bank_excel', '')
    
    if not bank_excel or not Path(bank_excel).exists():
        logger.info("No bank Excel file found or configured")
        return 0
    
    logger.info(f"Loading bank transactions from {bank_excel}...")
    
    try:
        from src.repositories.bank_repository import BankRepository
        db = get_database(config.paths.get('database', './receipts.db'))
        bank_repo = BankRepository(db)
        
        # Load from Excel using repository method
        count = bank_repo.load_from_excel(bank_excel)
        logger.info(f"Migrated {count} bank transactions")
        return count
        
    except Exception as e:
        logger.error(f"Error migrating bank transactions: {e}")
        return 0


def calculate_matches(config):
    """
    Calculate initial matches between receipts and bank transactions.
    
    Args:
        config: Configuration object
        
    Returns:
        Number of matches created
    """
    try:
        from src.services.bank_matching_service import BankMatchingService
        
        matching_service = BankMatchingService(config)
        matches_created = matching_service.recalculate_all_matches()
        
        logger.info(f"Created {matches_created} matches")
        return matches_created
        
    except Exception as e:
        logger.error(f"Error calculating matches: {e}")
        return 0


def main():
    """Main migration process."""
    logger.info("=" * 60)
    logger.info("Starting migration from JSON to SQLite")
    logger.info("=" * 60)
    
    # Load configuration
    config = get_config()
    
    # Initialize database (creates tables if needed)
    db = get_database(config.paths.get('database', './receipts.db'))
    logger.info(f"Database initialized at: {config.paths.get('database')}")
    
    # Initialize repositories
    receipt_repo = ReceiptRepository(db)
    ignored_repo = IgnoredRepository(db)
    
    # Check if database already has data
    existing_count = receipt_repo.count()
    if existing_count > 0:
        response = input(f"\nDatabase already contains {existing_count} receipts. Continue? (y/n): ")
        if response.lower() != 'y':
            logger.info("Migration cancelled")
            return
    
    # Migrate receipts
    receipts_migrated = migrate_receipts(config, receipt_repo)
    
    # Migrate ignored receipts
    ignored_migrated = migrate_ignored_receipts(config, receipt_repo, ignored_repo)
    
    # Migrate accepted conflicts
    conflicts_migrated = migrate_accepted_conflicts(config, receipt_repo)
    
    # Migrate bank transactions from Excel if available
    logger.info("\nMigrating bank transactions...")
    bank_migrated = migrate_bank_transactions(config)
    
    # Calculate matches if both receipts and bank transactions exist
    if receipts_migrated > 0 and bank_migrated > 0:
        logger.info("\nCalculating matches...")
        matches_created = calculate_matches(config)
    else:
        matches_created = 0
    
    # Summary
    logger.info("=" * 60)
    logger.info("Migration Summary:")
    logger.info(f"  Receipts: {receipts_migrated}")
    logger.info(f"  Ignored: {ignored_migrated}")
    logger.info(f"  Conflicts: {conflicts_migrated}")
    logger.info(f"  Bank Transactions: {bank_migrated}")
    logger.info(f"  Matches Created: {matches_created}")
    logger.info("=" * 60)
    logger.info("✅ Migration completed!")


if __name__ == "__main__":
    main()
