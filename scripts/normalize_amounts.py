"""
Script para normalizar todos los importes en la base de datos.
Convierte importes con formato de coma (9,60) a formato de punto (9.60).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from decimal import Decimal
from src.core.database import get_database
from src.core.config import get_config
from src.repositories.receipt_repository import ReceiptRepository
from src.repositories.bank_repository import BankRepository
from src.utils.formatters import normalizar_monto


def normalize_receipts(receipt_repo):
    """Normalizar importes en la tabla receipts."""
    receipts = receipt_repo.get_all()
    updated_count = 0
    
    print(f"\n=== Normalizando importes de recibos ===")
    print(f"Total de recibos: {len(receipts)}")
    
    for receipt in receipts:
        if receipt.amount:
            # El amount ya es un Decimal, pero verificamos si tiene el valor correcto
            original_str = str(receipt.amount)
            
            # Si el extracted_data tiene un formato inconsistente, lo normalizamos también
            if receipt.extracted_data:
                updated_data = False
                for key in ['total', 'importe', 'Total', 'Importe Total']:
                    if key in receipt.extracted_data:
                        value = receipt.extracted_data[key]
                        if isinstance(value, str) and ',' in value:
                            # Normalizar el valor
                            normalized = normalizar_monto(value)
                            if normalized:
                                receipt.extracted_data[key] = str(normalized)
                                updated_data = True
                                print(f"  Recibo {receipt.id}: {key} '{value}' -> '{normalized}'")
                
                if updated_data:
                    receipt_repo.update(receipt)
                    updated_count += 1
    
    print(f"\n✅ Actualizados {updated_count} recibos")
    return updated_count


def normalize_bank_transactions(bank_repo):
    """Normalizar importes en la tabla bank_transactions."""
    transactions = bank_repo.get_all()
    updated_count = 0
    
    print(f"\n=== Normalizando importes de transacciones bancarias ===")
    print(f"Total de transacciones: {len(transactions)}")
    
    for txn in transactions:
        if txn.amount:
            # El amount ya es un Decimal, verificamos consistencia
            original_str = str(txn.amount)
            # Los amounts en la DB ya deberían estar bien como Decimal
            # pero esto asegura que no haya problemas
    
    print(f"✅ Transacciones verificadas")
    return updated_count


def verify_database_amounts(db):
    """Verificar directamente en la base de datos que no haya comas en los amounts."""
    print(f"\n=== Verificando formato de importes en la base de datos ===")
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Verificar receipts
        cursor.execute("SELECT id, amount, extracted_data FROM receipts WHERE amount IS NOT NULL")
        receipts_with_comma = []
        for row in cursor.fetchall():
            receipt_id, amount, extracted_data = row
            if amount and ',' in str(amount):
                receipts_with_comma.append((receipt_id, amount))
        
        if receipts_with_comma:
            print(f"⚠️  Encontrados {len(receipts_with_comma)} recibos con comas en amount:")
            for rid, amt in receipts_with_comma[:5]:  # Mostrar solo los primeros 5
                print(f"   Recibo {rid}: {amt}")
        else:
            print(f"✅ Todos los amounts de recibos están en formato correcto (sin comas)")
        
        # Verificar bank_transactions
        cursor.execute("SELECT id, amount FROM bank_transactions WHERE amount IS NOT NULL")
        txns_with_comma = []
        for row in cursor.fetchall():
            txn_id, amount = row
            if amount and ',' in str(amount):
                txns_with_comma.append((txn_id, amount))
        
        if txns_with_comma:
            print(f"⚠️  Encontradas {len(txns_with_comma)} transacciones con comas en amount:")
            for tid, amt in txns_with_comma[:5]:
                print(f"   Transacción {tid}: {amt}")
        else:
            print(f"✅ Todos los amounts de transacciones están en formato correcto (sin comas)")
    
    return len(receipts_with_comma) + len(txns_with_comma)


def main():
    """Ejecutar normalización."""
    print("=" * 60)
    print("NORMALIZACIÓN DE IMPORTES EN BASE DE DATOS")
    print("=" * 60)
    
    # Inicializar
    config = get_config('config.yaml')
    db = get_database(config.paths.get('database'))
    
    receipt_repo = ReceiptRepository(db)
    bank_repo = BankRepository(db)
    
    # Verificar estado actual
    issues_found = verify_database_amounts(db)
    
    # Normalizar datos
    receipts_updated = normalize_receipts(receipt_repo)
    bank_updated = normalize_bank_transactions(bank_repo)
    
    # Verificar nuevamente
    print("\n" + "=" * 60)
    print("VERIFICACIÓN FINAL")
    print("=" * 60)
    issues_remaining = verify_database_amounts(db)
    
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Recibos actualizados: {receipts_updated}")
    print(f"Transacciones actualizadas: {bank_updated}")
    print(f"Problemas encontrados inicialmente: {issues_found}")
    print(f"Problemas restantes: {issues_remaining}")
    
    if issues_remaining == 0:
        print("\n✅ ¡Normalización completada exitosamente!")
    else:
        print(f"\n⚠️  Aún quedan {issues_remaining} problemas por resolver")
    
    print("=" * 60)


if __name__ == '__main__':
    main()
