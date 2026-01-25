"""ROCSkincare Visualization page - wrapper."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app_rocskincare import page_visualization as _page_visualization, init_session_state
def render():
    """Render visualization page."""
    init_session_state()
    _page_visualization()
