"""Dashboard Statistics page - wrapper."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app_dashboard import page_statistics as _page_statistics, init_session_state
def render():
    """Render statistics page."""
    init_session_state()
    _page_statistics()
