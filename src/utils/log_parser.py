"""Log parser utility for extracting error information."""
import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class LogParser:
    """Parse log files to extract error information."""
    
    @staticmethod
    def parse_error_for_file(log_file: Path, filename: str) -> Optional[Dict]:
        """
        Extract error information for a specific file from logs.
        
        Args:
            log_file: Path to log file
            filename: Name of the file to search for
            
        Returns:
            Dictionary with error information or None if not found
        """
        if not log_file.exists():
            return None
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find all occurrences of this filename
            error_info = None
            i = 0
            
            while i < len(lines):
                line = lines[i]
                
                # Check if this line contains the filename
                if f"IMAGEN: {filename}" in line:
                    # Start collecting info for this processing attempt
                    attempt_info = {
                        'filename': filename,
                        'timestamp': None,
                        'start_time': None,
                        'end_time': None,
                        'duration': None,
                        'error_message': None,
                        'error_details': [],
                        'success': False
                    }
                    
                    # Extract timestamp from log line
                    timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                    if timestamp_match:
                        attempt_info['timestamp'] = timestamp_match.group(1)
                    
                    # Look ahead for start time
                    if i + 1 < len(lines) and "Inicio:" in lines[i + 1]:
                        time_match = re.search(r'Inicio: (\d{2}:\d{2}:\d{2})', lines[i + 1])
                        if time_match:
                            attempt_info['start_time'] = time_match.group(1)
                    
                    # Look for end time, duration, and errors in subsequent lines
                    j = i + 2
                    while j < len(lines) and j < i + 50:  # Look ahead max 50 lines
                        next_line = lines[j]
                        
                        # Stop if we hit another image processing
                        if "IMAGEN:" in next_line and filename not in next_line:
                            break
                        
                        # Extract end time
                        if "Fin:" in next_line:
                            time_match = re.search(r'Fin: (\d{2}:\d{2}:\d{2})', next_line)
                            if time_match:
                                attempt_info['end_time'] = time_match.group(1)
                        
                        # Extract duration
                        if "Tiempo:" in next_line:
                            duration_match = re.search(r'Tiempo: ([\d.]+)s', next_line)
                            if duration_match:
                                attempt_info['duration'] = duration_match.group(1)
                        
                        # Check for success
                        if "✅ Procesado exitosamente" in next_line:
                            attempt_info['success'] = True
                            break
                        
                        # Check for errors
                        if "ERROR:" in next_line:
                            error_match = re.search(r'ERROR: (.+)$', next_line)
                            if error_match:
                                attempt_info['error_message'] = error_match.group(1).strip()
                        
                        # Check for error details
                        if "Detalles del error:" in next_line:
                            # Collect traceback lines
                            k = j + 1
                            while k < len(lines) and k < j + 20:
                                detail_line = lines[k].strip()
                                if detail_line and not detail_line.startswith('2026-'):
                                    attempt_info['error_details'].append(detail_line)
                                elif detail_line.startswith('2026-') and 'ERROR' not in detail_line:
                                    break
                                k += 1
                        
                        j += 1
                    
                    # If this attempt has an error, store it (overwrite previous to get latest)
                    if not attempt_info['success']:
                        error_info = attempt_info
                
                i += 1
            
            return error_info
            
        except Exception as e:
            return {
                'filename': filename,
                'error_message': f"Failed to parse log: {str(e)}",
                'error_details': [],
                'success': False
            }
    
    @staticmethod
    def get_all_errors(log_file: Path, limit: int = 50) -> List[Dict]:
        """
        Extract all error entries from log file.
        
        Args:
            log_file: Path to log file
            limit: Maximum number of errors to return
            
        Returns:
            List of error dictionaries
        """
        if not log_file.exists():
            return []
        
        errors = []
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # Look for error markers
                if "❌ ERROR:" in line:
                    error_entry = {
                        'timestamp': None,
                        'filename': None,
                        'error_message': None,
                        'error_details': []
                    }
                    
                    # Extract timestamp
                    timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                    if timestamp_match:
                        error_entry['timestamp'] = timestamp_match.group(1)
                    
                    # Extract error message
                    error_match = re.search(r'ERROR: (.+)$', line)
                    if error_match:
                        error_entry['error_message'] = error_match.group(1).strip()
                    
                    # Look backward for filename
                    for j in range(max(0, i - 10), i):
                        if "IMAGEN:" in lines[j]:
                            filename_match = re.search(r'IMAGEN: (.+)$', lines[j])
                            if filename_match:
                                error_entry['filename'] = filename_match.group(1).strip()
                                break
                    
                    # Look forward for details
                    if i + 1 < len(lines) and "Detalles del error:" in lines[i + 1]:
                        k = i + 2
                        while k < len(lines) and k < i + 22:
                            detail_line = lines[k].strip()
                            if detail_line and not detail_line.startswith('2026-'):
                                error_entry['error_details'].append(detail_line)
                            elif detail_line.startswith('2026-'):
                                break
                            k += 1
                    
                    errors.append(error_entry)
                    
                    if len(errors) >= limit:
                        break
                
                i += 1
            
            return errors
            
        except Exception:
            return []
    
    @staticmethod
    def format_error_display(error_info: Dict) -> str:
        """
        Format error information for display.
        
        Args:
            error_info: Error information dictionary
            
        Returns:
            Formatted string
        """
        if not error_info:
            return "No error information available"
        
        parts = []
        
        if error_info.get('timestamp'):
            parts.append(f"🕐 Timestamp: {error_info['timestamp']}")
        
        if error_info.get('filename'):
            parts.append(f"📄 Archivo: {error_info['filename']}")
        
        if error_info.get('start_time'):
            parts.append(f"⏰ Inicio: {error_info['start_time']}")
        
        if error_info.get('end_time'):
            parts.append(f"⏰ Fin: {error_info['end_time']}")
        
        if error_info.get('duration'):
            parts.append(f"⏱️ Duración: {error_info['duration']}s")
        
        if error_info.get('error_message'):
            parts.append(f"\n❌ Error: {error_info['error_message']}")
        
        if error_info.get('error_details'):
            parts.append("\n📋 Detalles:")
            for detail in error_info['error_details'][:10]:  # Limit details
                parts.append(f"  {detail}")
        
        return "\n".join(parts)
