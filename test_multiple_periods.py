"""
Test to verify that multiple periods can have transactions with the same csv_row_number.
This tests the fix for UNIQUE constraint failed: bank_transactions.id
"""
import tempfile
from pathlib import Path
from src.core.database import Database
from src.core.config import Config
from src.repositories.bank_repository import BankRepository
from src.repositories.worker_repository import WorkerRepository
from src.repositories.period_repository import PeriodRepository
from src.services.bank_matching_service import BankMatchingService


def create_csv(filepath: str, data: list) -> None:
    """Create a CSV file with specific data."""
    content = "fecha,descripcion,metodo,importe\n"
    content += "\n".join([f"{d[0]},{d[1]},{d[2]},{d[3]}" for d in data])
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def test_multiple_periods_same_csv_rows():
    """Test that multiple periods can have transactions with same csv_row_numbers."""
    print("\n" + "="*70)
    print("TEST: Multiple Periods with Same CSV Row Numbers")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_db = Path(tmpdir) / "test.db"
        
        # Initialize
        db = Database(str(tmp_db))
        config = Config()
        config.paths['database'] = str(tmp_db)
        
        bank_repo = BankRepository(db)
        worker_repo = WorkerRepository(db)
        period_repo = PeriodRepository(db)
        matching_service = BankMatchingService(config)
        
        # Create worker
        worker = worker_repo.create("TestWorker")
        print(f"✅ Created worker: {worker.nombre}")
        
        # === PERIOD 1 ===
        print(f"\n📅 Creating Period 1 (01/2024)...")
        period1 = period_repo.create(worker.id, "2024-01")
        
        # Create CSV for period 1
        tmp_csv1 = Path(tmpdir) / "period1.csv"
        create_csv(str(tmp_csv1), [
            ("01/01/2024", "Período 1 - Transacción A", "Tarjeta", "100.00"),
            ("02/01/2024", "Período 1 - Transacción B", "Efectivo", "200.00"),
        ])
        
        count1 = matching_service.upload_csv_for_period(worker.id, period1.id, str(tmp_csv1))
        print(f"✅ Period 1: Loaded {count1} transactions")
        
        # === PERIOD 2 ===
        print(f"\n📅 Creating Period 2 (02/2024)...")
        period2 = period_repo.create(worker.id, "2024-02")
        
        # Create CSV for period 2 (SAME row numbers as period 1!)
        tmp_csv2 = Path(tmpdir) / "period2.csv"
        create_csv(str(tmp_csv2), [
            ("01/02/2024", "Período 2 - Transacción X", "Tarjeta", "50.00"),
            ("02/02/2024", "Período 2 - Transacción Y", "Efectivo", "75.00"),
        ])
        
        try:
            count2 = matching_service.upload_csv_for_period(worker.id, period2.id, str(tmp_csv2))
            print(f"✅ Period 2: Loaded {count2} transactions (NO ERROR!)")
        except Exception as e:
            print(f"❌ Period 2: FAILED with error: {e}")
            return False
        
        # Verify both periods
        print("\n" + "-"*70)
        print("VERIFICATION: Both Periods Have Correct Data")
        print("-"*70)
        
        trans_p1 = bank_repo.get_by_period(period1.id)
        trans_p2 = bank_repo.get_by_period(period2.id)
        
        print(f"\n📊 Period 1 transactions ({len(trans_p1)}):")
        for t in sorted(trans_p1, key=lambda x: x.csv_row_number):
            print(f"   ID={t.id}, csv_row_number={t.csv_row_number}, "
                  f"Amount={t.amount}, Desc={t.description}")
        
        print(f"\n📊 Period 2 transactions ({len(trans_p2)}):")
        for t in sorted(trans_p2, key=lambda x: x.csv_row_number):
            print(f"   ID={t.id}, csv_row_number={t.csv_row_number}, "
                  f"Amount={t.amount}, Desc={t.description}")
        
        # Verify data integrity
        assert len(trans_p1) == 2, f"Period 1 should have 2 transactions, got {len(trans_p1)}"
        assert len(trans_p2) == 2, f"Period 2 should have 2 transactions, got {len(trans_p2)}"
        
        # Verify csv_row_numbers are preserved
        p1_sorted = sorted(trans_p1, key=lambda x: x.csv_row_number)
        p2_sorted = sorted(trans_p2, key=lambda x: x.csv_row_number)
        
        assert p1_sorted[0].csv_row_number == 2, "Period 1, row 1 should have csv_row_number=2"
        assert p1_sorted[1].csv_row_number == 3, "Period 1, row 2 should have csv_row_number=3"
        assert p2_sorted[0].csv_row_number == 2, "Period 2, row 1 should have csv_row_number=2"
        assert p2_sorted[1].csv_row_number == 3, "Period 2, row 2 should have csv_row_number=3"
        
        # Verify IDs are unique globally
        all_ids = [t.id for t in trans_p1] + [t.id for t in trans_p2]
        assert len(all_ids) == len(set(all_ids)), "All transaction IDs must be unique globally"
        
        # Verify descriptions are correct
        assert "Período 1" in p1_sorted[0].description
        assert "Período 2" in p2_sorted[0].description
        
        print("\n" + "-"*70)
        print("✅ csv_row_numbers are preserved correctly in both periods")
        print("✅ IDs are unique globally (no conflicts)")
        print("✅ Data integrity maintained across periods")
        
        print("\n" + "="*70)
        print("🎉 SUCCESS: Multiple periods can coexist with same csv_row_numbers!")
        print("   - Period 1: csv_row_numbers 2, 3")
        print("   - Period 2: csv_row_numbers 2, 3 (same numbers, different IDs)")
        print("   - No UNIQUE constraint errors")
        print("   - USER'S ISSUE RESOLVED: Can create Period 2 without errors")
        print("="*70)
        
        return True


if __name__ == "__main__":
    try:
        success = test_multiple_periods_same_csv_rows()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
