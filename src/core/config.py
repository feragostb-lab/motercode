"""Configuration management."""
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for the application."""
    
    def __init__(self, config_path: str = 'config.yaml'):
        """
        Initialize configuration from YAML file.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        self.load()
    
    def load(self):
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {self.config_path}")
        except FileNotFoundError:
            logger.warning(f"Configuration file not found: {self.config_path}")
            self._config = self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self._config = self._get_default_config()
    
    def save(self):
        """Save current configuration to YAML file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated key path.
        
        Args:
            key: Dot-separated key path (e.g., 'processor.threads')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """
        Set configuration value by dot-separated key path.
        
        Args:
            key: Dot-separated key path
            value: Value to set
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'processor': {
                'threads': 8,
                'batch_size': 2048,
                'gpu_layers': 35,
                'max_cpu_percent': 70,
                'max_ram_percent': 70,
                'idle_boost_enabled': True,
                'idle_threshold_minutes': 5,
                'idle_cpu_percent': 95,
                'idle_ram_percent': 95,
                'model_path': './models/Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf',
                'mmproj_path': './models/mmproj-Qwen2.5-VL-7B-Instruct-f16.gguf',
                'context_size': 32768,
                'temperature': 0.1,
                'max_tokens': 512,
                'max_image_size_kb': 150,
                'resource_check_interval_seconds': 5,
            },
            'queue': {
                'max_attempts': 3,
                'warning_threshold': 300,
                'retry_backoff_base_minutes': 2,
            },
            'paths': {
                'input_dir': './img',
                # output_dir is now determined by worker/period (./workers/{worker}/{period}/result)
                'database': './receipts.db',
                'logs_dir': './logs',
                'temp_dir': './temp',
                'backups_dir': './backups',
                'exports_dir': './exports',
                'bank_excel': './img/bankmov/Detalle de Tarjeta de Crédito.xlsx',
            },
            'backup': {
                'enabled': True,
                'retention_days': 7,
                'backup_on_startup': True,
            },
            'notifications': {
                'enabled': True,
                'notify_on_completion': True,
                'notify_on_permanent_failure': True,
                'notify_on_pause': True,
            },
            'logging': {
                'level': 'INFO',
                'max_file_size_mb': 10,
                'backup_count': 5,
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            },
            'receipt_types': [
                'taxis', 'comidas', 'hoteles', 'estacionamiento', 'vuelos',
                'alquiler_coche', 'gasolina', 'tren', 'peajes', 'otros'
            ],
            'matching': {
                'amount_tolerance': 0.02,
                'date_match_exact': True,
            },
        }
    
    @property
    def processor(self) -> Dict[str, Any]:
        """Get processor configuration."""
        return self._config.get('processor', {})
    
    @property
    def queue(self) -> Dict[str, Any]:
        """Get queue configuration."""
        return self._config.get('queue', {})
    
    @property
    def paths(self) -> Dict[str, Any]:
        """Get paths configuration."""
        return self._config.get('paths', {})
    
    @property
    def backup(self) -> Dict[str, Any]:
        """Get backup configuration."""
        return self._config.get('backup', {})
    
    @property
    def notifications(self) -> Dict[str, Any]:
        """Get notifications configuration."""
        return self._config.get('notifications', {})
    
    @property
    def logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self._config.get('logging', {})
    
    @property
    def receipt_types(self) -> list:
        """Get receipt types (legacy - for backward compatibility)."""
        return self._config.get('receipt_types', [])
    
    @property
    def receipt_type_definitions(self) -> Dict[str, Any]:
        """Get receipt type definitions configuration."""
        return self._config.get('receipt_type_definitions', {})
    
    @property
    def matching(self) -> Dict[str, Any]:
        """Get matching configuration."""
        return self._config.get('matching', {})
    
    def reload(self):
        """Reload configuration from file."""
        self.load()
        logger.info("Configuration reloaded")


# Global configuration instance
_config: Optional[Config] = None


def get_config(config_path: str = 'config.yaml') -> Config:
    """
    Get global configuration instance.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config
