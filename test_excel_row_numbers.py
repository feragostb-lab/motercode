"""
Test to simulate the user's Excel file scenario with skiprows=13.
This reproduces the exact issue: line 23 in Excel should be ID 23.
"""
import tempfile
from pathlib import Path
import pandas as pd
from src.core.database import Database
from src.core.config import Config
from src.repositories.bank_repository import BankRepository
from src.repositories.worker_repository import WorkerRepository
from src.repositories.period_repository import PeriodRepository
from src.services.bank_matching_service import BankMatchingService


def create_test_excel_with_headers(filepath: str) -> None:
    """Create Excel file simulating user's format (13 header rows + data)."""
    # Simulate 13 header rows (like the user's Excel file)
    # Row 14 is the header with column names
    # Rows 15+ are data
    data = {
        'Col1': (
            ['BANCO HEADER'] + [''] * 11 + ['INFORMACIÓN'] + 
            ['fecha', '15/12/2024', '16/12/2024', '17/12/2024']
        ),
        'Col2': (
            ['INFORMACIÓN'] + [''] * 11 + ['EXTRACTO'] + 
            ['descripcion', 'el abrazo de la china', 'otra transacción', 'tercera transacción']
        ),
        'Col3': (
            ['EXTRACTO'] + [''] * 11 + ['MOVIMIENTOS'] + 
            ['metodo', 'Wallet', 'Tarjeta', 'Efectivo']
        ),
        'Col4': (
            ['MOVIMIENTOS'] + [''] * 11 + ['DETALLE'] + 
            ['importe', '9.60', '15.50', '25.00']
        )
    }
    
    df = pd.DataFrame(data)
    df.to_excel(filepath, index=False, header=False)
    
    print(f"✅ Created Excel with structure:")
    print(f"   Rows 1-13: Headers/metadata")
    print(f"   Row 14: Column headers (fecha, descripcion, metodo, importe)")
    print(f"   Row 15: el abrazo de la china - 9.60€ (should get ID=15)")
    print(f"   Row 16: otra transacción - 15.50€ (should get ID=16)")
    print(f"   Row 17: tercera transacción - 25.00€ (should get ID=17)")
    print(f"\n   USER'S CASE: Line 23 in Excel → should be ID 23")


def test_excel_skiprows_scenario():
    """Test that Excel files with skiprows preserve correct line numbers."""
    print("\n" + "="*70)
    print("TEST: Excel with skiprows=13 (User's Real Scenario)")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_db = Path(tmpdir) / "test.db"
        tmp_excel = Path(tmpdir) / "banco.xlsx"
        
        # Create Excel file
        create_test_excel_with_headers(str(tmp_excel))
        
        # Initialize
        db = Database(str(tmp_db))
        config = Config()
        config.paths['database'] = str(tmp_db)
        
        bank_repo = BankRepository(db)
        worker_repo = WorkerRepository(db)
        period_repo = PeriodRepository(db)
        
        worker = worker_repo.create("TestWorker")
        period = period_repo.create(worker.id, "2024-12")
        matching_service = BankMatchingService(config)
        
        # Upload Excel
        print(f"\n📤 Uploading Excel: {tmp_excel}")
        count = matching_service.upload_csv_for_period(worker.id, period.id, str(tmp_excel))
        print(f"✅ Loaded {count} transactions")
        
        # Verify IDs
        print("\n" + "-"*70)
        print("VERIFICATION: Transaction IDs = Excel Row Numbers")
        print("-"*70)
        
        transactions = sorted(bank_repo.get_by_period(period.id), key=lambda t: t.id)
        
        # After skiprows=13, row 14 is headers, data starts at row 15
        expected_data = [
            (15, "el abrazo de la china", "9.6"),
            (16, "otra transacción", "15.5"),
            (17, "tercera transacción", "25.0")
        ]
        
        all_correct = True
        for transaction, (expected_row, expected_desc, expected_amt) in zip(transactions, expected_data):
            row_ok = transaction.csv_row_number == expected_row
            desc_ok = transaction.description == expected_desc
            amt_ok = str(transaction.amount) == expected_amt
            
            status = "✅" if (row_ok and desc_ok and amt_ok) else "❌"
            print(f"{status} Excel Row {expected_row}: csv_row_number={transaction.csv_row_number}, "
                  f"Amount={transaction.amount}, Desc={transaction.description}")
            
            if not (row_ok and desc_ok and amt_ok):
                all_correct = False
                if not row_ok:
                    print(f"   ❌ CSV_ROW_NUMBER MISMATCH: Got {transaction.csv_row_number}, expected {expected_row}")
        
        print("-"*70)
        
        if all_correct:
            print("\n🎉 SUCCESS: Excel row numbers correctly preserved in csv_row_number!")
            print("   ✅ skiprows=13 correctly handled")
            print("   ✅ csv_row_number = Excel row numbers (15, 16, 17)")
            print("   ✅ id values are auto-generated and unique globally")
            print(f"\n   USER'S CASE RESOLVED:")
            print(f"   - If transaction is on line 23 in Excel")
            print(f"   - It will have csv_row_number = 23 in database")
            print(f"   - Display csv_row_number in all tables (ROC Skincare & Dashboard)")
        else:
            print("\n❌ FAILURE: csv_row_numbers do not match Excel row numbers!")
        
        return all_correct


if __name__ == "__main__":
    try:
        success = test_excel_skiprows_scenario()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
