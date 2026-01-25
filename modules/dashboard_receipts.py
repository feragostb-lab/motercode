"""Dashboard Receipts page - wrapper."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app_dashboard import page_receipts as _page_receipts, init_session_state
def render():
    """Render receipts page."""
    init_session_state()
    _page_receipts()
