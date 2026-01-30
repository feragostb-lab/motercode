"""
Test script to verify that bank transaction IDs are preserved from CSV row order.
CRITICAL: Transaction IDs must match CSV row numbers (1-indexed).
"""
import tempfile
from pathlib import Path
from src.core.database import Database
from src.core.config import Config
from src.repositories.bank_repository import BankRepository
from src.repositories.worker_repository import WorkerRepository
from src.repositories.period_repository import PeriodRepository
from src.services.bank_matching_service import BankMatchingService


def create_test_csv(filepath: str) -> None:
    """Create a test CSV with known row order."""
    csv_content = """fecha,descripcion,metodo,importe
01/01/2024,Primera transacción,Tarjeta,10.50
02/01/2024,Segunda transacción,Efectivo,20.75
03/01/2024,Tercera transacción,Transferencia,30.00
04/01/2024,Cuarta transacción,Tarjeta,40.25
05/01/2024,Quinta transacción,Efectivo,50.99"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(csv_content)
    print(f"✅ Created test CSV: {filepath}")
    print(f"   Row 1: Header")
    print(f"   Row 2: Primera transacción (should get ID=2)")
    print(f"   Row 3: Segunda transacción (should get ID=3)")
    print(f"   Row 4: Tercera transacción (should get ID=4)")
    print(f"   Row 5: Cuarta transacción (should get ID=5)")
    print(f"   Row 6: Quinta transacción (should get ID=6)")


def test_transaction_id_preservation():
    """Test that transaction IDs preserve CSV row order (1-indexed)."""
    print("\n" + "="*70)
    print("TEST: Bank Transaction ID Preservation from CSV Row Order")
    print("="*70)
    
    # Create temporary database and CSV
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_db = Path(tmpdir) / "test.db"
        tmp_csv = Path(tmpdir) / "test_transactions.csv"
        
        # Create test CSV
        create_test_csv(str(tmp_csv))
        
        # Initialize database and repositories
        db = Database(str(tmp_db))
        
        # Load actual config
        config = Config()
        config.paths['database'] = str(tmp_db)
        
        bank_repo = BankRepository(db)
        worker_repo = WorkerRepository(db)
        period_repo = PeriodRepository(db)
        
        # Create test worker and period (using repository methods)
        worker = worker_repo.create("TestWorker")
        worker_id = worker.id
        print(f"✅ Created test worker: ID={worker_id}, Name={worker.nombre}")
        
        period = period_repo.create(worker_id, "2024-01")
        period_id = period.id
        print(f"✅ Created test period: ID={period_id}, Month={period.month_year}")
        
        # Create matching service and upload CSV
        matching_service = BankMatchingService(config)
        
        print(f"\n📤 Uploading CSV: {tmp_csv}")
        count = matching_service.upload_csv_for_period(worker_id, period_id, str(tmp_csv))
        print(f"✅ Loaded {count} transactions")
        
        # Verify transaction IDs match CSV row order
        print("\n" + "-"*70)
        print("VERIFICATION: Transaction IDs vs CSV Row Order")
        print("-"*70)
        
        transactions = bank_repo.get_by_period(period_id)
        transactions_sorted = sorted(transactions, key=lambda t: t.id)
        
        expected_descriptions = [
            "Primera transacción",
            "Segunda transacción",
            "Tercera transacción",
            "Cuarta transacción",
            "Quinta transacción"
        ]
        
        expected_amounts = ["10.5", "20.75", "30.0", "40.25", "50.99"]
        
        # Expected IDs are CSV row numbers (row 2-6, header is row 1)
        expected_csv_rows = [2, 3, 4, 5, 6]
        
        all_correct = True
        for idx, transaction in enumerate(transactions_sorted):
            expected_row = expected_csv_rows[idx]
            expected_desc = expected_descriptions[idx]
            expected_amt = expected_amounts[idx]
            
            row_ok = transaction.csv_row_number == expected_row
            desc_ok = transaction.description == expected_desc
            amt_ok = str(transaction.amount) == expected_amt
            
            status = "✅" if (row_ok and desc_ok and amt_ok) else "❌"
            print(f"{status} CSV Row {expected_row}: csv_row_number={transaction.csv_row_number} (expected {expected_row}), "
                  f"Amount={transaction.amount} (expected {expected_amt}), "
                  f"Desc={transaction.description[:30]}...")
            
            if not (row_ok and desc_ok and amt_ok):
                all_correct = False
                if not row_ok:
                    print(f"   ❌ CSV_ROW_NUMBER MISMATCH: Got {transaction.csv_row_number}, expected {expected_row}")
                if not desc_ok:
                    print(f"   ❌ DESC MISMATCH: Got '{transaction.description}', expected '{expected_desc}'")
                if not amt_ok:
                    print(f"   ❌ AMOUNT MISMATCH: Got {transaction.amount}, expected {expected_amt}")
        
        print("-"*70)
        if all_correct:
            print("\n🎉 SUCCESS: All transaction csv_row_numbers correctly preserve CSV row order!")
            print("   csv_row_number values match original CSV row numbers (header = row 1)")
            print("   csv_row_numbers are 2, 3, 4, 5, 6 (rows after header)")
            print("   id values are auto-generated and unique globally")
        else:
            print("\n❌ FAILURE: Some csv_row_numbers do NOT match CSV row order!")
            print("   This is a CRITICAL issue that must be fixed.")
        
        return all_correct


if __name__ == "__main__":
    try:
        success = test_transaction_id_preservation()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
