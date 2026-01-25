"""Dashboard pages - extracted from app_dashboard.py"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all necessary services
from src.core.config import get_config
from src.services.receipt_service import ReceiptService
from src.services.bank_matching_service import BankMatchingService
from src.services.statistics_service import StatisticsService
from src.services.export_service import ExportService
from src.repositories.ignored_repository import IgnoredRepository
from src.core.database import get_database


def init_dashboard_services():
    """Initialize dashboard services in session state."""
    if 'receipt_service' not in st.session_state:
        config = st.session_state.config
        st.session_state.receipt_service = ReceiptService(config)
        st.session_state.matching_service = BankMatchingService(config)
        st.session_state.stats_service = StatisticsService(config)
        st.session_state.export_service = ExportService(config)
        
        db = st.session_state.database
        st.session_state.ignored_repo = IgnoredRepository(db)
    
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0
    
    if 'filter_type' not in st.session_state:
        st.session_state.filter_type = 'all'
    
    if 'filter_match' not in st.session_state:
        st.session_state.filter_match = 'all'

    if 'unmatched_index' not in st.session_state:
        st.session_state.unmatched_index = 0
