"""Failed items management module."""
import streamlit as st
from pathlib import Path
from src.utils.log_parser import LogParser


def render():
    """Render failed items management page."""
    st.header("❌ Items Fallidos")
    
    # Check if services are initialized
    if 'queue_service' not in st.session_state:
        st.error("⚠️ Queue service not initialized. Please go to Processor page first.")
        return
    
    if 'config' not in st.session_state:
        st.error("⚠️ Configuration not loaded.")
        return
    
    queue_service = st.session_state.queue_service
    config = st.session_state.config
    
    # Get failed items
    failed_items = queue_service.get_failed_items()
    
    if not failed_items:
        st.success("✅ No hay items fallidos en la cola")
        return
    
    st.warning(f"⚠️ Hay {len(failed_items)} items fallidos")
    
    # Action buttons at the top
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.subheader(f"Total: {len(failed_items)} items")
    
    with col2:
        if st.button("🔄 Reintentar Todos", type="primary", use_container_width=True):
            count = queue_service.retry_all_failed_items()
            st.success(f"✅ {count} items reintentados")
            st.rerun()
    
    with col3:
        if st.button("🔄 Refrescar", use_container_width=True):
            st.rerun()
    
    st.divider()
    
    # Get log file path
    log_file = Path(config.paths.get('logs_dir', './logs')) / 'unified_app.log'
    
    # Display each failed item
    for idx, item in enumerate(failed_items, 1):
        with st.expander(f"❌ Item #{item.id} - {Path(item.file_path).name}", expanded=(idx == 1)):
            # Item details
            col_info, col_actions = st.columns([3, 1])
            
            with col_info:
                st.write(f"**Archivo:** `{item.file_path}`")
                st.write(f"**Intentos:** {item.attempts}/{queue_service.max_attempts}")
                
                if item.created_at:
                    st.write(f"**Creado:** {item.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                
                if item.processed_at:
                    st.write(f"**Último intento:** {item.processed_at.strftime('%Y-%m-%d %H:%M:%S')}")
                
                if item.last_error:
                    st.write(f"**Error almacenado:** `{item.last_error}`")
            
            with col_actions:
                if st.button(f"🔄 Reintentar", key=f"retry_{item.id}", use_container_width=True):
                    if queue_service.retry_failed_item(item.id):
                        st.success(f"✅ Item #{item.id} reintentado")
                        st.rerun()
                    else:
                        st.error(f"❌ Error al reintentar item #{item.id}")
            
            # Parse log for detailed error information
            st.divider()
            st.subheader("📋 Detalles del Log")
            
            filename = Path(item.file_path).name
            error_info = LogParser.parse_error_for_file(log_file, filename)
            
            if error_info:
                # Display formatted error information
                error_display = LogParser.format_error_display(error_info)
                st.text(error_display)
                
                # Show extracted data context if available
                if error_info.get('error_details'):
                    with st.expander("🔍 Ver detalles completos del error"):
                        st.code("\\n".join(error_info['error_details']), language="python")
            else:
                st.info("ℹ️ No se encontró información detallada en el log para este archivo")
            
            # Check if file still exists
            file_path = Path(item.file_path)
            if file_path.exists():
                st.success(f"✅ El archivo existe: {file_path.stat().st_size / 1024:.1f} KB")
            else:
                st.error("❌ El archivo no existe en la ruta especificada")
    
    # Show recent errors from log at the bottom
    st.divider()
    st.subheader("📊 Errores Recientes del Log")
    
    recent_errors = LogParser.get_all_errors(log_file, limit=10)
    
    if recent_errors:
        for error in recent_errors:
            with st.expander(f"⚠️ {error.get('timestamp', 'Unknown time')} - {error.get('filename', 'Unknown file')}"):
                if error.get('error_message'):
                    st.error(f"**Error:** {error['error_message']}")
                
                if error.get('error_details'):
                    st.code("\\n".join(error['error_details'][:5]), language="python")
    else:
        st.info("ℹ️ No se encontraron errores recientes en el log")
