"""Streamlit UI for OCR Processor control."""
import streamlit as st
import time
import logging
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
from src.ocr_processor import BackgroundOCRProcessor
from src.services.queue_service import QueueService
from src.utils.file_helpers import get_image_files


from src.core.logging import setup_logging


def main():
    """Main Streamlit app for processor control."""
    
    st.set_page_config(
        page_title="Receipt Processor",
        page_icon="🖼️",
        layout="wide"
    )
    
    st.title("🖼️ Receipt Processor - Background OCR")
    
    # Setup logging first (before anything else)
    if 'logging_configured' not in st.session_state:
        config = get_config()
        setup_logging(config, app_name="processor", capture_std=True)
        st.session_state.logging_configured = True
    
    # Initialize session state
    if 'processor' not in st.session_state:
        config = get_config()
        st.session_state.processor = BackgroundOCRProcessor()
        st.session_state.queue_service = QueueService(config)
        st.session_state.config = config
    
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
                        # If currently manual, clear override and let auto mode take over
                        processor.resource_monitor.clear_manual_override()
                        st.success("Switched to Automatic mode!")
                    else:
                        # Toggle to opposite mode with manual override
                        new_mode = 'normal' if is_turbo else 'idle-boost'
                        processor.resource_monitor.set_mode(new_mode)
                        st.success(f"Switched to {'Turbo' if new_mode == 'idle-boost' else 'Normal'} mode (Manual)!")
                st.rerun()
        
        st.divider()
        
        # Control buttons
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        
        with btn_col1:
            if st.button("▶️ Start", disabled=processor._is_running, width='stretch'):
                try:
                    processor.start()
                    st.success("Processor started!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to start: {e}")
        
        with btn_col2:
            if processor._is_running:
                if processor._is_paused:
                    if st.button("▶️ Resume", width='stretch'):
                        processor.resume()
                        st.rerun()
                else:
                    if st.button("⏸️ Pause", width='stretch'):
                        processor.pause()
                        st.info("ℹ️ El procesamiento se pausará después de completar el recibo actual")
                        time.sleep(1)
                        st.rerun()
            else:
                st.button("⏸️ Pause", disabled=True, width='stretch')
        
        with btn_col3:
            if st.button("⏹️ Stop", disabled=not processor._is_running, width='stretch'):
                processor.stop(force=True)
                st.warning("⚠️ Procesamiento detenido forzosamente")
                time.sleep(1)
                st.rerun()
        
        st.divider()
        
        # Queue management
        st.subheader("📁 Input Files")
        
        input_dir = st.text_input(
            "Input Directory",
            value=config.paths.get('input_dir', './img'),
            help="Directory containing images to process"
        )
        
        if st.button("🔄 Scan & Enqueue Images"):
            image_files = get_image_files(input_dir)
            count = queue_service.enqueue_batch(image_files)
            st.success(f"Enqueued {count} images")
            st.rerun()
        
        # Warning for large queue
        queue_stats = queue_service.get_queue_stats()
        if queue_stats.get('warning', False):
            st.warning(f"⚠️ Large queue: {queue_stats['pending']} pending items (threshold: {queue_stats['warning_threshold']})")
        
        st.divider()
        
        # Logs section - simplified view
        st.subheader("📋 Logs")
        
        log_file = Path(config.paths.get('logs_dir', './logs')) / 'processor.log'
        auto_refresh = False  # Initialize
        
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Filter for essential info only
                essential_lines = []
                include_next_lines = 0  # Counter for lines to include after a key marker
                
                for line in lines:
                    # Check if we should include this line based on previous context
                    if include_next_lines > 0:
                        # Include this line as part of a multi-line section
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
                    
                    # Keep only lines with key events
                    if any(marker in line for marker in [
                        'INICIO DEL PROCESO',
                        'FINALIZACIÓN DEL PROCESO', 
                        'IMAGEN:',
                        'Inicio:',
                        'Fin:',
                        'Tiempo:',
                        'Procesado exitosamente',
                        'ERROR:',
                        'Guardado como:',
                        'Datos extraídos:',
                        'FALTANTE'
                    ]):
                        # Clean up the line (remove logger prefix)
                        if ' - ' in line:
                            parts = line.split(' - ', 3)
                            if len(parts) >= 4:
                                essential_lines.append(parts[3])
                            else:
                                essential_lines.append(line)
                        else:
                            essential_lines.append(line)
                        
                        # If this is RESUMEN or Datos extraídos, include next 3-4 lines
                        if 'RESUMEN:' in line:
                            include_next_lines = 4  # Total, Tiempo total, Promedio, separator
                        elif 'Datos extraídos:' in line:
                            include_next_lines = 3  # Fecha, Importe, Tipo
                    
                    # Also include separator lines
                    elif line.strip().startswith('===') or line.strip().startswith('---'):
                        essential_lines.append(line)
                
                # Show last 30 essential lines
                display_lines = essential_lines[-30:] if len(essential_lines) > 30 else essential_lines
                log_text = ''.join(display_lines) if display_lines else "No hay actividad reciente"
                
                st.text_area("Registro de Actividad", value=log_text, height=250, help="Eventos principales del procesamiento")
                
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
        
        st.divider()
        
        # Debug logs - collapsible
        # Initialize expander state
        if 'debug_expanded' not in st.session_state:
            st.session_state.debug_expanded = False
        
        with st.expander("🐛 Debug Logs (Detallado)", expanded=st.session_state.debug_expanded):
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        # Read last 100 lines for debug
                        lines = f.readlines()
                        last_lines = lines[-100:] if len(lines) > 100 else lines
                        debug_text = ''.join(last_lines)
                    
                    # Use HTML div with auto-scroll to bottom
                    import time as time_module
                    scroll_id = f"scroll_{int(time_module.time())}"
                    
                    # Create scrollable div with auto-scroll JavaScript
                    st.markdown(
                        f"""
                        <div id="{scroll_id}" style="
                            height: 300px; 
                            overflow-y: scroll; 
                            background-color: #0e1117; 
                            color: #fafafa; 
                            padding: 10px; 
                            border-radius: 5px;
                            font-family: 'Source Code Pro', monospace;
                            font-size: 12px;
                            white-space: pre-wrap;
                            word-wrap: break-word;
                        ">{debug_text}</div>
                        <script>
                            var element = document.getElementById("{scroll_id}");
                            if (element) {{
                                element.scrollTop = element.scrollHeight;
                            }}
                        </script>
                        """,
                        unsafe_allow_html=True
                    )
                        
                except Exception as e:
                    st.error(f"Error reading debug logs: {e}")
            else:
                st.info("No debug logs available yet.")
        
        # Auto-refresh logic (updates entire page including expander content)
        if auto_refresh and stats.get('is_running', False):
            time.sleep(3)
            st.rerun()
    
    with col2:
        st.header("📊 Status")
        
        # Get stats
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
        
        # Queue metrics
        st.subheader("Queue")
        st.metric("Pending", queue_stats.get('pending', 0))
        st.metric("Processing", queue_stats.get('processing', 0))
        st.metric("Completed", queue_stats.get('completed', 0))
        st.metric("Failed", queue_stats.get('failed', 0))
        
        st.divider()
        
        # Resource metrics
        st.subheader("Resources")
        st.metric("CPU", f"{resource_stats.get('cpu_percent', 0):.1f}%")
        st.metric("RAM", f"{resource_stats.get('ram_percent', 0):.1f}%")
        st.metric("RAM Used", f"{resource_stats.get('ram_used_gb', 0):.2f} GB")
    
    # Full-width sections
    st.divider()
    
    # Progress and ETA
    if processor._is_running:
        total = queue_stats.get('pending', 0) + queue_stats.get('completed', 0)
        completed = queue_stats.get('completed', 0)
        
        if total > 0:
            progress = completed / total
            st.progress(progress, text=f"Progress: {completed}/{total} images")
            
            # Calculate ETA based on processing rate
            if 'start_time' not in st.session_state:
                st.session_state.start_time = None
            
            if st.session_state.start_time is None:
                from datetime import datetime
                st.session_state.start_time = datetime.now()
            
            if completed > 0:
                from datetime import datetime
                elapsed = (datetime.now() - st.session_state.start_time).total_seconds()
                if elapsed > 0:
                    rate = completed / elapsed  # items per second
                    remaining = queue_stats.get('pending', 0)
                    if rate > 0 and remaining > 0:
                        eta_seconds = remaining / rate
                        eta_minutes = int(eta_seconds / 60)
                        eta_seconds_remainder = int(eta_seconds % 60)
                        st.caption(f"⏱️ ETA: {eta_minutes}m {eta_seconds_remainder}s | Rate: {rate*60:.1f} items/min")
    else:
        # Reset start time when stopped
        if 'start_time' in st.session_state:
            st.session_state.start_time = None
    
    # # Log viewer
    # st.subheader("📄 Logs")
    
    # log_file = Path(config.paths.get('logs_dir', './logs')) / 'processor.log'
    # if log_file.exists():
    #     with open(log_file, 'r', encoding='utf-8') as f:
    #         # Read last 50 lines
    #         lines = f.readlines()
    #         log_text = ''.join(lines[-50:])
    #         st.text_area("Recent Logs", log_text, height=300)
    # else:
    #     st.info("No logs yet")
    
    # Auto-refresh when running
    if processor._is_running:
        time.sleep(2)
        st.rerun()


if __name__ == "__main__":
    # TODO: Add system tray integration
    # - Create tray icon when app starts
    # - Show/hide window from tray
    # - Keep processing in background when window closed
    
    main()
