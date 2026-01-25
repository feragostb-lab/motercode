"""OCR Processor page module."""
import streamlit as st
import time
from pathlib import Path
from datetime import datetime

from src.core.config import get_config
from src.core.database import get_database
from src.ocr_processor import BackgroundOCRProcessor
from src.services.queue_service import QueueService
from src.utils.file_helpers import get_image_files
from src.repositories.period_repository import PeriodRepository
from src.repositories.worker_repository import WorkerRepository
from src.utils.formatters import format_month_year_display


def init_processor():
    """Initialize processor in session state."""
    if 'processor' not in st.session_state:
        config = st.session_state.config
        st.session_state.processor = BackgroundOCRProcessor()
        st.session_state.queue_service = QueueService(config)
    
    # Initialize repositories if needed
    if 'period_repo' not in st.session_state:
        db = st.session_state.database
        st.session_state.period_repo = PeriodRepository(db)
        st.session_state.worker_repo = WorkerRepository(db)


def render():
    """Render OCR Processor page."""
    
    st.title("🖼️ Receipt Processor - Background OCR")
    
    # Initialize processor
    init_processor()
    
    processor = st.session_state.processor
    queue_service = st.session_state.queue_service
    config = st.session_state.config
    
    # Main layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("Control Panel")
        stats = processor.get_stats()
        # Mode toggle
        current_mode = processor.resource_monitor.get_current_mode() if hasattr(processor, 'resource_monitor') else 'normal'
        is_turbo = current_mode == 'idle-boost'
        is_manual = processor.resource_monitor._manual_override if hasattr(processor, 'resource_monitor') else False
        
        turbo_col1, turbo_col2 = st.columns([3, 1])
        with turbo_col1:
            mode_label = "🚀 TURBO MODE" if is_turbo else "🐢 Normal Mode"
            limits = processor.resource_monitor.get_current_limits() if hasattr(processor, 'resource_monitor') else {}
            cpu_limit = limits.get('max_cpu_percent', 70)
            ram_limit = limits.get('max_ram_percent', 70)
            manual_indicator = " (Manual)" if is_manual else " (Auto)"
            st.subheader(f"{mode_label}{manual_indicator} ({cpu_limit:.0f}% CPU / {ram_limit:.0f}% RAM)")
        with turbo_col2:
            if st.button("🔄 Toggle", help="Switch between Normal (70%) and Turbo (95%) resource usage. Manual mode stays until you toggle again."):
                if hasattr(processor, 'resource_monitor'):
                    if is_manual:
                        processor.resource_monitor.clear_manual_override()
                        st.success("Switched to Automatic mode!")
                    else:
                        new_mode = 'normal' if is_turbo else 'idle-boost'
                        processor.resource_monitor.set_mode(new_mode)
                        st.success(f"Switched to {'Turbo' if new_mode == 'idle-boost' else 'Normal'} mode (Manual)!")
                st.rerun()
        
        st.divider()
        
        # Control buttons
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        
        with btn_col1:
            if st.button("▶️ Start", disabled=processor._is_running, use_container_width=True):
                try:
                    processor.start()
                    st.success("Processor started!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to start: {e}")
        
        with btn_col2:
            if processor._is_running:
                if processor._is_paused:
                    if st.button("▶️ Resume", use_container_width=True):
                        processor.resume()
                        st.rerun()
                else:
                    if st.button("⏸️ Pause", use_container_width=True):
                        processor.pause()
                        st.info("ℹ️ El procesamiento se pausará después de completar el recibo actual")
                        time.sleep(1)
                        st.rerun()
            else:
                st.button("⏸️ Pause", disabled=True, use_container_width=True)
        
        with btn_col3:
            if st.button("⏹️ Stop", disabled=not processor._is_running, use_container_width=True):
                processor.stop(force=True)
                st.warning("⚠️ Procesamiento detenido forzosamente")
                time.sleep(1)
                st.rerun()
        
        st.divider()
        
        # Queue management
        st.subheader("📁 Input Files")
        
        # Get active period info
        period_repo = st.session_state.period_repo
        worker_repo = st.session_state.worker_repo
        active_period = period_repo.get_active_processing_period()
        
        if active_period:
            worker = worker_repo.get_by_id(active_period.worker_id)
            input_dir = Path(f"./workers/{worker.nombre}/{active_period.month_year}/img")
            
            # Show active period info
            st.info(f"📅 Periodo activo: **{format_month_year_display(active_period.month_year)}** - Trabajador: **{worker.nombre}**")
            st.write(f"📁 Directorio: `{input_dir}`")
            
            # Create directory if it doesn't exist
            input_dir.mkdir(parents=True, exist_ok=True)
        else:
            st.warning("⚠️ No hay periodo activo. Se usará el directorio por defecto.")
            input_dir = Path(config.paths.get('input_dir', './img'))
            st.write(f"📁 Directorio: `{input_dir}`")
        
        if st.button("🔄 Scan & Enqueue Images"):
            image_files = get_image_files(str(input_dir))
            count = queue_service.enqueue_batch(image_files)
            st.success(f"Enqueued {count} images")
            st.rerun()
        
        # Warning for large queue
        queue_stats = queue_service.get_queue_stats()
        if queue_stats.get('warning', False):
            st.warning(f"⚠️ Large queue: {queue_stats['pending']} pending items (threshold: {queue_stats['warning_threshold']})")
        
        st.divider()
        
        # Logs section
        st.subheader("📋 Logs")
        
        log_file = Path(config.paths.get('logs_dir', './logs')) / 'processor.log'
        auto_refresh = False
        
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Filter essential lines
                essential_lines = []
                include_next_lines = 0
                
                for line in lines:
                    if include_next_lines > 0:
                        if ' - ' in line:
                            parts = line.split(' - ', 3)
                            if len(parts) >= 4:
                                essential_lines.append(parts[3])
                            else:
                                essential_lines.append(line)
                        else:
                            essential_lines.append(line)
                        include_next_lines -= 1
                        continue
                    
                    if any(marker in line for marker in [
                        'INICIO DEL PROCESO', 'FINALIZACIÓN DEL PROCESO', 'IMAGEN:',
                        'Inicio:', 'Fin:', 'Tiempo:', 'Procesado exitosamente',
                        'ERROR:', 'Guardado como:', 'Datos extraídos:', 'FALTANTE'
                    ]):
                        if ' - ' in line:
                            parts = line.split(' - ', 3)
                            if len(parts) >= 4:
                                essential_lines.append(parts[3])
                            else:
                                essential_lines.append(line)
                        else:
                            essential_lines.append(line)
                        
                        if 'RESUMEN:' in line:
                            include_next_lines = 4
                        elif 'Datos extraídos:' in line:
                            include_next_lines = 3
                    elif line.strip().startswith('===') or line.strip().startswith('---'):
                        essential_lines.append(line)
                
                display_lines = essential_lines[-30:] if len(essential_lines) > 30 else essential_lines
                log_text = ''.join(display_lines) if display_lines else "No hay actividad reciente"
                
                st.text_area("Registro de Actividad", value=log_text, height=250)
                
                refresh_col1, refresh_col2 = st.columns([1, 1])
                with refresh_col1:
                    if st.button("🔄 Refresh Logs"):
                        st.rerun()
                with refresh_col2:
                    auto_refresh = st.checkbox("Auto-refresh (3s)", value=False)
                    
            except Exception as e:
                st.error(f"Error reading logs: {e}")
        else:
            st.info("No log file found yet. Start processing to generate logs.")
        
        if auto_refresh and stats.get('is_running', False):
            time.sleep(3)
            st.rerun()
    
    with col2:
        st.header("📊 Status")
        
        stats = processor.get_stats()
        queue_stats = stats.get('queue', {})
        resource_stats = stats.get('resources', {})
        
        # Status indicators
        status_text = "🟢 Running" if processor._is_running else "🔴 Stopped"
        if processor._is_paused:
            status_text = "🟡 Paused"
        st.metric("Status", status_text)
        
        mode_emoji = "🚀" if resource_stats.get('mode') == 'idle-boost' else "🐢"
        st.metric("Mode", f"{mode_emoji} {resource_stats.get('mode', 'normal').title()}")
        
        st.divider()
        
        st.subheader("Queue")
        st.metric("Pending", queue_stats.get('pending', 0))
        st.metric("Processing", queue_stats.get('processing', 0))
        st.metric("Completed", queue_stats.get('completed', 0))
        st.metric("Failed", queue_stats.get('failed', 0))
        
        st.divider()
        
        st.subheader("Resources")
        st.metric("CPU", f"{resource_stats.get('cpu_percent', 0):.1f}%")
        st.metric("RAM", f"{resource_stats.get('ram_percent', 0):.1f}%")
        st.metric("RAM Used", f"{resource_stats.get('ram_used_gb', 0):.2f} GB")
    
    # Progress and ETA
    st.divider()
    
    if processor._is_running:
        total = queue_stats.get('pending', 0) + queue_stats.get('completed', 0)
        completed = queue_stats.get('completed', 0)
        
        if total > 0:
            progress = completed / total
            st.progress(progress, text=f"Progress: {completed}/{total} images")
            
            if 'start_time' not in st.session_state:
                st.session_state.start_time = None
            
            if st.session_state.start_time is None:
                st.session_state.start_time = datetime.now()
            
            if completed > 0:
                elapsed = (datetime.now() - st.session_state.start_time).total_seconds()
                if elapsed > 0:
                    rate = completed / elapsed
                    remaining = queue_stats.get('pending', 0)
                    if rate > 0 and remaining > 0:
                        eta_seconds = remaining / rate
                        eta_minutes = int(eta_seconds / 60)
                        eta_seconds_remainder = int(eta_seconds % 60)
                        st.caption(f"⏱️ ETA: {eta_minutes}m {eta_seconds_remainder}s | Rate: {rate*60:.1f} items/min")
    else:
        if 'start_time' in st.session_state:
            st.session_state.start_time = None
    
    # Auto-refresh when running
    if processor._is_running:
        time.sleep(2)
        st.rerun()
