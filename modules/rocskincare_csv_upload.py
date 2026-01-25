"""ROCSkincare CSV Upload page - wrapper."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app_rocskincare import page_csv_upload as _page_csv_upload, init_session_state
def render():
    """Render CSV upload page."""
    init_session_state()
    _page_csv_upload()
