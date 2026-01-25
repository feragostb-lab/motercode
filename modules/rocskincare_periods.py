"""ROCSkincare Periods page - wrapper."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app_rocskincare import page_periods as _page_periods, init_session_state
def render():
    """Render periods page."""
    init_session_state()
    _page_periods()
