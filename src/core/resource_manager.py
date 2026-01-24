"""Resource monitoring and management for optimal system usage."""
import psutil
import threading
import time
import ctypes
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)


class ResourceMonitor:
    """Monitors and adjusts system resource usage."""
    
    def __init__(self, max_cpu_percent: float = 70, max_ram_percent: float = 70,
                 idle_boost_enabled: bool = True, idle_threshold_minutes: int = 5,
                 idle_cpu_percent: float = 95, idle_ram_percent: float = 95,
                 check_interval_seconds: int = 5):
        """
        Initialize resource monitor.
        
        Args:
            max_cpu_percent: Maximum CPU usage in normal mode
            max_ram_percent: Maximum RAM usage in normal mode
            idle_boost_enabled: Enable automatic boost when system is idle
            idle_threshold_minutes: Minutes of inactivity to trigger idle mode
            idle_cpu_percent: CPU usage limit in idle mode
            idle_ram_percent: RAM usage limit in idle mode
            check_interval_seconds: How often to check resources
        """
        self.max_cpu_percent = max_cpu_percent
        self.max_ram_percent = max_ram_percent
        self.idle_boost_enabled = idle_boost_enabled
        self.idle_threshold_minutes = idle_threshold_minutes
        self.idle_cpu_percent = idle_cpu_percent
        self.idle_ram_percent = idle_ram_percent
        self.check_interval_seconds = check_interval_seconds
        
        self._is_monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._current_mode = "normal"  # "normal" or "idle-boost"
        self._manual_override = False  # True if user manually set mode
        self._adjustment_callback: Optional[Callable] = None
    
    def start_monitoring(self, adjustment_callback: Optional[Callable] = None):
        """
        Start resource monitoring in background thread.
        
        Args:
            adjustment_callback: Function to call when mode changes
        """
        if self._is_monitoring:
            logger.warning("Resource monitoring already running")
            return
        
        self._adjustment_callback = adjustment_callback
        self._is_monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Resource monitoring started")
    
    def stop_monitoring(self):
        """Stop resource monitoring."""
        self._is_monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=self.check_interval_seconds + 1)
        logger.info("Resource monitoring stopped")
    
    def set_mode(self, mode: str):
        """
        Manually set resource mode.
        
        Args:
            mode: Either 'normal' or 'idle-boost'
        """
        if mode not in ['normal', 'idle-boost']:
            logger.warning(f"Invalid mode: {mode}. Must be 'normal' or 'idle-boost'")
            return
        
        if mode != self._current_mode:
            old_mode = self._current_mode
            self._current_mode = mode
            self._manual_override = True  # Mark as manually set
            logger.info(f"Resource mode manually changed: {old_mode} -> {mode} (manual override enabled)")
            
            # Trigger callback if set
            if self._adjustment_callback:
                try:
                    self._adjustment_callback(mode)
                except Exception as e:
                    logger.error(f"Error in adjustment callback: {e}")
    
    def clear_manual_override(self):
        """
        Clear manual override and allow automatic mode switching again.
        """
        self._manual_override = False
        logger.info("Manual override cleared - automatic mode switching enabled")
    
    def get_current_mode(self) -> str:
        """
        Get current resource mode.
        
        Returns:
            Current mode ('normal' or 'idle-boost')
        """
        return self._current_mode
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self._is_monitoring:
            try:
                # Skip automatic switching if manual override is active
                if self._manual_override:
                    time.sleep(self.check_interval_seconds)
                    continue
                
                # Check if system is idle
                is_idle = self._is_system_idle()
                
                # Determine mode
                new_mode = "idle-boost" if (self.idle_boost_enabled and is_idle) else "normal"
                
                # If mode changed, trigger callback
                if new_mode != self._current_mode:
                    old_mode = self._current_mode
                    self._current_mode = new_mode
                    logger.info(f"Resource mode changed: {old_mode} -> {new_mode} (automatic)")
                    
                    if self._adjustment_callback:
                        try:
                            self._adjustment_callback(new_mode)
                        except Exception as e:
                            logger.error(f"Error in adjustment callback: {e}")
                
                time.sleep(self.check_interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in resource monitoring loop: {e}")
                time.sleep(self.check_interval_seconds)
    
    def _is_system_idle(self) -> bool:
        """
        Check if system is idle (no user input for threshold minutes).
        
        Returns:
            True if system is idle, False otherwise
        """
        try:
            # Windows-specific: Get last input time
            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [
                    ('cbSize', ctypes.c_uint),
                    ('dwTime', ctypes.c_uint),
                ]
            
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            
            ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
            
            # Get current tick count
            current_tick = ctypes.windll.kernel32.GetTickCount()
            
            # Calculate idle time in milliseconds
            idle_time_ms = current_tick - lii.dwTime
            idle_time_minutes = idle_time_ms / (1000 * 60)
            
            return idle_time_minutes >= self.idle_threshold_minutes
            
        except Exception as e:
            logger.error(f"Error checking system idle state: {e}")
            return False
    
    def get_current_usage(self) -> dict:
        """
        Get current system resource usage.
        
        Returns:
            Dictionary with CPU, RAM, and GPU usage info
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            return {
                'cpu_percent': cpu_percent,
                'ram_percent': memory.percent,
                'ram_used_gb': memory.used / (1024 ** 3),
                'ram_total_gb': memory.total / (1024 ** 3),
                'mode': self._current_mode,
            }
        except Exception as e:
            logger.error(f"Error getting current usage: {e}")
            return {}
    
    def get_current_limits(self) -> dict:
        """
        Get current resource limits based on mode.
        
        Returns:
            Dictionary with current CPU and RAM limits
        """
        if self._current_mode == "idle-boost":
            return {
                'max_cpu_percent': self.idle_cpu_percent,
                'max_ram_percent': self.idle_ram_percent,
                'mode': 'idle-boost',
            }
        else:
            return {
                'max_cpu_percent': self.max_cpu_percent,
                'max_ram_percent': self.max_ram_percent,
                'mode': 'normal',
            }
    
    def is_over_limit(self) -> bool:
        """
        Check if current usage is over limits.
        
        Returns:
            True if over limit, False otherwise
        """
        usage = self.get_current_usage()
        limits = self.get_current_limits()
        
        return (usage.get('cpu_percent', 0) > limits['max_cpu_percent'] or
                usage.get('ram_percent', 0) > limits['max_ram_percent'])
    
    def get_optimized_config(self) -> dict:
        """
        Get optimized configuration for current resource limits.
        
        Returns:
            Dictionary with optimized n_threads, n_batch, n_gpu_layers, n_ctx
        """
        limits = self.get_current_limits()
        system_info = self.get_system_info()
        
        # Calculate optimal threads (use percentage of logical cores)
        max_threads = system_info.get('cpu_count_logical', 8)
        cpu_percent = limits['max_cpu_percent'] / 100.0
        n_threads = max(1, int(max_threads * cpu_percent))
        
        # Batch size - can be configurable, default conservative value
        n_batch = 2048
        
        # GPU layers - 0 for now (would need GPU detection)
        n_gpu_layers = 0
        
        # Context size - standard for this model
        n_ctx = 32768
        
        return {
            'n_threads': n_threads,
            'n_batch': n_batch,
            'n_gpu_layers': n_gpu_layers,
            'n_ctx': n_ctx,
            'mode': self._current_mode,
        }
    
    @staticmethod
    def get_system_info() -> dict:
        """
        Get static system information.
        
        Returns:
            Dictionary with CPU cores, RAM, etc.
        """
        try:
            memory = psutil.virtual_memory()
            
            return {
                'cpu_count': psutil.cpu_count(logical=False),  # Physical cores
                'cpu_count_logical': psutil.cpu_count(logical=True),  # Logical cores
                'ram_total_gb': memory.total / (1024 ** 3),
            }
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {}
