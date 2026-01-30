"""Configuration service for managing receipt type definitions."""
import logging
import yaml
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import shutil

from ..models.domain import ReceiptTypeDefinition, FieldDefinition

logger = logging.getLogger(__name__)


class ConfigService:
    """Service for managing receipt type configuration."""
    
    def __init__(self, config_path: str = "./config.yaml"):
        """
        Initialize config service.
        
        Args:
            config_path: Path to config.yaml file
        """
        self.config_path = Path(config_path)
        self._config_data = None
        self._load_config()
        
        # Initialize database connection for system config
        from ..core.config import get_config
        from ..core.database import get_database
        config = get_config(config_path)
        self.db = get_database(config.paths.get('database'))
    
    def _load_config(self):
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config_data = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {self.config_path}")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    def reload_config(self) -> bool:
        """
        Reload configuration from file and invalidate caches.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self._load_config()
            logger.info("Configuration reloaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error reloading configuration: {e}")
            return False
    
    def save_type_definitions(self, type_definitions: List[Dict[str, Any]]) -> tuple[bool, Optional[str]]:
        """
        Save receipt type definitions to config file.
        Creates auto-backup if enabled and cleans old backups.
        
        Args:
            type_definitions: List of type definition dictionaries
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Validate type definitions
            validation_error = self._validate_type_definitions(type_definitions)
            if validation_error:
                return False, validation_error
            
            # Create backup if enabled
            auto_backup = self._config_data.get('receipt_type_definitions', {}).get('auto_backup_on_save', True)
            if auto_backup:
                backup_path = self._create_backup()
                if backup_path:
                    logger.info(f"Created backup: {backup_path}")
                    self._cleanup_old_backups()
            
            # Update type_definitions in config data
            if 'receipt_type_definitions' not in self._config_data:
                self._config_data['receipt_type_definitions'] = {}
            
            self._config_data['receipt_type_definitions']['type_definitions'] = type_definitions
            
            # Write to file
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            # Reload to update internal state
            self._load_config()
            
            logger.info("Type definitions saved successfully")
            return True, None
            
        except Exception as e:
            error_msg = f"Error saving type definitions: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_system_config(self, key: str) -> Optional[str]:
        """
        Get system configuration value.
        
        Args:
            key: Configuration key
            
        Returns:
            Configuration value or None
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            ''')
            cursor.execute('SELECT value FROM system_config WHERE key = ?', (key,))
            row = cursor.fetchone()
            return row['value'] if row else None
    
    def set_system_config(self, key: str, value: Optional[str]):
        """
        Set system configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value (None to delete)
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            ''')
            
            if value is None:
                cursor.execute('DELETE FROM system_config WHERE key = ?', (key,))
            else:
                cursor.execute('''
                    INSERT OR REPLACE INTO system_config (key, value, updated_at)
                    VALUES (?, ?, ?)
                ''', (key, value, datetime.now().isoformat()))
    
    def _validate_type_definitions(self, type_definitions: List[Dict[str, Any]]) -> Optional[str]:
        """
        Validate type definitions for errors.
        
        Args:
            type_definitions: List of type definition dictionaries
            
        Returns:
            Error message if validation fails, None if valid
        """
        seen_names = set()
        direct_indicator_fields = {}
        
        for idx, type_def in enumerate(type_definitions):
            # Validate required fields
            if 'name' not in type_def:
                return f"Type definition at index {idx}: missing 'name' field"
            
            name = type_def['name']
            
            # Validate name length
            if len(name) > 30:
                return f"Type '{name}': name exceeds 30 characters (has {len(name)})"
            
            # Check for duplicate names
            if name in seen_names:
                return f"Duplicate type name: '{name}'"
            seen_names.add(name)
            
            # Validate enabled field
            if 'enabled' not in type_def:
                return f"Type '{name}': missing 'enabled' field"
            
            # Validate direct_indicator
            if 'direct_indicator' in type_def:
                indicator = type_def['direct_indicator']
                if 'field_key' in indicator:
                    field_key = indicator['field_key']
                    # Warn about duplicate direct indicators
                    if field_key in direct_indicator_fields:
                        logger.warning(
                            f"Type '{name}': direct indicator field '{field_key}' "
                            f"also used by type '{direct_indicator_fields[field_key]}'"
                        )
                    direct_indicator_fields[field_key] = name
            
            # Validate auxiliary_fields types
            if 'auxiliary_fields' in type_def:
                for field_key, field_config in type_def['auxiliary_fields'].items():
                    if 'type' in field_config:
                        field_type = field_config['type']
                        if field_type not in ['text', 'number', 'date', 'boolean']:
                            return (
                                f"Type '{name}', field '{field_key}': "
                                f"invalid type '{field_type}' (must be text/number/date/boolean)"
                            )
        
        return None
    
    def _create_backup(self) -> Optional[Path]:
        """
        Create timestamped backup of config file.
        
        Returns:
            Path to backup file, or None if failed
        """
        try:
            backups_dir = Path(self._config_data.get('paths', {}).get('backups_dir', './backups'))
            backups_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"config_{timestamp}.yaml"
            backup_path = backups_dir / backup_filename
            
            shutil.copy2(self.config_path, backup_path)
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None
    
    def _cleanup_old_backups(self):
        """Delete backup files older than retention period."""
        try:
            retention_days = self._config_data.get('receipt_type_definitions', {}).get('backup_retention_days', 30)
            backups_dir = Path(self._config_data.get('paths', {}).get('backups_dir', './backups'))
            
            if not backups_dir.exists():
                return
            
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            deleted_count = 0
            for backup_file in backups_dir.glob('config_*.yaml'):
                try:
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        backup_file.unlink()
                        deleted_count += 1
                except Exception as e:
                    logger.warning(f"Error deleting old backup {backup_file}: {e}")
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old config backups")
                
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")
    
    def export_to_json(self, output_path: str) -> bool:
        """
        Export type definitions to JSON file.
        
        Args:
            output_path: Path for output JSON file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            type_defs = self._config_data.get('receipt_type_definitions', {})
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(type_defs, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported type definitions to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}")
            return False
    
    def export_to_yaml(self, output_path: str) -> bool:
        """
        Export type definitions to YAML file.
        
        Args:
            output_path: Path for output YAML file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            type_defs = self._config_data.get('receipt_type_definitions', {})
            
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(type_defs, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            logger.info(f"Exported type definitions to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to YAML: {e}")
            return False
    
    def import_from_file(self, input_path: str) -> tuple[bool, Optional[str]]:
        """
        Import type definitions from JSON or YAML file.
        
        Args:
            input_path: Path to input file
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            input_path = Path(input_path)
            
            # Load file based on extension
            with open(input_path, 'r', encoding='utf-8') as f:
                if input_path.suffix.lower() == '.json':
                    imported_data = json.load(f)
                else:
                    imported_data = yaml.safe_load(f)
            
            # Validate structure
            if 'type_definitions' not in imported_data:
                return False, "Invalid file format: missing 'type_definitions'"
            
            type_definitions = imported_data['type_definitions']
            
            # Validate type definitions
            validation_error = self._validate_type_definitions(type_definitions)
            if validation_error:
                return False, f"Validation error: {validation_error}"
            
            # Save the imported definitions
            return self.save_type_definitions(type_definitions)
            
        except json.JSONDecodeError as e:
            return False, f"JSON parse error at line {e.lineno}, column {e.colno}: {e.msg}"
        except yaml.YAMLError as e:
            error_msg = f"YAML parse error: {str(e)}"
            if hasattr(e, 'problem_mark'):
                mark = e.problem_mark
                error_msg = f"YAML parse error at line {mark.line + 1}, column {mark.column + 1}: {e.problem}"
            return False, error_msg
        except Exception as e:
            return False, f"Error importing file: {str(e)}"
    
    def get_field_library(self) -> Dict[str, Dict[str, str]]:
        """
        Get the field library for reusable field definitions.
        
        Returns:
            Dictionary of field definitions
        """
        return self._config_data.get('receipt_type_definitions', {}).get('field_library', {})
    
    def generate_field_library_docs(self) -> str:
        """
        Generate formatted documentation for the field library.
        
        Returns:
            Markdown-formatted documentation string
        """
        field_library = self.get_field_library()
        
        if not field_library:
            return "No fields defined in library."
        
        docs = "# Available Fields in Library\n\n"
        docs += "| Field Key | Type | Question | Help Text |\n"
        docs += "|-----------|------|----------|----------|\n"
        
        for field_key, field_config in sorted(field_library.items()):
            field_type = field_config.get('type', 'text')
            question = field_config.get('question', '')
            help_text = field_config.get('help', '')
            
            docs += f"| `{field_key}` | {field_type} | {question} | {help_text} |\n"
        
        return docs
    
    def rebuild_cache(self):
        """
        Manual cache rebuild for troubleshooting.
        This invalidates all cached prompts and scoring rules.
        """
        # Reload configuration
        self._load_config()
        logger.info("Cache rebuilt - configuration reloaded")
    
    def get_type_definitions(self) -> List[ReceiptTypeDefinition]:
        """
        Get all receipt type definitions as domain objects.
        
        Returns:
            List of ReceiptTypeDefinition objects
        """
        type_defs_data = self._config_data.get('receipt_type_definitions', {}).get('type_definitions', [])
        
        type_definitions = []
        for type_data in type_defs_data:
            try:
                type_def = ReceiptTypeDefinition(
                    name=type_data.get('name', ''),
                    enabled=type_data.get('enabled', True),
                    direct_indicator=type_data.get('direct_indicator', {}),
                    auxiliary_fields=type_data.get('auxiliary_fields', {}),
                    keyword_weights=type_data.get('keyword_weights', {}),
                    normalized_type=type_data.get('normalized_type', ''),
                    gl_account=type_data.get('gl_account', '')
                )
                type_definitions.append(type_def)
            except Exception as e:
                logger.error(f"Error parsing type definition '{type_data.get('name', 'unknown')}': {e}")
        
        return type_definitions
    
    def get_enabled_type_definitions(self) -> List[ReceiptTypeDefinition]:
        """
        Get only enabled receipt type definitions.
        
        Returns:
            List of enabled ReceiptTypeDefinition objects
        """
        all_types = self.get_type_definitions()
        return [t for t in all_types if t.enabled]
    
    def get_common_fields(self) -> Dict[str, Dict[str, str]]:
        """
        Get common fields shared by all receipt types.
        
        Returns:
            Dictionary of common field definitions
        """
        return self._config_data.get('receipt_type_definitions', {}).get('common_fields', {})
