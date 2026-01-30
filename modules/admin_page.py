"""Admin page for system management."""
import streamlit as st
from pathlib import Path
import shutil
from datetime import datetime
import sqlite3
import json
import tempfile

from src.core.database import get_database, Database
from src.core.backup_manager import BackupManager
from src.services.config_service import ConfigService
from src.models.domain import TypeScoreDetail


def render():
    """Render admin page."""
    st.title("⚙️ Administración del Sistema")
    
    st.warning("⚠️ **ZONA DE ADMINISTRACIÓN** - Las acciones aquí son irreversibles")
    
    # System info
    st.subheader("📊 Información del Sistema")
    
    config = st.session_state.config
    db = st.session_state.database
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Base de Datos", config.paths.get('database', './receipts.db'))
        
        # Count workers
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM workers")
            worker_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM periods")
            period_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM receipts")
            receipt_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bank_transactions")
            transaction_count = cursor.fetchone()[0]
        
        st.metric("Trabajadores", worker_count)
        st.metric("Periodos", period_count)
    
    with col2:
        workers_dir = Path("./workers")
        if workers_dir.exists():
            worker_dirs = [d for d in workers_dir.iterdir() if d.is_dir()]
            st.metric("Directorios de Trabajadores", len(worker_dirs))
        else:
            st.metric("Directorios de Trabajadores", 0)
        
        st.metric("Recibos", receipt_count)
        st.metric("Transacciones", transaction_count)
    
    st.divider()
    
    # Reset options
    st.subheader("🗑️ Opciones de Reseteo")
    
    # Database reset
    with st.expander("🔴 RESETEAR BASE DE DATOS COMPLETA", expanded=False):
        st.error("**PELIGRO:** Esta acción eliminará TODOS los datos de la base de datos:")
        st.write("- ❌ Todos los trabajadores")
        st.write("- ❌ Todos los periodos")
        st.write("- ❌ Todos los recibos procesados")
        st.write("- ❌ Todas las transacciones bancarias")
        st.write("- ❌ Todos los matches")
        st.write("- ❌ Todo el historial")
        
        st.info("✅ Se creará un backup automático antes de resetear")
        
        confirm_db = st.checkbox("Entiendo que esta acción es irreversible", key="confirm_db_reset")
        
        if confirm_db:
            verification_text = st.text_input(
                "Escribe 'RESETEAR BASE DE DATOS' para confirmar:",
                key="verify_db_reset"
            )
            
            if st.button("🔴 RESETEAR BASE DE DATOS", type="primary", disabled=verification_text != "RESETEAR BASE DE DATOS"):
                with st.spinner("Creando backup..."):
                    try:
                        # Reset database
                        db_path = Path(config.paths.get('database', './receipts.db'))
                        backup_dir = Path(config.paths.get('backups_dir', './backups'))
                        
                        # Create backup
                        backup_manager = BackupManager(str(db_path), str(backup_dir))
                        backup_path = backup_manager.create_backup()
                        st.success(f"✅ Backup creado: {backup_path}")
                        
                        # Delete database file
                        if db_path.exists():
                            db_path.unlink()
                            st.success("✅ Base de datos eliminada")
                        
                        # Recreate database with schema
                        from src.core.database import Database
                        new_db = Database(str(db_path))
                        st.success("✅ Nueva base de datos creada")
                        
                        # Update session state
                        st.session_state.database = new_db
                        
                        st.balloons()
                        st.success("🎉 Base de datos reseteada exitosamente!")
                        st.info("Recarga la página para ver los cambios")
                        
                    except Exception as e:
                        st.error(f"❌ Error al resetear base de datos: {e}")
    
    st.divider()
    
    # Workers directory cleanup
    with st.expander("🔴 LIMPIAR DIRECTORIOS DE TRABAJADORES", expanded=False):
        st.error("**PELIGRO:** Esta acción eliminará TODOS los archivos de trabajadores:")
        st.write("- ❌ Todas las imágenes de recibos")
        st.write("- ❌ Todos los archivos CSV bancarios")
        st.write("- ❌ Todos los resultados procesados")
        st.write("- ❌ Toda la estructura de directorios `./workers/`")
        
        st.warning("⚠️ Esta acción NO afecta la base de datos")
        
        workers_dir = Path("./workers")
        if workers_dir.exists():
            # Count files
            total_files = sum(1 for _ in workers_dir.rglob('*') if _.is_file())
            total_size = sum(f.stat().st_size for f in workers_dir.rglob('*') if f.is_file())
            
            st.info(f"📁 Archivos totales: {total_files} ({total_size / (1024*1024):.2f} MB)")
        
        confirm_dirs = st.checkbox("Entiendo que esta acción es irreversible", key="confirm_dirs_reset")
        
        if confirm_dirs:
            verification_text = st.text_input(
                "Escribe 'ELIMINAR TODO' para confirmar:",
                key="verify_dirs_reset"
            )
            
            if st.button("🔴 ELIMINAR DIRECTORIOS", type="primary", disabled=verification_text != "ELIMINAR TODO"):
                with st.spinner("Eliminando directorios..."):
                    try:
                        workers_dir = Path("./workers")
                        if workers_dir.exists():
                            shutil.rmtree(workers_dir)
                            st.success("✅ Directorios de trabajadores eliminados")
                        else:
                            st.info("ℹ️ No hay directorios de trabajadores para eliminar")
                        
                        st.balloons()
                        st.success("🎉 Directorios limpiados exitosamente!")
                        
                    except Exception as e:
                        st.error(f"❌ Error al limpiar directorios: {e}")
    
    st.divider()
    
    # Full system reset
    with st.expander("🔴🔴 RESETEO COMPLETO DEL SISTEMA 🔴🔴", expanded=False):
        st.error("**MÁXIMO PELIGRO:** Esta acción resetea COMPLETAMENTE el sistema:")
        st.write("- ❌ Base de datos completa")
        st.write("- ❌ Todos los directorios de trabajadores")
        st.write("- ❌ El sistema volverá al estado inicial")
        
        st.info("✅ Se creará un backup completo antes de resetear")
        
        confirm_full = st.checkbox("Entiendo las consecuencias de esta acción", key="confirm_full_reset")
        
        if confirm_full:
            verification_text = st.text_input(
                "Escribe 'RESETEO COMPLETO' para confirmar:",
                key="verify_full_reset"
            )
            
            if st.button("🔴🔴 RESETEAR TODO EL SISTEMA 🔴🔴", type="primary", disabled=verification_text != "RESETEO COMPLETO"):
                with st.spinner("Realizando reseteo completo..."):
                    try:
                        # Reset database
                        db_path = Path(config.paths.get('database', './receipts.db'))
                        backup_dir = Path(config.paths.get('backups_dir', './backups'))
                        
                        # Create backup
                        backup_manager = BackupManager(str(db_path), str(backup_dir))
                        backup_path = backup_manager.create_backup()
                        st.success(f"✅ Backup creado: {backup_path}")
                        
                        # Delete database file
                        if db_path.exists():
                            db_path.unlink()
                            st.success("✅ Base de datos eliminada")
                        
                        # Recreate database
                        from src.core.database import Database
                        new_db = Database(str(db_path))
                        st.success("✅ Nueva base de datos creada")
                        
                        # Update session state
                        st.session_state.database = new_db
                        
                        # Delete workers directories
                        workers_dir = Path("./workers")
                        if workers_dir.exists():
                            shutil.rmtree(workers_dir)
                            st.success("✅ Directorios de trabajadores eliminados")
                        
                        # Clean queue
                        queue_dir = Path("./temp")
                        if queue_dir.exists():
                            for f in queue_dir.glob('*'):
                                if f.is_file():
                                    f.unlink()
                            st.success("✅ Cola de procesamiento limpiada")
                        
                        st.balloons()
                        st.success("🎉 Sistema completamente reseteado!")
                        st.info("🔄 Recarga la página para comenzar desde cero")
                        
                    except Exception as e:
                        st.error(f"❌ Error durante el reseteo: {e}")
    
    st.divider()
    
    # Backup management
    st.subheader("💾 Gestión de Backups")
    
    backup_dir = Path(config.paths.get('backups_dir', './backups'))
    if backup_dir.exists():
        backups = sorted(backup_dir.glob('receipts_*.db'), reverse=True)
        
        if backups:
            st.write(f"**Backups disponibles:** {len(backups)}")
            
            for backup in backups[:10]:  # Show last 10
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"📦 {backup.name}")
                with col2:
                    size_mb = backup.stat().st_size / (1024 * 1024)
                    st.write(f"{size_mb:.2f} MB")
                with col3:
                    mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                    st.caption(mtime.strftime("%d-%m-%Y %H:%M"))
            
            if len(backups) > 10:
                st.caption(f"... y {len(backups) - 10} backups más antiguos")
        else:
            st.info("No hay backups disponibles")
    else:
        st.info("No hay directorio de backups")
    
    # Manual backup
    if st.button("💾 Crear Backup Manual"):
        with st.spinner("Creando backup..."):
            try:
                db_path = Path(config.paths.get('database', './receipts.db'))
                backup_dir = Path(config.paths.get('backups_dir', './backups'))
                backup_manager = BackupManager(str(db_path), str(backup_dir))
                backup_path = backup_manager.create_backup()
                st.success(f"✅ Backup creado: {backup_path}")
            except Exception as e:
                st.error(f"❌ Error al crear backup: {e}")
    
    st.divider()
    
    # Receipt Types Configuration
    render_receipt_types_config()


def render_receipt_types_config():
    """Render receipt types configuration section."""
    st.subheader("📝 Configuración de Tipos de Recibo")
    
    st.info(
        "💡 **Recomendación:** Exporta manualmente la configuración antes de realizar cambios importantes. "
        "Usa la función Importar/Exportar para guardar versiones de tu configuración."
    )
    
    # Initialize config service
    if 'config_service' not in st.session_state:
        st.session_state.config_service = ConfigService()
    
    config_service = st.session_state.config_service
    
    # Auto-backup settings
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    
    with col1:
        auto_backup = st.toggle(
            "Auto-backup al guardar",
            value=True,
            help="Crear backup automático antes de guardar cambios"
        )
    
    with col2:
        retention_days = st.number_input(
            "Días de retención",
            min_value=1,
            max_value=365,
            value=30,
            help="Días para mantener backups antiguos"
        )
    
    with col3:
        if st.button("🔄 Reconstruir Caché", help="Recargar configuración y limpiar cachés"):
            config_service.rebuild_cache()
            st.success("✅ Caché reconstruida")
            st.rerun()
    
    with col4:
        if st.button("📖 Ver Librería de Campos"):
            st.session_state.show_field_library = not st.session_state.get('show_field_library', False)
    
    # Field library documentation
    if st.session_state.get('show_field_library', False):
        with st.expander("📚 Librería de Campos Disponibles", expanded=True):
            field_library = config_service.get_field_library()
            
            if field_library:
                st.markdown("**Campos reutilizables disponibles para configuración de tipos:**")
                st.caption("Edita estos campos directamente en config.yaml")
                
                # Create DataFrame for display
                library_data = []
                for field_key, field_config in sorted(field_library.items()):
                    library_data.append({
                        'Campo': f"`{field_key}`",
                        'Tipo': field_config.get('type', 'text'),
                        'Pregunta': field_config.get('question', ''),
                        'Ayuda': field_config.get('help', '')
                    })
                
                st.dataframe(library_data, use_container_width=True, hide_index=True)
            else:
                st.info("No hay campos en la librería")
    
    # Import/Export section
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        if st.button("📤 Exportar Configuración (JSON)"):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                success = config_service.export_to_json(f.name)
                if success:
                    with open(f.name, 'r', encoding='utf-8') as rf:
                        json_data = rf.read()
                    st.download_button(
                        label="⬇️ Descargar JSON",
                        data=json_data,
                        file_name=f"receipt_types_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
    
    with col_exp2:
        uploaded_file = st.file_uploader(
            "📥 Importar Configuración",
            type=['json', 'yaml', 'yml'],
            help="Importar tipos desde archivo JSON o YAML"
        )
        
        if uploaded_file is not None:
            with tempfile.NamedTemporaryFile(mode='wb', suffix=uploaded_file.name, delete=False) as f:
                f.write(uploaded_file.getvalue())
                temp_path = f.name
            
            success, error_msg = config_service.import_from_file(temp_path)
            
            if success:
                st.success("✅ Configuración importada correctamente")
                st.rerun()
            else:
                st.error(f"❌ Error al importar: {error_msg}")
    
    st.divider()
    
    # Types list
    st.subheader("📋 Tipos Configurados")
    
    type_definitions = config_service.get_type_definitions()
    
    # Summary stats
    enabled_count = sum(1 for t in type_definitions if t.enabled)
    disabled_count = len(type_definitions) - enabled_count
    
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    col_stat1.metric("Total de Tipos", len(type_definitions))
    col_stat2.metric("Habilitados", enabled_count)
    col_stat3.metric("Deshabilitados", disabled_count)
    
    # Types table
    for idx, type_def in enumerate(type_definitions):
        with st.expander(
            f"{'✅' if type_def.enabled else '❌'} **{type_def.name}** "
            f"(Max Score: {type_def.calculate_max_score()})",
            expanded=False
        ):
            render_type_editor(type_def, idx, config_service)
    
    # Add new type
    st.divider()
    
    if st.button("➕ Añadir Nuevo Tipo"):
        st.session_state.adding_new_type = True
    
    if st.session_state.get('adding_new_type', False):
        render_new_type_form(config_service, type_definitions)


def render_type_editor(type_def, idx, config_service):
    """Render editor for a single receipt type."""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        new_name = st.text_input(
            "Nombre del Tipo",
            value=type_def.name,
            max_chars=30,
            key=f"name_{idx}",
            help="Máximo 30 caracteres. NOTA: Renombrar crea un NUEVO tipo sin migrar recibos existentes."
        )
    
    with col2:
        enabled = st.toggle(
            "Habilitado",
            value=type_def.enabled,
            key=f"enabled_{idx}"
        )
    
    # Additional fields: Normalized Type and GL Account
    col_nt, col_gl = st.columns(2)
    
    with col_nt:
        normalized_type = st.text_input(
            "Normalized Type",
            value=type_def.normalized_type,
            max_chars=50,
            key=f"normalized_type_{idx}",
            help="Tipo normalizado para exportación"
        )
    
    with col_gl:
        gl_account = st.text_input(
            "GL Account",
            value=type_def.gl_account,
            max_chars=20,
            key=f"gl_account_{idx}",
            help="Cuenta contable (formato: xxxxxxxx)"
        )
    
    st.write("**Indicador Directo** (Pregunta principal - peso recomendado: 8-15)")
    
    col_di1, col_di2, col_di3 = st.columns([2, 3, 1])
    
    with col_di1:
        di_field = st.text_input(
            "Campo clave",
            value=type_def.direct_indicator.get('field_key', ''),
            key=f"di_field_{idx}"
        )
    
    with col_di2:
        di_question = st.text_input(
            "Pregunta",
            value=type_def.direct_indicator.get('question', ''),
            key=f"di_question_{idx}"
        )
    
    with col_di3:
        di_weight = st.number_input(
            "Peso",
            min_value=0,
            value=type_def.direct_indicator.get('weight', 10),
            key=f"di_weight_{idx}",
            help="Recomendado: 8-15"
        )
        
        if di_weight < 5:
            st.warning("⚠️ Peso bajo")
    
    st.write("**Campos Auxiliares** (Peso recomendado: 1-3 por campo)")
    
    # Display existing auxiliary fields
    aux_fields = type_def.auxiliary_fields.copy()
    
    fields_to_delete = []
    
    for field_idx, (field_key, field_config) in enumerate(aux_fields.items()):
        col_f1, col_f2, col_f3, col_f4, col_f5, col_f6 = st.columns([2, 3, 1, 1, 2, 1])
        
        with col_f1:
            st.text_input(
                "Campo",
                value=field_key,
                key=f"aux_field_{idx}_{field_idx}",
                disabled=True
            )
        
        with col_f2:
            st.text_input(
                "Pregunta",
                value=field_config.get('question', ''),
                key=f"aux_q_{idx}_{field_idx}",
                disabled=True
            )
        
        with col_f3:
            st.number_input(
                "Peso",
                value=field_config.get('weight', 1),
                key=f"aux_w_{idx}_{field_idx}",
                disabled=True
            )
        
        with col_f4:
            st.selectbox(
                "Tipo",
                ['text', 'number', 'date', 'boolean'],
                index=['text', 'number', 'date', 'boolean'].index(field_config.get('type', 'text')),
                key=f"aux_t_{idx}_{field_idx}",
                disabled=True
            )
        
        with col_f5:
            st.text_input(
                "Ayuda",
                value=field_config.get('help', ''),
                key=f"aux_h_{idx}_{field_idx}",
                disabled=True
            )
        
        with col_f6:
            if st.button("🗑️", key=f"del_aux_{idx}_{field_idx}"):
                fields_to_delete.append(field_key)
    
    st.caption("📝 Para editar campos, modifica directamente el archivo config.yaml o usa Importar/Exportar")
    
    st.write("**Palabras Clave** (Peso recomendado: 3-8 por palabra)")
    
    keywords = type_def.keyword_weights.copy()
    
    for kw_idx, (keyword, weight) in enumerate(keywords.items()):
        col_kw1, col_kw2 = st.columns([3, 1])
        
        with col_kw1:
            st.text_input(
                "Palabra clave",
                value=keyword,
                key=f"kw_{idx}_{kw_idx}",
                disabled=True
            )
        
        with col_kw2:
            st.number_input(
                "Peso",
                value=weight,
                key=f"kw_w_{idx}_{kw_idx}",
                disabled=True
            )
    
    st.caption("📝 Para modificar palabras clave, edita config.yaml")
    
    # Save changes button
    st.divider()
    
    col_save, col_delete = st.columns([1, 1])
    
    with col_save:
        if st.button(f"💾 Guardar Cambios", key=f"save_{idx}", type="primary"):
            # Get all current type definitions
            all_types = config_service.get_type_definitions()
            
            # Update this specific type with new values from form
            for t in all_types:
                if t.name == type_def.name:
                    # Update basic fields
                    t.name = new_name
                    t.enabled = enabled
                    t.normalized_type = normalized_type
                    t.gl_account = gl_account
                    
                    # Update direct indicator
                    t.direct_indicator = {
                        'field_key': di_field,
                        'question': di_question,
                        'weight': di_weight
                    }
                    break
            
            # Convert to dict and save
            type_defs_data = [t.to_dict() for t in all_types]
            success, error = config_service.save_type_definitions(type_defs_data)
            
            if success:
                st.success(f"✅ Cambios guardados para '{new_name}'")
                st.rerun()
            else:
                st.error(f"❌ Error al guardar: {error}")
    
    with col_delete:
        if st.button(f"🗑️ Eliminar Tipo", key=f"delete_{idx}", type="secondary"):
            st.session_state[f'confirm_delete_{idx}'] = True
    
    if st.session_state.get(f'confirm_delete_{idx}', False):
        st.warning(f"⚠️ ¿Estás seguro de eliminar el tipo **{type_def.name}**?")
        
        # Check if there are receipts with this type
        db = st.session_state.database
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM receipts WHERE receipt_type = ?", (type_def.name,))
            receipt_count = cursor.fetchone()[0]
        
        if receipt_count > 0:
            st.error(f"⚠️ Hay {receipt_count} recibos con este tipo")
            
            # Offer reclassification
            other_types = [t.name for t in config_service.get_type_definitions() if t.name != type_def.name]
            
            new_type = st.selectbox(
                "Reclasificar a:",
                options=other_types,
                key=f"reclassify_{idx}"
            )
            
            if st.button(f"✅ Confirmar eliminación y reclasificar", key=f"confirm_del_{idx}"):
                # Update receipts
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE receipts SET receipt_type = ? WHERE receipt_type = ?",
                        (new_type, type_def.name)
                    )
                    conn.commit()
                
                # Disable type (soft delete)
                all_types = config_service.get_type_definitions()
                for t in all_types:
                    if t.name == type_def.name:
                        t.enabled = False
                
                type_defs_data = [t.to_dict() for t in all_types]
                success, error = config_service.save_type_definitions(type_defs_data)
                
                if success:
                    st.success(f"✅ Tipo eliminado y {receipt_count} recibos reclasificados")
                    del st.session_state[f'confirm_delete_{idx}']
                    st.rerun()
                else:
                    st.error(f"❌ Error: {error}")
        else:
            if st.button(f"✅ Confirmar eliminación", key=f"confirm_del_no_receipts_{idx}"):
                # Disable type
                all_types = config_service.get_type_definitions()
                for t in all_types:
                    if t.name == type_def.name:
                        t.enabled = False
                
                type_defs_data = [t.to_dict() for t in all_types]
                success, error = config_service.save_type_definitions(type_defs_data)
                
                if success:
                    st.success("✅ Tipo eliminado")
                    del st.session_state[f'confirm_delete_{idx}']
                    st.rerun()
                else:
                    st.error(f"❌ Error: {error}")


def render_new_type_form(config_service, existing_types):
    """Render form for adding a new receipt type."""
    st.subheader("➕ Crear Nuevo Tipo")
    
    # Clone from template
    template_names = [t.name for t in existing_types]
    clone_from = st.selectbox(
        "Clonar desde plantilla (opcional)",
        options=["-- Tipo vacío --"] + template_names,
        key="clone_template"
    )
    
    st.write("**Nota:** Actualmente solo se puede crear la estructura básica. "
             "Para añadir campos auxiliares y palabras clave, edita config.yaml después de crear el tipo.")
    
    if st.button("❌ Cancelar"):
        st.session_state.adding_new_type = False
        st.rerun()
    
    st.caption("💡 Después de crear el tipo base, puedes editarlo en config.yaml para añadir campos auxiliares completos")


def render_receipt_types_config():
    """Render receipt types configuration section."""
    st.subheader("📝 Configuración de Tipos de Recibo")
    
    st.info(
        "💡 **Gestión de tipos:** Esta sección permite ver la configuración de tipos de recibo. "
        "Para modificaciones avanzadas (campos auxiliares, palabras clave), edita directamente config.yaml "
        "y usa el botón 'Reconstruir Caché' para recargar los cambios."
    )
    
    # Initialize config service
    if 'config_service' not in st.session_state:
        st.session_state.config_service = ConfigService()
    
    config_service = st.session_state.config_service
    
    # Control buttons
    col1, col2, col3 = st.columns([2, 2, 2])
    
    with col1:
        if st.button("🔄 Reconstruir Caché", help="Recargar configuración desde config.yaml"):
            config_service.rebuild_cache()
            # Invalidate caches in receipt service (OCR processor no longer uses cache)
            if 'receipt_service' in st.session_state:
                st.session_state.receipt_service.invalidate_scoring_cache()
            st.success("✅ Caché reconstruida y configuración recargada")
            st.rerun()
    
    with col2:
        if st.button("📖 Ver Librería de Campos"):
            st.session_state.show_field_library = not st.session_state.get('show_field_library', False)
    
    with col3:
        if st.button("📤 Exportar Config"):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                success = config_service.export_to_yaml(f.name)
                if success:
                    with open(f.name, 'r', encoding='utf-8') as rf:
                        yaml_data = rf.read()
                    st.download_button(
                        label="⬇️ Descargar YAML",
                        data=yaml_data,
                        file_name=f"receipt_types_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml",
                        mime="text/yaml"
                    )
    
    # Field library
    if st.session_state.get('show_field_library', False):
        with st.expander("📚 Librería de Campos Disponibles", expanded=True):
            field_library = config_service.get_field_library()
            
            if field_library:
                st.markdown("**Campos reutilizables (definidos en config.yaml):**")
                
                library_data = []
                for field_key, field_config in sorted(field_library.items()):
                    library_data.append({
                        'Campo': f"`{field_key}`",
                        'Tipo': field_config.get('type', 'text'),
                        'Pregunta': field_config.get('question', ''),
                        'Ayuda': field_config.get('help', '')
                    })
                
                st.dataframe(library_data, use_container_width=True, hide_index=True)
            else:
                st.info("No hay campos en la librería")
    
    st.divider()
    
    # Types list
    st.subheader("📋 Tipos Configurados")
    
    type_definitions = config_service.get_type_definitions()
    
    # Summary stats
    enabled_count = sum(1 for t in type_definitions if t.enabled)
    disabled_count = len(type_definitions) - enabled_count
    
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    col_stat1.metric("Total de Tipos", len(type_definitions))
    col_stat2.metric("Habilitados", enabled_count)
    col_stat3.metric("Deshabilitados", disabled_count)
    
    # Types table - simplified view
    for idx, type_def in enumerate(type_definitions):
        status_icon = "✅" if type_def.enabled else "❌"
        max_score = type_def.calculate_max_score()
        
        with st.expander(
            f"{status_icon} **{type_def.name}** (Score máximo: {max_score})",
            expanded=False
        ):
            col_info1, col_info2 = st.columns(2)
            
            with col_info1:
                st.write(f"**Estado:** {'Habilitado' if type_def.enabled else 'Deshabilitado'}")
                st.write(f"**Indicador Directo:**")
                if type_def.direct_indicator:
                    di = type_def.direct_indicator
                    st.code(f"{di.get('field_key', 'N/A')}: {di.get('question', 'N/A')} (peso: {di.get('weight', 0)})")
                else:
                    st.caption("Sin indicador directo")
            
            with col_info2:
                st.write(f"**Campos Auxiliares:** {len(type_def.auxiliary_fields)}")
                if type_def.auxiliary_fields:
                    for field_key, field_config in list(type_def.auxiliary_fields.items())[:3]:
                        st.caption(f"• {field_key} (peso: {field_config.get('weight', 0)})")
                    if len(type_def.auxiliary_fields) > 3:
                        st.caption(f"... y {len(type_def.auxiliary_fields) - 3} más")
                
                st.write(f"**Palabras Clave:** {len(type_def.keyword_weights)}")
                if type_def.keyword_weights:
                    keywords_text = ", ".join(list(type_def.keyword_weights.keys())[:5])
                    st.caption(keywords_text)
                    if len(type_def.keyword_weights) > 5:
                        st.caption(f"... y {len(type_def.keyword_weights) - 5} más")
            
            st.info("💡 Para modificar este tipo, edita config.yaml y usa 'Reconstruir Caché'")
    
    st.divider()
    st.caption("🔧 **Gestión Avanzada:** Edita config.yaml para modificar campos, pesos y palabras clave. "
               "Usa Export para guardar backups de tu configuración.")
