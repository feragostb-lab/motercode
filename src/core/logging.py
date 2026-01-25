"""Centralized logging setup for apps and services."""
import logging
import logging.handlers
from pathlib import Path
from typing import Optional


class TeeStream:
    """Redirect stream to both file and original stream."""
    def __init__(self, file_path: str, original_stream):
        self.file_path = file_path
        self.original_stream = original_stream
        self._file: Optional[object] = None

    def _ensure_file_open(self):
        if self._file is None or getattr(self._file, 'closed', True):
            Path(self.file_path).parent.mkdir(parents=True, exist_ok=True)
            self._file = open(self.file_path, 'a', encoding='utf-8', buffering=1)

    def write(self, data):
        if not data:
            return
        # Try writing to file (silent fail if closed)
        try:
            self._ensure_file_open()
            if self._file and not getattr(self._file, 'closed', True):
                self._file.write(data)
                self._file.flush()
        except (ValueError, OSError):
            # File closed or I/O error, silently skip
            pass
        except Exception:
            pass
        # Always try to write to original stream
        try:
            if self.original_stream and not getattr(self.original_stream, 'closed', False):
                self.original_stream.write(data)
                self.original_stream.flush()
        except (ValueError, OSError):
            # Stream closed, silently skip
            pass
        except Exception:
            pass

    def flush(self):
        try:
            if self._file and not self._file.closed:
                self._file.flush()
        except Exception:
            pass
        try:
            self.original_stream.flush()
        except Exception:
            pass

    def close(self):
        if self._file and not self._file.closed:
            self._file.close()


def _level_from_string(level_str: str) -> int:
    mapping = {
        'CRITICAL': logging.CRITICAL,
        'ERROR': logging.ERROR,
        'WARNING': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG,
        'NOTSET': logging.NOTSET,
    }
    return mapping.get(level_str.upper(), logging.INFO)


def setup_logging(config, app_name: str = 'app', capture_std: bool = True):
    """Setup root logging using config, with optional stdout/stderr capture.

    Args:
        config: Config instance providing paths and logging_config
        app_name: Name used for log file naming
        capture_std: If True, wrap stdout/stderr with TeeStream
    """
    import sys

    logs_dir = Path(config.paths.get('logs_dir', './logs'))
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"{app_name}.log"

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(_level_from_string(config.logging_config.get('level', 'INFO')))

    # Clear handlers to avoid duplicates in Streamlit reruns
    root_logger.handlers.clear()

    # Formatter
    fmt = config.logging_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    formatter = logging.Formatter(fmt)

    # File handler with rotation
    max_mb = config.logging_config.get('max_file_size_mb', 10)
    backup_count = config.logging_config.get('backup_count', 5)
    file_handler = logging.handlers.RotatingFileHandler(
        str(log_file), maxBytes=int(max_mb * 1024 * 1024), backupCount=int(backup_count), encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Console handler (use original stdout to avoid recursion)
    console_handler = logging.StreamHandler(sys.__stdout__)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Optional stdout/stderr capture (for non-logging prints or native libs)
    if capture_std:
        # Close and replace existing TeeStreams to avoid "closed file" errors on Streamlit reruns
        if isinstance(sys.stdout, TeeStream):
            try:
                sys.stdout.close()
            except:
                pass
            sys.stdout = sys.__stdout__
        if isinstance(sys.stderr, TeeStream):
            try:
                sys.stderr.close()
            except:
                pass
            sys.stderr = sys.__stderr__
        
        # Create new TeeStreams
        sys.stdout = TeeStream(str(log_file), sys.__stdout__)
        sys.stderr = TeeStream(str(log_file), sys.__stderr__)

    # Log initialized
    logging.getLogger(__name__).info(f"Logging initialized for '{app_name}' -> {log_file}")
