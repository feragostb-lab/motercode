"""Dashboard Export page - wrapper."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app_dashboard import page_export as _page_export, init_session_state
def render():
    """Render export page."""
    init_session_state()
    _page_export()
