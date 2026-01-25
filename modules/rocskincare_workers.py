"""ROCSkincare Workers page - wrapper."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app_rocskincare import page_workers as _page_workers, init_session_state
def render():
    """Render workers page."""
    init_session_state()
    _page_workers()
