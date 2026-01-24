"""Receipt service - Business logic for receipt management."""
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
import shutil
import os

from ..models.domain import Receipt
from ..repositories.receipt_repository import ReceiptRepository
from ..utils.formatters import generar_nombre_archivo, deduplicar_nombre_archivo
from ..core.database import get_database

logger = logging.getLogger(__name__)


class ReceiptService:
    """Service for receipt business logic."""
    
    def __init__(self, config):
        """
        Initialize receipt service.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.db = get_database(config.paths.get('database', './receipts.db'))
        self.repository = ReceiptRepository(self.db)
        self.output_dir = Path(config.paths.get('output_dir', './result'))
    
    def create_receipt(self, receipt: Receipt) -> Receipt:
        """
        Create a new receipt.
        
        Args:
            receipt: Receipt model
            
        Returns:
            Created receipt with ID
        """
        return self.repository.create(receipt)
    
    def get_receipt_by_id(self, receipt_id: int) -> Optional[Receipt]:
        """Get receipt by ID."""
        return self.repository.get_by_id(receipt_id)
    
    def get_all_receipts(self) -> List[Receipt]:
        """Get all receipts."""
        return self.repository.get_all()
    
    def update_receipt_type(self, receipt_id: int, new_type: str) -> bool:
        """
        Update receipt type and rename file accordingly.
        
        Args:
            receipt_id: Receipt ID
            new_type: New receipt type
            
        Returns:
            True if successful, False otherwise
        """
        receipt = self.repository.get_by_id(receipt_id)
        if not receipt:
            logger.error(f"Receipt {receipt_id} not found")
            return False
        
        # If type hasn't changed, nothing to do
        if receipt.receipt_type == new_type:
            return True
        
        # Get old file path
        old_path = Path(receipt.file_path)
        if not old_path.exists():
            logger.error(f"File {receipt.file_path} not found")
            return False
        
        # Generate new filename with new type
        extension = old_path.suffix
        new_name = generar_nombre_archivo(
            receipt.date,
            receipt.amount,
            new_type
        )
        new_name = f"{new_name}{extension}"
        
        # Check for duplicates and deduplicate
        existing_files = self.get_existing_filenames(str(old_path.parent))
        new_name = deduplicar_nombre_archivo(new_name, existing_files)
        
        # Rename physical file
        new_path = old_path.parent / new_name
        try:
            old_path.rename(new_path)
            
            # Update database
            receipt.receipt_type = new_type
            receipt.file_path = str(new_path)
            return self.repository.update(receipt)
            
        except Exception as e:
            logger.error(f"Error renaming file: {e}")
            # Try to revert if possible
            if new_path.exists() and not old_path.exists():
                try:
                    new_path.rename(old_path)
                except:
                    pass
            return False
    
    def update_receipt_date(self, receipt_id: int, new_date: datetime) -> bool:
        """
        Update receipt date and rename file accordingly.
        
        Args:
            receipt_id: Receipt ID
            new_date: New date (can be datetime or date object)
            
        Returns:
            True if successful, False otherwise
        """
        receipt = self.repository.get_by_id(receipt_id)
        if not receipt:
            logger.error(f"Receipt {receipt_id} not found")
            return False
        
        # Convert to date for comparison if needed
        from datetime import date as date_type
        new_date_obj = new_date if isinstance(new_date, date_type) and not isinstance(new_date, datetime) else (new_date.date() if isinstance(new_date, datetime) else new_date)
        receipt_date_obj = receipt.date.date() if isinstance(receipt.date, datetime) else receipt.date
        
        # If date hasn't changed, nothing to do
        if receipt.date and receipt_date_obj == new_date_obj:
            return True
        
        # Get old file path
        old_path = Path(receipt.file_path)
        if not old_path.exists():
            logger.error(f"File {receipt.file_path} not found")
            return False
        
        # Generate new filename with new date
        # Convert date to datetime if needed
        from datetime import date as date_type
        date_for_filename = datetime.combine(new_date, datetime.min.time()) if isinstance(new_date, date_type) and not isinstance(new_date, datetime) else new_date
        
        extension = old_path.suffix
        new_name = generar_nombre_archivo(
            date_for_filename,
            receipt.amount,
            receipt.receipt_type
        )
        new_name = f"{new_name}{extension}"
        
        # Check for duplicates and deduplicate
        existing_files = self.get_existing_filenames(str(old_path.parent))
        new_name = deduplicar_nombre_archivo(new_name, existing_files)
        
        # Rename physical file
        new_path = old_path.parent / new_name
        try:
            old_path.rename(new_path)
            
            # Update database (convert to datetime if needed)
            receipt.date = date_for_filename
            receipt.file_path = str(new_path)
            return self.repository.update(receipt)
            
        except Exception as e:
            logger.error(f"Error renaming file: {e}")
            # Try to revert if possible
            if new_path.exists() and not old_path.exists():
                try:
                    new_path.rename(old_path)
                except:
                    pass
            return False
    
    def update_receipt_amount(self, receipt_id: int, new_amount: Decimal) -> bool:
        """
        Update receipt amount and rename file accordingly.
        
        Args:
            receipt_id: Receipt ID
            new_amount: New amount
            
        Returns:
            True if successful, False otherwise
        """
        receipt = self.repository.get_by_id(receipt_id)
        if not receipt:
            logger.error(f"Receipt {receipt_id} not found")
            return False
        
        # If amount hasn't changed, nothing to do
        if receipt.amount == new_amount:
            return True
        
        # Get old file path
        old_path = Path(receipt.file_path)
        if not old_path.exists():
            logger.error(f"File {receipt.file_path} not found")
            return False
        
        # Generate new filename with new amount
        extension = old_path.suffix
        new_name = generar_nombre_archivo(
            receipt.date,
            new_amount,
            receipt.receipt_type
        )
        new_name = f"{new_name}{extension}"
        
        # Check for duplicates and deduplicate
        existing_files = self.get_existing_filenames(str(old_path.parent))
        new_name = deduplicar_nombre_archivo(new_name, existing_files)
        
        # Rename physical file
        new_path = old_path.parent / new_name
        try:
            old_path.rename(new_path)
            
            # Update database
            receipt.amount = new_amount
            receipt.file_path = str(new_path)
            return self.repository.update(receipt)
            
        except Exception as e:
            logger.error(f"Error renaming file: {e}")
            # Try to revert if possible
            if new_path.exists() and not old_path.exists():
                try:
                    new_path.rename(old_path)
                except:
                    pass
            return False
    
    def update_receipt_description(self, receipt_id: int, new_description: str) -> bool:
        """
        Update receipt description.
        
        Args:
            receipt_id: Receipt ID
            new_description: New description text
            
        Returns:
            True if successful, False otherwise
        """
        receipt = self.repository.get_by_id(receipt_id)
        if not receipt:
            logger.error(f"Receipt {receipt_id} not found")
            return False
        
        # Update description
        receipt.description = new_description
        return self.repository.update(receipt)
    
    def deduce_receipt_type(self, extracted_data: Dict[str, Any]) -> str:
        """
        Deduce receipt type from extracted data based on specific keywords and patterns.
        Uses field presence to determine the most likely receipt category.
        
        Args:
            extracted_data: Dictionary with extracted OCR data
            
        Returns:
            Deduced receipt type (taxi, hotel, parking, restaurante, gasolina, etc.)
        """
        if not extracted_data:
            return 'otros'
        
        # Convert all keys to lowercase for case-insensitive matching
        data_lower = {k.lower(): v for k, v in extracted_data.items() if v}
        
        # Count specific indicators for each type (more specific = higher priority)
        
# "restaurcion": "Indica si el recibo es de restaurante/comida",
#   "parking": "Indica si el recibo es de parking",
#   "gasolina": "Indica si el recibo es de repostaje de gasolina o gasóleo",
#   "taxi": "Indica si el recibo es de taxi, uber o similar",
#   "hotel": "Indica si el recibo es de hotel",
#   "peaje": "Indica si el recibo es de peaje de autopista",
#   "vuelo": "Indica si el recibo es de vuelo aéreo",
#   "tren": "Indica si el recibo es de billete de tren",
#   "telefono": "Indica si el recibo es de factura de teléfono",
#   "alquiler_coche": "Indica si el recibo es de alquiler de coche",
#   "mensajeria": "Indica si el recibo es de mensajería o envío"


        # TAXI / UBER - Check for transport-specific fields
        taxi_fields = ['origen', 'destino', 'distancia', 'licencia', 'matricula', 'taximetro']
        taxi_score = sum(1 for field in taxi_fields if field in data_lower)
        taxi_score += sum(5 for key in data_lower if 'taxi' in key)

        # HOTEL - Check for hotel-specific fields
        hotel_fields = ['nombre_hotel', 'cliente', 'llegada', 'salida', 'habitacion', 'check_in', 'check_out']
        hotel_score = sum(1 for field in hotel_fields if field in data_lower)
        hotel_score += sum(5 for key in data_lower if 'hotel' in key)

        # RESTAURANTE / COMIDA - Check for restaurant-specific fields
        restaurant_fields = ['nombre_restaurante', 'camarero', 'cubiertos', 'comensales', 'mesa','hotel']
        restaurant_score = sum(1 for field in restaurant_fields if field in data_lower)
        restaurant_score += sum(hotel_score for key in data_lower if 'restaurante' in key)
        

        # PARKING - Check for parking-specific fields
        parking_fields = ['ciudad_parking', 'matricula','origen','parking', 'estacionamiento', 'zona_parking']
        parking_score = sum(1 for field in parking_fields if field in data_lower)
        parking_score += sum(5 for key in data_lower if 'parking' in key)
        
        # GASOLINA - Check for gas station-specific fields
        gasolina_fields = ['litros_combustible', 'combustible', 'litros', 'gasolinera']
        gasolina_score = sum(1 for field in gasolina_fields if field in data_lower)
        gasolina_score += sum(5 for key in data_lower if 'gasolina' in key or 'diesel' in key)
        
        # ALQUILER COCHE - Check for car rental-specific fields
        alquiler_fields = ['empresa_alquiler', 'rental', 'alquiler_coche']
        alquiler_score = sum(1 for field in alquiler_fields if field in data_lower)
        alquiler_score += sum(5 for key in data_lower if 'alquiler' in key or 'rental' in key)

        # VUELO - Check for flight-specific fields
        vuelo_fields = ['compañia_aerea', 'compania_aerea', 'vuelo', 'flight', 'aeropuerto', 'boarding']
        common_airlines = ['iberia', 'vueling', 'ryanair', 'easyjet', 'air europa', 'lufthansa', 'british airways']
        #si el campo empresa en data_lower contiene uno de los nombres de aerolineas comunes, aumentar el puntaje
        vuelo_score = sum(1 for field in vuelo_fields if field in data_lower)
        if 'empresa' in data_lower:
            empresa_value = str(data_lower['empresa']).lower()
            if any(airline in empresa_value for airline in common_airlines):
                vuelo_score += 5
        vuelo_score += sum(5 for key in data_lower if 'vuelo' in key or 'flight' in key)


        # TREN - Check for train-specific fields
        tren_fields = ['empresa_ferroviaria', 'tren', 'train', 'estacion', 'renfe']
        tren_score = sum(1 for field in tren_fields if field in data_lower)
        tren_score += sum(5 for key in data_lower if 'tren' in key or 'train' in key)

        # TELÉFONO - Check for phone service-specific fields
        telefono_fields = ['compañia_telefonia', 'compania_telefonia', 'telefono', 'movil', 'linea']
        telefono_score = sum(1 for field in telefono_fields if field in data_lower)
        telefono_score += sum(5 for key in data_lower if 'telefono' in key or 'telefonia' in key)

        # PEAJE - Check for toll-specific fields
        peaje_fields = ['clase', 'autopista']
        peaje_score = sum(1 for field in peaje_fields if field in data_lower)
        peaje_score += sum(5 for key in data_lower if 'peaje' in key or 'autopista' in key)
        
        # MENSAJERÍA / ENVÍO - Check for shipping-specific fields
        mensajeria_fields = ['empresa_mensajeria', 'envio', 'mensajeria', 'courier']
        mensajeria_score = sum(1 for field in mensajeria_fields if field in data_lower)
        mensajeria_score += sum(5 for key in data_lower if 'mensajeria' in key or 'envio' in key or 'courier' in key)

        
        # Create scores dictionary
        scores = {
            'taxi': taxi_score,
            'hotel': hotel_score,
            'restaurante': restaurant_score,
            'parking': parking_score,
            'gasolina': gasolina_score,
            'alquiler': alquiler_score,
            'vuelo': vuelo_score,
            'tren': tren_score,
            'telefono': telefono_score,
            'peaje': peaje_score,
            'mensajeria': mensajeria_score,
        }
        print("Scores:", scores)
        # Find the category with the highest score
        max_score = max(scores.values())
        
        # If we have a clear match (score > 0), return it
        if max_score > 0:
            # Get all categories with max score
            top_categories = [cat for cat, score in scores.items() if score == max_score]
            # Return the first one (if tied, priority by order)
            print("Top categories:", top_categories)
            return top_categories[0]
        
        # Fallback: Check for invoice/factura based on NIF/CIF presence
        if 'nif' in data_lower or 'cif' in data_lower or 'numero_factura' in data_lower:
            return 'factura'
        
        # Last resort: check text content for keywords
        all_text = ' '.join(str(v).lower() for v in data_lower.values() if v)
        
        if any(word in all_text for word in ['taxi', 'uber', 'cabify']):
            return 'taxi'
        if any(word in all_text for word in ['hotel', 'hospedaje', 'alojamiento']):
            return 'hotel'
        if any(word in all_text for word in ['restaurante', 'bar', 'cafeteria', 'restaurant']):
            return 'restaurante'
        if any(word in all_text for word in ['parking', 'aparcamiento', 'estacionamiento']):
            return 'parking'
        if any(word in all_text for word in ['gasolina', 'combustible', 'fuel', 'gasolinera']):
            return 'gasolina'
        if any(word in all_text for word in ['factura', 'invoice']):
            return 'factura'
        
        # Default to 'otros' if no match found
        return 'otros'
    
    def update_receipt_type_simple(self, receipt_id: int, new_type: str) -> bool:
        """
        Update receipt type (simplified version without file renaming).
        
        Args:
            receipt_id: Receipt ID
            new_type: New receipt type
            
        Returns:
            True if successful, False otherwise
        """
        receipt = self.repository.get_by_id(receipt_id)
        if not receipt:
            logger.error(f"Receipt {receipt_id} not found")
            return False
        
        # Validate type
        valid_types = self.config.receipt_types
        if new_type not in valid_types:
            logger.error(f"Invalid receipt type: {new_type}")
            return False
        
        # Update receipt
        receipt.receipt_type = new_type
        return self.repository.update(receipt)
    
    def update_receipt_date_simple(self, receipt_id: int, new_date: datetime) -> bool:
        """
        Update receipt date (simplified version without file renaming).
        
        Args:
            receipt_id: Receipt ID
            new_date: New date
            
        Returns:
            True if successful, False otherwise
        """
        receipt = self.repository.get_by_id(receipt_id)
        if not receipt:
            logger.error(f"Receipt {receipt_id} not found")
            return False
        
        receipt.date = new_date
        return self.repository.update(receipt)
    
    def update_receipt_amount_simple(self, receipt_id: int, new_amount: Decimal) -> bool:
        """
        Update receipt amount (simplified version without file renaming).
        
        Args:
            receipt_id: Receipt ID
            new_amount: New amount
            
        Returns:
            True if successful, False otherwise
        """
        receipt = self.repository.get_by_id(receipt_id)
        if not receipt:
            logger.error(f"Receipt {receipt_id} not found")
            return False
        
        receipt.amount = new_amount
        return self.repository.update(receipt)
    
    def update_receipt_description(self, receipt_id: int, new_description: str) -> bool:
        """
        Update receipt description.
        
        Args:
            receipt_id: Receipt ID
            new_description: New description
            
        Returns:
            True if successful, False otherwise
        """
        receipt = self.repository.get_by_id(receipt_id)
        if not receipt:
            logger.error(f"Receipt {receipt_id} not found")
            return False
        
        receipt.description = new_description
        return self.repository.update(receipt)
    
    def rename_receipt_file(self, receipt: Receipt, new_filename: str) -> bool:
        """
        Rename physical receipt file and update database.
        
        Args:
            receipt: Receipt model
            new_filename: New filename
            
        Returns:
            True if successful, False otherwise
        """
        try:
            old_path = Path(receipt.file_path)
            new_path = old_path.parent / new_filename
            
            if old_path.exists():
                shutil.move(str(old_path), str(new_path))
                receipt.file_path = str(new_path)
                return self.repository.update(receipt)
            return False
            
        except Exception as e:
            logger.error(f"Error renaming file: {e}")
            return False
    
    def get_existing_filenames(self, directory: str) -> List[str]:
        """
        Get list of existing filenames in directory.
        
        Args:
            directory: Directory path
            
        Returns:
            List of filenames
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            return []
        return [f.name for f in dir_path.iterdir() if f.is_file()]
