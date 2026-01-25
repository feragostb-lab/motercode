"""Dashboard Bank Transactions page - wrapper."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app_dashboard import page_bank_transactions as _page_bank_transactions, init_session_state
def render():
    """Render bank transactions page."""
    init_session_state()
    _page_bank_transactions()
