"""Unit tests for conflict resolution functionality (accepting conflicts)."""
from datetime import datetime
from decimal import Decimal

from src.models.domain import Receipt, BankTransaction, Match, MatchType
from src.repositories.match_repository import MatchRepository
from src.services.statistics_service import StatisticsService
from src.repositories.receipt_repository import ReceiptRepository


def test_accept_conflict_updates_flag(test_db, match_repo: MatchRepository):
    """Marking a conflict as accepted should update conflict_accepted."""
    # Create a conflicting match
    conflict = Match(
        receipt_id=1,
        transaction_id=10,
        match_type=MatchType.BOTH,
        confidence=0.95,
        is_conflict=True,
        conflict_accepted=False,
    )
    created = match_repo.create(conflict)

    # Sanity: initially not accepted
    fetched = match_repo.get_by_receipt_id(created.receipt_id)
    assert fetched is not None and fetched.is_conflict and not fetched.conflict_accepted

    # Accept conflict
    updated = match_repo.accept_conflict(created.receipt_id)
    assert updated is True

    # Verify flag
    fetched_after = match_repo.get_by_receipt_id(created.receipt_id)
    assert fetched_after is not None and fetched_after.conflict_accepted is True


def test_statistics_counts_accepted_conflicts(test_config, match_repo: MatchRepository, receipt_repo: ReceiptRepository):
    """StatisticsService should report accepted vs unresolved conflicts correctly."""
    # Create two receipts
    r1 = receipt_repo.create(Receipt(file_path='r1.jpg', receipt_type='taxis'))
    r2 = receipt_repo.create(Receipt(file_path='r2.jpg', receipt_type='taxis'))

    # Two matches conflicting on the same transaction
    m1 = match_repo.create(Match(
        receipt_id=r1.id,
        transaction_id=100,
        match_type=MatchType.BOTH,
        confidence=0.9,
        is_conflict=True,
        conflict_accepted=False,
    ))
    m2 = match_repo.create(Match(
        receipt_id=r2.id,
        transaction_id=100,
        match_type=MatchType.BOTH,
        confidence=0.88,
        is_conflict=True,
        conflict_accepted=False,
    ))

    # Accept one of them
    match_repo.accept_conflict(m1.receipt_id)

    # Compute statistics
    stats_service = StatisticsService(test_config)
    matching_stats = stats_service.get_matching_statistics()

    assert matching_stats['conflicts'] == 2
    assert matching_stats['accepted_conflicts'] == 1
    assert matching_stats['unresolved_conflicts'] == 1
