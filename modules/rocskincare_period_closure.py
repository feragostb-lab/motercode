"""ROCSkincare Period Closure page - wrapper."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app_rocskincare import page_period_closure as _page_period_closure, init_session_state
def render():
    """Render period closure page."""
    init_session_state()
    _page_period_closure()
