"""Tests ensuring ignored receipts don't appear as conflicts for others."""
from datetime import datetime
from decimal import Decimal
import pytest

from src.services.bank_matching_service import BankMatchingService
from src.repositories.receipt_repository import ReceiptRepository
from src.repositories.match_repository import MatchRepository
from src.repositories.ignored_repository import IgnoredRepository
from src.repositories.bank_repository import BankRepository
from src.models.domain import Receipt, Match, MatchType, BankTransaction


def _setup_service(mock_config, test_db):
    service = BankMatchingService(mock_config)
    service.db = test_db
    service.receipt_repo = ReceiptRepository(test_db)
    service.bank_repo = BankRepository(test_db)
    service.match_repo = MatchRepository(test_db)
    service.ignored_repo = IgnoredRepository(test_db)
    return service


def test_conflicts_by_transaction_exclude_ignored(mock_config, test_db):
    """If two receipts conflict on same transaction, ignored one is excluded."""
    service = _setup_service(mock_config, test_db)

    # Create two receipts
    r1 = service.receipt_repo.create(Receipt(file_path='r1.jpg', receipt_type='taxis', amount=Decimal('10.00'), date=datetime(2025,1,1)))
    r2 = service.receipt_repo.create(Receipt(file_path='r2.jpg', receipt_type='taxis', amount=Decimal('10.00'), date=datetime(2025,1,1)))

    # Create a transaction and conflicting matches pointing to same transaction
    t = service.bank_repo.create(BankTransaction(date=datetime(2025,1,1), amount=Decimal('10.00'), description='TAXI', reference='TXN001'))

    service.match_repo.create(Match(receipt_id=r1.id, transaction_id=t.id, match_type=MatchType.BOTH, confidence=1.0, is_conflict=True))
    service.match_repo.create(Match(receipt_id=r2.id, transaction_id=t.id, match_type=MatchType.BOTH, confidence=1.0, is_conflict=True))

    # Ignore r2
    service.ignored_repo.ignore_receipt(r2.id, "Testing ignore")

    # For r1, the ignored r2 must not appear in conflicts
    conflicts_for_r1 = service.get_conflicting_receipts(r1.id)
    assert r2.id not in conflicts_for_r1


def test_conflicts_by_duplicate_exclude_ignored(mock_config, test_db):
    """Duplicate receipts (same date+amount) should exclude ignored ones."""
    service = _setup_service(mock_config, test_db)

    # Two receipts with same date and amount (duplicate scenario)
    r1 = service.receipt_repo.create(Receipt(file_path='dup1.jpg', receipt_type='taxis', amount=Decimal('33.33'), date=datetime(2025,3,3)))
    r2 = service.receipt_repo.create(Receipt(file_path='dup2.jpg', receipt_type='taxis', amount=Decimal('33.33'), date=datetime(2025,3,3)))

    # Add dummy matches with conflict flags so get_conflicting_receipts will consider conflicts
    service.match_repo.create(Match(receipt_id=r1.id, transaction_id=None, match_type=MatchType.NONE, confidence=0.0, is_conflict=True))
    service.match_repo.create(Match(receipt_id=r2.id, transaction_id=None, match_type=MatchType.NONE, confidence=0.0, is_conflict=True))

    # Ignore r2
    service.ignored_repo.ignore_receipt(r2.id, "Testing ignore duplicate")

    # For r1, r2 shouldn't appear among conflicting duplicates
    conflicts_for_r1 = service.get_conflicting_receipts(r1.id)
    assert r2.id not in conflicts_for_r1


def test_conflict_group_flag_persists_after_ignores_current_behavior(mock_config, test_db):
    """Current behavior: si en un grupo se ignoran todos salvo uno, el flag is_conflict permanece en True.

    Grupo 1: r1,r2,r3 en conflicto (mismo movimiento)
    Grupo 2: r4,r5,r6 en conflicto (mismo movimiento). Ignoramos r5 y r6.
    Comprobamos que:
        - get_conflicting_receipts(r4) no devuelve r5/r6 (porque están ignorados)
        - PERO el match de r4 sigue con is_conflict=True (comportamiento actual)
    """
    service = _setup_service(mock_config, test_db)

    # Crear 6 recibos
    r1 = service.receipt_repo.create(Receipt(file_path='g1_1.jpg', receipt_type='taxis'))
    r2 = service.receipt_repo.create(Receipt(file_path='g1_2.jpg', receipt_type='taxis'))
    r3 = service.receipt_repo.create(Receipt(file_path='g1_3.jpg', receipt_type='taxis'))

    r4 = service.receipt_repo.create(Receipt(file_path='g2_4.jpg', receipt_type='taxis'))
    r5 = service.receipt_repo.create(Receipt(file_path='g2_5.jpg', receipt_type='taxis'))
    r6 = service.receipt_repo.create(Receipt(file_path='g2_6.jpg', receipt_type='taxis'))

    # Dos movimientos bancarios: uno para cada grupo
    t1 = service.bank_repo.create(BankTransaction(date=datetime(2025,1,1), amount=Decimal('10.00'), description='G1', reference='T1'))
    t2 = service.bank_repo.create(BankTransaction(date=datetime(2025,1,2), amount=Decimal('20.00'), description='G2', reference='T2'))

    # Crear matches (sin marcar conflicto manual), y dejar que detect_conflicts lo marque
    service.match_repo.create(Match(receipt_id=r1.id, transaction_id=t1.id, match_type=MatchType.BOTH, confidence=1.0))
    service.match_repo.create(Match(receipt_id=r2.id, transaction_id=t1.id, match_type=MatchType.BOTH, confidence=1.0))
    service.match_repo.create(Match(receipt_id=r3.id, transaction_id=t1.id, match_type=MatchType.BOTH, confidence=1.0))

    service.match_repo.create(Match(receipt_id=r4.id, transaction_id=t2.id, match_type=MatchType.BOTH, confidence=1.0))
    service.match_repo.create(Match(receipt_id=r5.id, transaction_id=t2.id, match_type=MatchType.BOTH, confidence=1.0))
    service.match_repo.create(Match(receipt_id=r6.id, transaction_id=t2.id, match_type=MatchType.BOTH, confidence=1.0))

    # Detectar y marcar conflictos
    service.detect_conflicts()

    # Ignorar r6 y r5 del grupo 2
    service.ignored_repo.ignore_receipt(r6.id, "ignore g2-6")
    service.ignored_repo.ignore_receipt(r5.id, "ignore g2-5")

    # 1) La lista de conflictos para r4 no incluye a r5/r6 (ignorados)
    conflicts_for_r4 = service.get_conflicting_receipts(r4.id)
    assert r5.id not in conflicts_for_r4
    assert r6.id not in conflicts_for_r4

    # 2) Comportamiento actual: el flag is_conflict del match de r4 permanece en True
    m4 = service.match_repo.get_by_receipt_id(r4.id)
    assert m4 is not None and m4.is_conflict is True


def test_group_accept_and_ignore_should_clear_remaining_conflict_expected(mock_config, test_db):
    """Esperado: en un grupo (r4,r5,r6), si se ignora r6 y se acepta el conflicto de r5,
    entonces r4 debería quedar SIN conflicto (sin rivales y con is_conflict=False).

    Nota: Este test captura el comportamiento deseado; puede fallar con la lógica actual.
    """
    service = _setup_service(mock_config, test_db)

    # Grupo 1 (control): 1,2,3
    r1 = service.receipt_repo.create(Receipt(file_path='g1_1.jpg', receipt_type='taxis'))
    r2 = service.receipt_repo.create(Receipt(file_path='g1_2.jpg', receipt_type='taxis'))
    r3 = service.receipt_repo.create(Receipt(file_path='g1_3.jpg', receipt_type='taxis'))
    t1 = service.bank_repo.create(BankTransaction(date=datetime(2025,1,1), amount=Decimal('10.00'), description='G1', reference='T1'))
    service.match_repo.create(Match(receipt_id=r1.id, transaction_id=t1.id, match_type=MatchType.BOTH, confidence=1.0))
    service.match_repo.create(Match(receipt_id=r2.id, transaction_id=t1.id, match_type=MatchType.BOTH, confidence=1.0))
    service.match_repo.create(Match(receipt_id=r3.id, transaction_id=t1.id, match_type=MatchType.BOTH, confidence=1.0))

    # Grupo 2 (bajo prueba): 4,5,6
    r4 = service.receipt_repo.create(Receipt(file_path='g2_4.jpg', receipt_type='taxis'))
    r5 = service.receipt_repo.create(Receipt(file_path='g2_5.jpg', receipt_type='taxis'))
    r6 = service.receipt_repo.create(Receipt(file_path='g2_6.jpg', receipt_type='taxis'))
    t2 = service.bank_repo.create(BankTransaction(date=datetime(2025,1,2), amount=Decimal('20.00'), description='G2', reference='T2'))
    service.match_repo.create(Match(receipt_id=r4.id, transaction_id=t2.id, match_type=MatchType.BOTH, confidence=1.0))
    service.match_repo.create(Match(receipt_id=r5.id, transaction_id=t2.id, match_type=MatchType.BOTH, confidence=1.0))
    service.match_repo.create(Match(receipt_id=r6.id, transaction_id=t2.id, match_type=MatchType.BOTH, confidence=1.0))

    # Detectar conflictos iniciales
    service.detect_conflicts()

    # Ignoro r6 y acepto conflicto de r5
    service.ignored_repo.ignore_receipt(r6.id, "ignore g2-6")
    service.match_repo.accept_conflict(r5.id)
    
    # Recomputar flags después de cambios
    service.recompute_conflict_flags()

    # Esperado: r4 queda sin conflictos visibles
    conflicts_for_r4 = service.get_conflicting_receipts(r4.id)
    assert conflicts_for_r4 == []

    # Esperado: el flag del match de r4 debería limpiarse (sin conflicto)
    m4 = service.match_repo.get_by_receipt_id(r4.id)
    assert m4 is not None and m4.is_conflict is False


def test_unignore_receipt_recomputes_conflicts(mock_config, test_db):
    """Al des-ignorar un recibo, los conflictos deben recalcularse.
    
    Escenario: r4,r5,r6 en conflicto. Ignoramos r5 y r6 (r4 queda sin conflicto).
    Luego des-ignoramos r5: r4 debe volver a tener conflicto con r5.
    """
    service = _setup_service(mock_config, test_db)

    # Crear grupo de 3 recibos en conflicto
    r4 = service.receipt_repo.create(Receipt(file_path='r4.jpg', receipt_type='taxis'))
    r5 = service.receipt_repo.create(Receipt(file_path='r5.jpg', receipt_type='taxis'))
    r6 = service.receipt_repo.create(Receipt(file_path='r6.jpg', receipt_type='taxis'))
    t = service.bank_repo.create(BankTransaction(date=datetime(2025,1,1), amount=Decimal('10.00'), description='TX', reference='T1'))

    service.match_repo.create(Match(receipt_id=r4.id, transaction_id=t.id, match_type=MatchType.BOTH, confidence=1.0))
    service.match_repo.create(Match(receipt_id=r5.id, transaction_id=t.id, match_type=MatchType.BOTH, confidence=1.0))
    service.match_repo.create(Match(receipt_id=r6.id, transaction_id=t.id, match_type=MatchType.BOTH, confidence=1.0))

    # Marcar conflictos
    service.detect_conflicts()

    # Ignorar r5 y r6
    service.ignored_repo.ignore_receipt(r5.id, "test")
    service.ignored_repo.ignore_receipt(r6.id, "test")
    service.recompute_conflict_flags()

    # r4 debe quedar sin conflicto
    m4 = service.match_repo.get_by_receipt_id(r4.id)
    assert m4 is not None and m4.is_conflict is False

    # Des-ignorar r5
    service.ignored_repo.unignore_receipt(r5.id)
    service.recompute_conflict_flags()

    # Ahora r4 debe tener conflicto de nuevo (con r5)
    m4_after = service.match_repo.get_by_receipt_id(r4.id)
    assert m4_after is not None and m4_after.is_conflict is True

    # Y r4 debe ver a r5 en la lista de conflictos
    conflicts = service.get_conflicting_receipts(r4.id)
    assert r5.id in conflicts
    assert r6.id not in conflicts  # r6 sigue ignorado
