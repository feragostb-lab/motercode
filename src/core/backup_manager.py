"""Backup manager for database files."""
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages automatic backups of the database."""
    
    def __init__(self, db_path: str, backup_dir: str = './backups', 
                 retention_days: int = 7):
        """
        Initialize backup manager.
        
        Args:
            db_path: Path to database file
            backup_dir: Directory to store backups
            retention_days: Number of days to keep backups
        """
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.retention_days = retention_days
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self) -> Optional[str]:
        """
        Create a backup of the database.
        
        Returns:
            Path to backup file or None if failed
        """
        if not self.db_path.exists():
            logger.warning(f"Database file not found: {self.db_path}")
            return None
        
        try:
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"{self.db_path.stem}_{timestamp}{self.db_path.suffix}"
            backup_path = self.backup_dir / backup_filename
            
            # Copy database file
            shutil.copy2(self.db_path, backup_path)
            
            logger.info(f"Database backup created: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def cleanup_old_backups(self):
        """Remove backups older than retention_days."""
        if self.retention_days <= 0:
            return
        
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        deleted_count = 0
        
        try:
            for backup_file in self.backup_dir.glob(f"{self.db_path.stem}_*{self.db_path.suffix}"):
                # Get file modification time
                mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
                
                if mtime < cutoff_date:
                    backup_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old backup: {backup_file}")
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old backup(s)")
                
        except Exception as e:
            logger.error(f"Error during backup cleanup: {e}")
    
    def perform_backup_with_cleanup(self) -> Optional[str]:
        """
        Create backup and cleanup old backups.
        
        Returns:
            Path to new backup file or None if failed
        """
        backup_path = self.create_backup()
        if backup_path:
            self.cleanup_old_backups()
        return backup_path
    
    def list_backups(self) -> list:
        """
        List all existing backups.
        
        Returns:
            List of backup file paths, sorted by date (newest first)
        """
        backups = list(self.backup_dir.glob(f"{self.db_path.stem}_*{self.db_path.suffix}"))
        return sorted(backups, key=lambda x: x.stat().st_mtime, reverse=True)
    
    def restore_backup(self, backup_path: str) -> bool:
        """
        Restore database from backup.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if successful, False otherwise
        """
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        try:
            # Create backup of current database before restoring
            if self.db_path.exists():
                emergency_backup = self.db_path.with_suffix('.db.emergency')
                shutil.copy2(self.db_path, emergency_backup)
                logger.info(f"Emergency backup created: {emergency_backup}")
            
            # Restore from backup
            shutil.copy2(backup_file, self.db_path)
            logger.info(f"Database restored from backup: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False
