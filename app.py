"""Streamlit unified application - Receipt Management System."""
import streamlit as st
from pathlib import Path
import sys
import io

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import get_config
from src.core.database import get_database
from src.core.logging import setup_logging

# Import pages from the modular structure
from modules import (
    processor_page,
    dashboard_receipts,
    dashboard_bank_transactions,
    dashboard_statistics,
    dashboard_export,
    rocskincare_workers,
    rocskincare_periods,
    rocskincare_image_upload,
    rocskincare_csv_upload,
    rocskincare_period_closure,
    rocskincare_visualization,
    admin_page
)


def init_session_state():
    """Initialize session state variables for all modules."""
    # Setup logging first
    if 'logging_configured' not in st.session_state:
        config = get_config()
        setup_logging(config, app_name="unified_app", capture_std=True)
        st.session_state.logging_configured = True
    
    # Configuration
    if 'config' not in st.session_state:
        st.session_state.config = get_config()
    
    # Database
    if 'database' not in st.session_state:
        config = st.session_state.config
        st.session_state.database = get_database(config.paths.get('database'))
    
    # Main navigation state
    if 'main_module' not in st.session_state:
        st.session_state.main_module = "OCR Processor"
    
    if 'sub_page' not in st.session_state:
        st.session_state.sub_page = None


def main():
    """Main unified application."""
    
    st.set_page_config(
        page_title="Receipt Management System",
        page_icon="🧾",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    init_session_state()
    
    # Sidebar navigation
    with st.sidebar:
        st.title("🧾 Receipt System")
        st.markdown("---")
        
        # Main module selection
        module = st.radio(
            "Seleccione Módulo:",
            ["🖼️ OCR Processor", "📊 Dashboard", "👥 ROC Skincare", "⚙️ Administración"],
            key='main_module_radio',
            label_visibility="collapsed"
        )
        
        # Store selected module
        if module.startswith("🖼️"):
            st.session_state.main_module = "OCR Processor"
        elif module.startswith("📊"):
            st.session_state.main_module = "Dashboard"
        elif module.startswith("👥"):
            st.session_state.main_module = "ROC Skincare"
        elif module.startswith("⚙️"):
            st.session_state.main_module = "Admin"
        
        st.markdown("---")
        
        # Sub-navigation based on module
        if st.session_state.main_module == "Dashboard":
            st.subheader("Dashboard")
            sub_page = st.radio(
                "Páginas:",
                ["📄 Recibos", "🏦 Transacciones Bancarias", "📊 Estadísticas", "📥 Exportar"],
                key='dashboard_sub_nav',
                label_visibility="collapsed"
            )
            st.session_state.sub_page = sub_page
            
        elif st.session_state.main_module == "ROC Skincare":
            st.subheader("ROC Skincare")
            sub_page = st.radio(
                "Páginas:",
                ["👥 Trabajadores", "📅 Periodos", "�️ Cargar Imágenes", "�📤 Cargar CSV", "🔒 Cierre de Periodos", "📊 Visualización"],
                key='rocskincare_sub_nav',
                label_visibility="collapsed"
            )
            st.session_state.sub_page = sub_page
        else:
            st.session_state.sub_page = None
        
        st.markdown("---")
        st.caption("Receipt Management System v2.0")
        st.caption(f"© 2026")
    
    # Render selected page
    if st.session_state.main_module == "OCR Processor":
        processor_page.render()
    
    elif st.session_state.main_module == "Dashboard":
        if st.session_state.sub_page == "📄 Recibos":
            dashboard_receipts.render()
        elif st.session_state.sub_page == "🏦 Transacciones Bancarias":
            dashboard_bank_transactions.render()
        elif st.session_state.sub_page == "📊 Estadísticas":
            dashboard_statistics.render()
        elif st.session_state.sub_page == "📥 Exportar":
            dashboard_export.render()
    
    elif st.session_state.main_module == "ROC Skincare":
        if st.session_state.sub_page == "👥 Trabajadores":
            rocskincare_workers.render()
        elif st.session_state.sub_page == "📅 Periodos":
            rocskincare_periods.render()
        elif st.session_state.sub_page == "�️ Cargar Imágenes":
            rocskincare_image_upload.render()
        elif st.session_state.sub_page == "�📤 Cargar CSV":
            rocskincare_csv_upload.render()
        elif st.session_state.sub_page == "🔒 Cierre de Periodos":
            rocskincare_period_closure.render()
        elif st.session_state.sub_page == "📊 Visualización":
            rocskincare_visualization.render()    
    elif st.session_state.main_module == "Admin":
        admin_page.render()

if __name__ == "__main__":
    main()
