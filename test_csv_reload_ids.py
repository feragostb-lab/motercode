"""
Test script to verify transaction ID preservation across multiple CSV uploads.
Tests that IDs are correctly reset/reassigned when uploading a new CSV.
"""
import tempfile
from pathlib import Path
from src.core.database import Database
from src.core.config import Config
from src.repositories.bank_repository import BankRepository
from src.repositories.worker_repository import WorkerRepository
from src.repositories.period_repository import PeriodRepository
from src.services.bank_matching_service import BankMatchingService


def create_test_csv_v1(filepath: str) -> None:
    """Create first version of test CSV."""
    csv_content = """fecha,descripcion,metodo,importe
01/01/2024,Compra A,Tarjeta,100.00
02/01/2024,Compra B,Efectivo,200.00
03/01/2024,Compra C,Transferencia,300.00"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(csv_content)


def create_test_csv_v2(filepath: str) -> None:
    """Create second version of test CSV (different data, different row count)."""
    csv_content = """fecha,descripcion,metodo,importe
05/01/2024,Venta X,Tarjeta,50.00
06/01/2024,Venta Y,Efectivo,75.00
07/01/2024,Venta Z,Transferencia,25.00
08/01/2024,Venta W,Tarjeta,99.99
09/01/2024,Venta V,Efectivo,150.50"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(csv_content)


def test_multiple_csv_uploads():
    """Test that transaction IDs are correctly reassigned on CSV re-upload."""
    print("\n" + "="*70)
    print("TEST: Transaction ID Preservation Across Multiple CSV Uploads")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_db = Path(tmpdir) / "test.db"
        tmp_csv1 = Path(tmpdir) / "transactions_v1.csv"
        tmp_csv2 = Path(tmpdir) / "transactions_v2.csv"
        
        # Initialize
        db = Database(str(tmp_db))
        config = Config()
        config.paths['database'] = str(tmp_db)
        
        bank_repo = BankRepository(db)
        worker_repo = WorkerRepository(db)
        period_repo = PeriodRepository(db)
        
        worker = worker_repo.create("TestWorker")
        period = period_repo.create(worker.id, "2024-01")
        matching_service = BankMatchingService(config)
        
        # === UPLOAD 1: First CSV (3 rows) ===
        print("\n📤 UPLOAD 1: Loading first CSV (3 transactions)...")
        create_test_csv_v1(str(tmp_csv1))
        count1 = matching_service.upload_csv_for_period(worker.id, period.id, str(tmp_csv1))
        print(f"✅ Loaded {count1} transactions")
        
        transactions_v1 = sorted(bank_repo.get_by_period(period.id), key=lambda t: t.id)
        print(f"\n📊 Verification after UPLOAD 1:")
        for t in transactions_v1:
            print(f"   ID={t.id}, Amount={t.amount}, Desc={t.description}")
        
        assert len(transactions_v1) == 3, f"Expected 3 transactions, got {len(transactions_v1)}"
        # CSV rows: 1=header, 2=Compra A, 3=Compra B, 4=Compra C
        assert transactions_v1[0].csv_row_number == 2, "First transaction should have csv_row_number=2 (CSV row 2)"
        assert transactions_v1[1].csv_row_number == 3, "Second transaction should have csv_row_number=3 (CSV row 3)"
        assert transactions_v1[2].csv_row_number == 4, "Third transaction should have csv_row_number=4 (CSV row 4)"
        assert transactions_v1[0].description == "Compra A"
        print("✅ Upload 1: All csv_row_numbers correct (2, 3, 4 = CSV rows)")
        
        # === UPLOAD 2: Second CSV (5 rows, replaces previous) ===
        print("\n📤 UPLOAD 2: Loading second CSV (5 transactions, replaces previous)...")
        create_test_csv_v2(str(tmp_csv2))
        count2 = matching_service.upload_csv_for_period(worker.id, period.id, str(tmp_csv2))
        print(f"✅ Loaded {count2} transactions (previous transactions deleted)")
        
        transactions_v2 = sorted(bank_repo.get_by_period(period.id), key=lambda t: t.id)
        print(f"\n📊 Verification after UPLOAD 2:")
        for t in transactions_v2:
            print(f"   ID={t.id}, Amount={t.amount}, Desc={t.description}")
        
        assert len(transactions_v2) == 5, f"Expected 5 transactions, got {len(transactions_v2)}"
        # CSV rows: 1=header, 2=Venta X, 3=Venta Y, 4=Venta Z, 5=Venta W, 6=Venta V
        assert transactions_v2[0].csv_row_number == 2, "First transaction should have csv_row_number=2"
        assert transactions_v2[1].csv_row_number == 3, "Second transaction should have csv_row_number=3"
        assert transactions_v2[2].csv_row_number == 4, "Third transaction should have csv_row_number=4"
        assert transactions_v2[3].csv_row_number == 5, "Fourth transaction should have csv_row_number=5"
        assert transactions_v2[4].csv_row_number == 6, "Fifth transaction should have csv_row_number=6"
        assert transactions_v2[0].description == "Venta X"
        assert transactions_v2[4].description == "Venta V"
        print("✅ Upload 2: All csv_row_numbers correct (2, 3, 4, 5, 6)")
        
        # Verify old data is gone
        for t in transactions_v2:
            assert "Compra" not in t.description, f"Old data still present: {t.description}"
        print("✅ Previous transaction data correctly replaced")
        
        print("\n" + "="*70)
        print("🎉 SUCCESS: Transaction IDs correctly preserved across multiple uploads!")
        print("   - IDs match original CSV row numbers (header = row 1)")
        print("   - IDs correspond to data rows (starting at row 2)")
        print("   - Previous data is correctly replaced")
        print("="*70)
        
        return True


if __name__ == "__main__":
    try:
        success = test_multiple_csv_uploads()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
