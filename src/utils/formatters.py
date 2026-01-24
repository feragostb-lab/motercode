"""Formatting utilities for dates, amounts, and other data."""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional


def normalizar_fecha(fecha_str) -> Optional[datetime]:
    """
    Convert various date formats to a datetime object.
    
    Args:
        fecha_str: Date string in various formats
        
    Returns:
        datetime object or None if parsing fails
    """
    if not fecha_str or fecha_str == "":
        return None
    
    formatos = [
        '%d/%m/%Y',
        '%d.%m.%Y',
        '%Y-%m-%d',
        '%d/%m/%y',
        '%d %b %y',
        '%d %B %y',
        '%d %b %Y',
        '%d %B %Y',
    ]
    
    for formato in formatos:
        try:
            return datetime.strptime(str(fecha_str).strip(), formato)
        except:
            continue
    
    # Try to extract date with regex
    match = re.search(r'(\d{1,2})[/\.\-](\d{1,2})[/\.\-](\d{2,4})', str(fecha_str))
    if match:
        dia, mes, año = match.groups()
        if len(año) == 2:
            año = '20' + año
        try:
            return datetime(int(año), int(mes), int(dia))
        except:
            pass
    
    return None


def normalizar_monto(importe_str) -> Optional[Decimal]:
    """
    Convert various amount formats to Decimal.
    
    Args:
        importe_str: Amount string (with or without currency symbols)
        
    Returns:
        Decimal object or None if parsing fails
    """
    if not importe_str or importe_str == "":
        return None
    
    try:
        # If already a number
        if isinstance(importe_str, (int, float)):
            return Decimal(str(abs(float(importe_str))))
        
        # Clean string: remove currency symbols, replace comma with dot
        importe_clean = str(importe_str).replace('€', '').replace(',', '.').strip()
        importe_clean = re.sub(r'[^\d\.]', '', importe_clean)
        
        if importe_clean:
            return Decimal(importe_clean)
    except (ValueError, InvalidOperation):
        pass
    
    return None


def formatear_fecha(fecha: Optional[datetime], formato: str = '%d/%m/%Y') -> str:
    """
    Format a datetime object to string.
    
    Args:
        fecha: datetime object
        formato: Target format string
        
    Returns:
        Formatted date string or empty string if None
    """
    if fecha is None:
        return ""
    return fecha.strftime(formato)


def formatear_monto(monto: Optional[Decimal], simbolo: str = '€') -> str:
    """
    Format a Decimal amount to string with currency symbol.
    
    Args:
        monto: Decimal amount
        simbolo: Currency symbol
        
    Returns:
        Formatted amount string or empty string if None
    """
    if monto is None:
        return ""
    return f"{monto:.2f}{simbolo}"


def generar_nombre_archivo(fecha: Optional[datetime], monto: Optional[Decimal], 
                          tipo: str, extension: str = '.jpeg') -> str:
    """
    Generate standardized filename for a receipt.
    Format: YYMMDD_AMOUNT_TYPE.ext
    
    Args:
        fecha: Receipt date
        monto: Receipt amount
        tipo: Receipt type
        extension: File extension
        
    Returns:
        Generated filename
    """
    fecha_str = fecha.strftime('%y%m%d') if fecha else 'NODATE'
    monto_str = f"{monto:.2f}".replace('.', '') if monto else 'NOAMT'
    return f"{fecha_str}_{monto_str}_{tipo}{extension}"


def deduplicar_nombre_archivo(file_path: str, existing_files: list) -> str:
    """
    Add ordinal suffix to filename if it already exists.
    Example: file.jpg -> file(1).jpg -> file(2).jpg
    
    Args:
        file_path: Original file path
        existing_files: List of existing file names
        
    Returns:
        Deduplicated filename
    """
    from pathlib import Path
    
    path = Path(file_path)
    base_name = path.stem
    extension = path.suffix
    directory = path.parent
    
    counter = 1
    new_path = file_path
    
    while Path(new_path).name in existing_files:
        new_name = f"{base_name}({counter}){extension}"
        new_path = str(directory / new_name)
        counter += 1
    
    return new_path
