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
    failed_items_page,
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
    admin_page,
    admin_test_receipt,
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
    
    # Initialize dashboard services (needed for statistics, export, etc.)
    if 'receipt_service' not in st.session_state:
        from src.services.receipt_service import ReceiptService
        from src.services.bank_matching_service import BankMatchingService
        from src.services.statistics_service import StatisticsService
        from src.services.export_service import ExportService
        from src.repositories.ignored_repository import IgnoredRepository
        
        config = st.session_state.config
        db = st.session_state.database
        
        st.session_state.receipt_service = ReceiptService(config)
        st.session_state.matching_service = BankMatchingService(config)
        st.session_state.stats_service = StatisticsService(config)
        st.session_state.export_service = ExportService(config)
        st.session_state.ignored_repo = IgnoredRepository(db)
    
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
        if st.session_state.main_module == "OCR Processor":
            st.subheader("OCR Processor")
            sub_page = st.radio(
                "Páginas:",
                ["🖼️ Procesador", "❌ Items Fallidos"],
                key='processor_sub_nav',
                label_visibility="collapsed"
            )
            st.session_state.sub_page = sub_page
        
        elif st.session_state.main_module == "Dashboard":
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
        elif st.session_state.main_module == "Admin":
            st.subheader("Administración")
            sub_page = st.radio(
                "Páginas:",
                ["⚙️ Administración", "🧪 Test Receipt"],
                key='admin_sub_nav',
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
        if st.session_state.sub_page == "❌ Items Fallidos":
            failed_items_page.render()
        else:
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
        if st.session_state.sub_page == "🧪 Test Receipt":
            admin_test_receipt.render()
        else:
            admin_page.render()

if __name__ == "__main__":
    if st.runtime.exists():
        main()
    else:
        import sys
        import os
        from streamlit.web import cli as stcli

        # Default to running this script
        script_path = os.path.abspath(__file__)

        # Resolve target script path for frozen app (PyInstaller)
        if getattr(sys, 'frozen', False):
            # Locate the bundled app.py
            # We added 'app.py' to datas, so it should be available in the bundle.
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
            
            possible_paths = [
                os.path.join(base_dir, 'app.py'),
                os.path.join(base_dir, '_internal', 'app.py'), # Default internal folder for onedir
                os.path.join(os.path.dirname(sys.executable), 'app.py'),
            ]
            
            found = False
            for p in possible_paths:
                if os.path.exists(p):
                    script_path = p
                    found = True
                    break
            
            if not found:
                # Last resort: Assuming it's in the current directory if we are lucky
                if os.path.exists("app.py"):
                    script_path = "app.py"
                else:
                    print("Error: Could not find app.py source file for Streamlit!")
                    print(f"Searched in: {possible_paths}")
                    # Keep going to let it fail naturally or maybe it works if streamlit finds it differently
        
        sys.argv = ["streamlit", "run", script_path, "--global.developmentMode=false"]
        sys.exit(stcli.main())
