"""Admin page for system management."""
import streamlit as st
from pathlib import Path
import shutil
from datetime import datetime
import sqlite3

from src.core.database import get_database, Database
from src.core.backup_manager import BackupManager


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
                    st.caption(mtime.strftime("%Y-%m-%d %H:%M"))
            
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
