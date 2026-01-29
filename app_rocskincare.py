"""Streamlit dashboard for ROC Skincare - Multi-worker receipt management."""
import streamlit as st
from pathlib import Path
import sys
from PIL import Image
import pandas as pd
from datetime import datetime
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import get_config
from src.core.database import get_database
from src.services.worker_service import WorkerService
from src.services.period_service import PeriodService
from src.services.period_closure_service import PeriodClosureService
from src.services.receipt_service import ReceiptService
from src.services.bank_matching_service import BankMatchingService
from src.services.export_service import ExportService
from src.repositories.worker_repository import WorkerRepository
from src.repositories.period_repository import PeriodRepository
from src.utils.formatters import format_date_spanish, format_datetime_spanish, format_month_year_display
from src.models.domain import PeriodStatus


def init_session_state():
    """Initialize session state variables."""
    if 'config' not in st.session_state:
        st.session_state.config = get_config()
        
    if 'services_initialized' not in st.session_state:
        config = st.session_state.config
        db = get_database(config.paths.get('database'))
        
        # Initialize services
        st.session_state.worker_service = WorkerService(config)
        st.session_state.period_service = PeriodService(config)
        st.session_state.closure_service = PeriodClosureService(config)
        st.session_state.receipt_service = ReceiptService(config)
        st.session_state.matching_service = BankMatchingService(config)
        st.session_state.export_service = ExportService(config)
        
        # Initialize repositories
        st.session_state.worker_repo = WorkerRepository(db)
        st.session_state.period_repo = PeriodRepository(db)
        
        st.session_state.services_initialized = True
    
    # Navigation state
    if 'page' not in st.session_state:
        st.session_state.page = 'workers'


def page_workers():
    """Worker management page."""
    st.header("👥 Gestión de Trabajadores")
    
    worker_service = st.session_state.worker_service
    
    # Create new worker section
    with st.expander("➕ Crear Nuevo Trabajador", expanded=False):
        with st.form("create_worker_form"):
            new_worker_name = st.text_input(
                "Nombre del Trabajador",
                help="Solo caracteres alfanuméricos (sin espacios ni símbolos)"
            )
            submit = st.form_submit_button("Crear Trabajador")
            
            if submit:
                if not new_worker_name:
                    st.error("❌ El nombre no puede estar vacío")
                else:
                    try:
                        worker = worker_service.create_worker(new_worker_name)
                        st.success(f"✅ Trabajador '{worker.nombre}' creado exitosamente")
                        st.rerun()
                    except ValueError as e:
                        st.error(f"❌ Error: {e}")
    
    # List existing workers
    st.subheader("📋 Trabajadores Existentes")
    
    workers = worker_service.get_all_workers(include_inactive=True)
    
    if not workers:
        st.info("No hay trabajadores registrados. Crea el primero arriba.")
        return
    
    # Display workers in a table
    for worker in workers:
        col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
        
        with col1:
            status_icon = "✅" if worker.activo else "❌"
            st.write(f"{status_icon} **{worker.nombre}**")
        
        with col2:
            worker_dir = Path(f"./workers/{worker.nombre}")
            if worker_dir.exists():
                st.caption(f"📁 {worker_dir}")
            else:
                st.caption("📁 Sin directorio")
        
        with col3:
            # Count periods
            periods = st.session_state.period_repo.get_by_worker(worker.id)
            st.caption(f"📅 {len(periods)} periodos")
        
        with col4:
            # Toggle active/inactive
            if worker.activo:
                if st.button(f"Desactivar", key=f"deactivate_{worker.id}"):
                    worker_service.deactivate_worker(worker.id)
                    st.success(f"Trabajador '{worker.nombre}' desactivado")
                    st.rerun()
            else:
                if st.button(f"Activar", key=f"activate_{worker.id}"):
                    worker_service.activate_worker(worker.id)
                    st.success(f"Trabajador '{worker.nombre}' activado")
                    st.rerun()
        
        st.divider()


def page_periods():
    """Period management page."""
    st.header("📅 Gestión de Periodos")
    
    worker_service = st.session_state.worker_service
    period_service = st.session_state.period_service
    period_repo = st.session_state.period_repo
    
    # Get active workers
    workers = worker_service.get_all_workers(include_inactive=False)
    
    if not workers:
        st.warning("⚠️ No hay trabajadores activos. Crea uno primero en la página de Trabajadores.")
        return
    
    # Create new period section
    with st.expander("➕ Crear Nuevo Periodo", expanded=False):
        with st.form("create_period_form"):
            worker_options = {w.nombre: w.id for w in workers}
            selected_worker_name = st.selectbox("Trabajador", list(worker_options.keys()))
            
            col1, col2 = st.columns(2)
            with col1:
                month = st.selectbox("Mes", list(range(1, 13)), format_func=lambda x: f"{x:02d}")
            with col2:
                year = st.number_input("Año", min_value=2020, max_value=2030, value=datetime.now().year)
            
            submit = st.form_submit_button("Crear Periodo")
            
            if submit:
                worker_id = worker_options[selected_worker_name]
                month_year = f"{month:02d}{year}"
                
                try:
                    period = period_service.create_period(worker_id, month_year)
                    st.success(f"✅ Periodo {format_month_year_display(month_year)} creado para {selected_worker_name}")
                    st.rerun()
                except ValueError as e:
                    st.error(f"❌ Error: {e}")
    
    # List periods by worker
    st.subheader("📋 Periodos por Trabajador")
    
    for worker in workers:
        with st.expander(f"👤 {worker.nombre}", expanded=True):
            periods = period_repo.get_by_worker(worker.id)
            
            if not periods:
                st.info("Sin periodos creados")
                continue
            
            for period in periods:
                col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])
                
                with col1:
                    st.write(f"**{format_month_year_display(period.month_year)}**")
                
                with col2:
                    status_color = "🟢" if period.status == PeriodStatus.ACTIVE else "🔴"
                    st.write(f"{status_color} {period.status.value}")
                
                with col3:
                    if period.is_processing_active:
                        st.write("🔄 **Procesando**")
                    else:
                        st.write("⏸️ Inactivo")
                
                with col4:
                    # Get stats
                    stats = period_repo.get_period_stats(period.id)
                    if stats:
                        st.caption(f"📄 {stats.total_receipts} recibos")
                        st.caption(f"💳 {stats.total_transactions} transacciones")
                
                with col5:
                    # Actions
                    if period.status == PeriodStatus.ACTIVE:
                        if not period.is_processing_active:
                            if st.button("▶️ Activar", key=f"activate_period_{period.id}"):
                                period_service.set_active_processing_period(period.id)
                                st.success("Periodo activado para procesamiento")
                                st.rerun()
                        else:
                            st.success("✓ Activo")
                    else:
                        st.caption("Cerrado")
                
                # Show more details
                with st.container():
                    if stats:
                        col_a, col_b, col_c, col_d = st.columns(4)
                        with col_a:
                            st.metric("Procesados", stats.processed_receipts)
                        with col_b:
                            st.metric("Con Match", stats.matched_receipts)
                        with col_c:
                            st.metric("Sin Match", stats.unmatched_receipts)
                        with col_d:
                            st.metric("Conflictos", stats.conflicts)
                
                st.divider()


def page_csv_upload():
    """CSV upload and management page."""
    st.header("📤 Carga de CSV Bancario")
    
    period_repo = st.session_state.period_repo
    matching_service = st.session_state.matching_service
    worker_repo = st.session_state.worker_repo
    
    # Get active processing period
    active_period = period_repo.get_active_processing_period()
    
    if not active_period:
        st.warning("⚠️ No hay ningún periodo activo para procesamiento. Activa uno en la página de Periodos.")
        return
    
    # Get worker info
    worker = worker_repo.get_by_id(active_period.worker_id)
    
    st.info(f"📅 Periodo activo: **{format_month_year_display(active_period.month_year)}** - Trabajador: **{worker.nombre}**")
    
    # Upload CSV section
    st.subheader("📁 Subir CSV")
    
    uploaded_file = st.file_uploader(
        "Selecciona archivo CSV o Excel",
        type=['csv', 'xlsx'],
        help="El archivo reemplazará las transacciones previas de este periodo"
    )
    
    if uploaded_file:
        # Save temporarily
        temp_path = Path(f"./temp/{uploaded_file.name}")
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(temp_path, 'wb') as f:
            f.write(uploaded_file.getvalue())
        
        st.write(f"Archivo: **{uploaded_file.name}**")
        st.write(f"Tamaño: {uploaded_file.size / 1024:.1f} KB")
        
        if st.button("🚀 Cargar y Procesar CSV"):
            with st.spinner("Procesando CSV..."):
                try:
                    count = matching_service.upload_csv_for_period(
                        worker.id,
                        active_period.id,
                        str(temp_path)
                    )
                    st.success(f"✅ CSV procesado exitosamente: {count} transacciones cargadas")
                    st.success("✅ Re-matching automático completado")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al procesar CSV: {e}")
    
    # Show upload history
    if active_period.csv_last_upload:
        st.subheader("📊 Última Carga")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Fecha de Carga", format_datetime_spanish(active_period.csv_last_upload))
        with col2:
            if active_period.csv_file_path:
                csv_path = Path(active_period.csv_file_path)
                st.metric("Archivo", csv_path.name)
        
        # Show transactions stats
        stats = period_repo.get_period_stats(active_period.id)
        if stats:
            st.subheader("📈 Estadísticas de Transacciones")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Transacciones", stats.total_transactions)
            with col2:
                st.metric("Matched", stats.matched_transactions)
            with col3:
                st.metric("Sin Match", stats.unmatched_transactions)


def page_image_upload():
    """Image upload page for active period."""
    st.header("🖼️ Carga de Imágenes")
    
    period_repo = st.session_state.period_repo
    worker_repo = st.session_state.worker_repo
    config = st.session_state.config
    
    # Get active processing period
    active_period = period_repo.get_active_processing_period()
    
    if not active_period:
        st.warning("⚠️ No hay ningún periodo activo para procesamiento. Activa uno en la página de Periodos.")
        return
    
    # Get worker info
    worker = worker_repo.get_by_id(active_period.worker_id)
    
    st.info(f"📅 Periodo activo: **{format_month_year_display(active_period.month_year)}** - Trabajador: **{worker.nombre}**")
    
    # Determine target directory
    target_dir = Path(f"./workers/{worker.nombre}/{active_period.month_year}/img")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    st.write(f"📁 Las imágenes se guardarán en: `{target_dir}`")
    
    # Upload images section
    st.subheader("📁 Subir Imágenes")
    
    uploaded_files = st.file_uploader(
        "Selecciona imágenes de recibos",
        type=['jpg', 'jpeg', 'png', 'webp'],
        accept_multiple_files=True,
        help="Puedes seleccionar múltiples imágenes a la vez"
    )
    
    if uploaded_files:
        st.write(f"**{len(uploaded_files)} archivo(s) seleccionado(s)**")
        
        # Show preview of files
        with st.expander("Ver archivos seleccionados", expanded=True):
            for idx, file in enumerate(uploaded_files, 1):
                col1, col2, col3 = st.columns([1, 3, 1])
                with col1:
                    st.write(f"{idx}.")
                with col2:
                    st.write(f"📷 {file.name}")
                with col3:
                    st.write(f"{file.size / 1024:.1f} KB")
        
        if st.button("🚀 Cargar Imágenes", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            success_count = 0
            error_count = 0
            errors = []
            
            for idx, file in enumerate(uploaded_files):
                try:
                    # Update progress
                    progress = (idx + 1) / len(uploaded_files)
                    progress_bar.progress(progress)
                    status_text.text(f"Procesando {idx + 1}/{len(uploaded_files)}: {file.name}")
                    
                    # Save file
                    file_path = target_dir / file.name
                    
                    # Check if file already exists
                    if file_path.exists():
                        # Add timestamp to avoid overwriting
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        file_stem = file_path.stem
                        file_suffix = file_path.suffix
                        file_path = target_dir / f"{file_stem}_{timestamp}{file_suffix}"
                    
                    with open(file_path, 'wb') as f:
                        f.write(file.getvalue())
                    
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"{file.name}: {str(e)}")
            
            progress_bar.empty()
            status_text.empty()
            
            # Show results
            if success_count > 0:
                st.success(f"✅ {success_count} imagen(es) cargada(s) exitosamente en `{target_dir}`")
            
            if error_count > 0:
                st.error(f"❌ {error_count} imagen(es) con errores:")
                for error in errors:
                    st.write(f"  - {error}")
            
            st.info("💡 **Siguiente paso:** Ve al módulo **OCR Processor** para procesar las imágenes")
    
    # Show existing images
    st.divider()
    st.subheader("📊 Imágenes en el Directorio")
    
    # Count existing images
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    existing_images = [f for f in target_dir.glob('*') if f.suffix.lower() in image_extensions]
    
    if existing_images:
        st.metric("Total de Imágenes", len(existing_images))
        
        # Show sample images
        with st.expander("Ver imágenes", expanded=False):
            cols = st.columns(4)
            for idx, img_path in enumerate(existing_images[:12]):  # Show first 12
                with cols[idx % 4]:
                    try:
                        img = Image.open(img_path)
                        st.image(img, caption=img_path.name, use_column_width=True)
                    except Exception as e:
                        st.error(f"Error: {img_path.name}")
            
            if len(existing_images) > 12:
                st.caption(f"... y {len(existing_images) - 12} imágenes más")
    else:
        st.info("No hay imágenes en el directorio del periodo activo")


def page_period_closure():
    """Period closure and reopening page."""
    st.header("🔒 Cierre de Periodos")
    
    worker_service = st.session_state.worker_service
    period_repo = st.session_state.period_repo
    closure_service = st.session_state.closure_service
    
    # Get all workers
    workers = worker_service.get_all_workers(include_inactive=True)
    
    if not workers:
        st.warning("⚠️ No hay trabajadores registrados.")
        return
    
    # Select worker and period
    col1, col2 = st.columns(2)
    
    with col1:
        worker_options = {w.nombre: w.id for w in workers}
        selected_worker_name = st.selectbox("Trabajador", list(worker_options.keys()))
        worker_id = worker_options[selected_worker_name]
    
    periods = period_repo.get_by_worker(worker_id)
    
    if not periods:
        st.info(f"No hay periodos para {selected_worker_name}")
        return
    
    with col2:
        period_options = {format_month_year_display(p.month_year): p.id for p in periods}
        selected_period_name = st.selectbox("Periodo", list(period_options.keys()))
        period_id = period_options[selected_period_name]
    
    # Get selected period
    period = period_repo.get_by_id(period_id)
    
    st.divider()
    
    # Show period status
    col1, col2 = st.columns(2)
    with col1:
        status_color = "🟢" if period.status == PeriodStatus.ACTIVE else "🔴"
        st.metric("Estado", f"{status_color} {period.status.value}")
    with col2:
        active_icon = "🔄" if period.is_processing_active else "⏸️"
        st.metric("Procesamiento", f"{active_icon} {'Activo' if period.is_processing_active else 'Inactivo'}")
    
    # Get stats
    stats = period_repo.get_period_stats(period_id)
    
    if stats:
        st.subheader("📊 Estadísticas del Periodo")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Recibos", stats.total_receipts)
            st.metric("Procesados", stats.processed_receipts)
        with col2:
            st.metric("Con Match", stats.matched_receipts)
            st.metric("Sin Match", stats.unmatched_receipts)
        with col3:
            st.metric("Conflictos", stats.conflicts)
            st.metric("Imágenes sin procesar", stats.unprocessed_images)
        with col4:
            st.metric("Transacciones", stats.total_transactions)
            st.metric("Trans. Matched", stats.matched_transactions)
    
    st.divider()
    
    # Period closure section
    if period.status == PeriodStatus.ACTIVE:
        st.subheader("🔒 Cerrar Periodo")
        
        # Validate closure
        validation = closure_service.validate_closure(period_id)
        
        st.write("**Validación de Cierre:**")
        
        # Build checks from validation results
        checks = [
            ("CSV cargado", 'No se ha cargado ningún archivo CSV bancario' not in validation['blocking_reasons']),
            ("Todos los recibos procesados", validation['can_close']),  # Simplified for now
        ]
        
        all_valid = validation['can_close']
        
        for check_name, is_valid in checks:
            icon = "✅" if is_valid else "❌"
            st.write(f"{icon} {check_name}")
        
        # Show blocking reasons if any
        if validation['blocking_reasons']:
            st.error("❌ No se puede cerrar el periodo:")
            for reason in validation['blocking_reasons']:
                st.write(f"  • {reason}")
        else:
            st.success("✅ Periodo listo para cerrar")
            
            if st.button("🔒 Cerrar Periodo Ahora", type="primary"):
                with st.spinner("Cerrando periodo..."):
                    try:
                        zip_path = closure_service.close_period(period_id)
                        st.success(f"✅ Periodo cerrado exitosamente")
                        st.success(f"📦 ZIP generado: {zip_path}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al cerrar periodo: {e}")
    
    # Period reopening section
    else:  # CLOSED
        st.subheader("🔓 Reabrir Periodo")
        
        st.warning("⚠️ Este periodo está cerrado. Reabrirlo permitirá agregar más datos.")
        
        with st.form("reopen_form"):
            reason = st.text_area(
                "Razón para reabrir",
                help="Explica por qué es necesario reabrir este periodo cerrado"
            )
            submit = st.form_submit_button("🔓 Reabrir Periodo")
            
            if submit:
                if not reason.strip():
                    st.error("❌ Debes proporcionar una razón para reabrir el periodo")
                else:
                    with st.spinner("Reabriendo periodo..."):
                        try:
                            closure_service.reopen_period(period_id, reason)
                            st.success("✅ Periodo reabierto exitosamente")
                            st.success("✅ El ZIP de cierre fue renombrado con sufijo _reopened")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al reabrir periodo: {e}")


def page_visualization():
    """Visualization and export page."""
    st.header("📊 Visualización y Exportación")
    
    worker_service = st.session_state.worker_service
    period_repo = st.session_state.period_repo
    receipt_service = st.session_state.receipt_service
    export_service = st.session_state.export_service
    matching_service = st.session_state.matching_service
    
    # Get all workers
    workers = worker_service.get_all_workers(include_inactive=True)
    
    if not workers:
        st.warning("⚠️ No hay trabajadores registrados.")
        return
    
    # Filter selection
    col1, col2 = st.columns(2)
    
    with col1:
        worker_options = {"Todos": None}
        worker_options.update({w.nombre: w.id for w in workers})
        selected_worker_name = st.selectbox("Filtrar por Trabajador", list(worker_options.keys()))
        selected_worker_id = worker_options[selected_worker_name]
    
    # Get periods for selected worker (or all)
    if selected_worker_id:
        periods = period_repo.get_by_worker(selected_worker_id)
    else:
        periods = period_repo.get_all()
    
    with col2:
        if periods:
            period_options = {"Todos": None}
            period_options.update({format_month_year_display(p.month_year): p.id for p in periods})
            selected_period_name = st.selectbox("Filtrar por Periodo", list(period_options.keys()))
            selected_period_id = period_options[selected_period_name]
        else:
            st.info("Sin periodos disponibles")
            selected_period_id = None
    
    st.divider()
    
    # Export section
    if selected_period_id:
        st.subheader("📤 Exportación Temporal")
        
        st.info("💡 Genera un Excel con todos los datos del periodo seleccionado")
        
        if st.button("📊 Exportar Datos del Periodo"):
            with st.spinner("Generando exportación..."):
                try:
                    export_path = export_service.export_period_data(selected_period_id, 'temporal')
                    st.success(f"✅ Exportación completada: {export_path}")
                    
                    # Offer download
                    with open(export_path, 'rb') as f:
                        st.download_button(
                            "⬇️ Descargar Excel",
                            f,
                            file_name=Path(export_path).name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                except Exception as e:
                    st.error(f"❌ Error al exportar: {e}")
    
    st.divider()
    
    # Data visualization
    st.subheader("📋 Datos")
    
    # Get receipts based on filters
    if selected_period_id:
        receipts = receipt_service.repository.get_by_period(selected_period_id)
    elif selected_worker_id:
        receipts = receipt_service.repository.get_by_worker(selected_worker_id)
    else:
        receipts = receipt_service.repository.get_all()
    
    st.write(f"**Total recibos:** {len(receipts)}")
    
    if receipts:
        # Create DataFrame for display
        data = []
        for receipt in receipts:
            match = matching_service.match_repo.get_by_receipt_id(receipt.id)
            
            data.append({
                'ID': receipt.id,
                'Fecha': format_date_spanish(receipt.date) if receipt.date else 'N/A',
                'Importe': f"{float(receipt.amount):.2f}€" if receipt.amount else 'N/A',
                'Tipo': receipt.receipt_type or 'N/A',
                'Descripción': receipt.description or 'N/A',
                'Match': match.match_type.value if match else 'sin_match',
                'Conflicto': '⚠️' if (match and match.is_conflict) else ''
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, height=400)


def main():
    """Main application."""
    st.set_page_config(
        page_title="ROC Skincare - Gestión de Recibos",
        page_icon="🧴",
        layout="wide"
    )
    
    init_session_state()
    
    # Sidebar navigation
    st.sidebar.title("🧴 ROC Skincare")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "Navegación",
        ["👥 Trabajadores", "📅 Periodos", "�️ Cargar Imágenes", "📤 Cargar CSV", "🔒 Cierre de Periodos", "📊 Visualización"],
        key='nav_radio'
    )
    
    # Map page selection to function
    page_map = {
        "👥 Trabajadores": page_workers,
        "📅 Periodos": page_periods,
        "🖼️ Cargar Imágenes": page_image_upload,
        "📤 Cargar CSV": page_csv_upload,
        "🔒 Cierre de Periodos": page_period_closure,
        "📊 Visualización": page_visualization
    }
    
    # Render selected page
    page_map[page]()
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.caption("ROC Skincare Receipt Management System")
    st.sidebar.caption(f"Versión 1.0 - {datetime.now().strftime('%Y')}")


if __name__ == "__main__":
    main()
