"""OCR Processor - Background processing of receipts using VLM."""
import logging
import threading
import time
import json
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime
from decimal import Decimal

from llama_cpp import Llama
from llama_cpp.llama_chat_format import Llava15ChatHandler

from src.core.config import get_config
from src.core.database import get_database
from src.core.backup_manager import BackupManager
from src.core.resource_manager import ResourceMonitor
from src.services.queue_service import QueueService
from src.services.receipt_service import ReceiptService
from src.utils.file_helpers import resize_image_if_needed, image_to_base64, cleanup_temp_files
from src.utils.formatters import normalizar_fecha, normalizar_monto, generar_nombre_archivo
from src.models.domain import Receipt, ProcessingStatus

logger = logging.getLogger(__name__)


class BackgroundOCRProcessor:
    """Background processor for receipt OCR using Vision Language Model."""
    
    def __init__(self, config_path: str = 'config.yaml'):
        """
        Initialize OCR processor.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = get_config(config_path)
        self.db = get_database(self.config.paths.get('database'))
        
        # Services
        self.queue_service = QueueService(self.config)
        self.receipt_service = ReceiptService(self.config)
        
        # Components
        self.backup_manager = BackupManager(
            self.config.paths.get('database'),
            self.config.paths.get('backups_dir'),
            self.config.backup.get('retention_days', 7)
        )
        self.resource_monitor = ResourceMonitor(
            max_cpu_percent=self.config.processor.get('max_cpu_percent', 70),
            max_ram_percent=self.config.processor.get('max_ram_percent', 70),
            idle_boost_enabled=self.config.processor.get('idle_boost_enabled', True),
            idle_threshold_minutes=self.config.processor.get('idle_threshold_minutes', 5),
            idle_cpu_percent=self.config.processor.get('idle_cpu_percent', 95),
            idle_ram_percent=self.config.processor.get('idle_ram_percent', 95),
            check_interval_seconds=self.config.processor.get('resource_check_interval_seconds', 5)
        )
        
        # State
        self._is_running = False
        self._is_paused = False
        self._force_stop = False  # Flag to force stop current processing
        self._worker_thread: Optional[threading.Thread] = None
        self._llm: Optional[Llama] = None
        
        # Stats
        self.stats = {
            'processed': 0,
            'failed': 0,
            'started_at': None,
        }
    
    def startup(self):
        """
        Perform startup tasks.
        
        - Cleanup temporary files
        - Create backup if enabled
        - Auto-reset interrupted queue items
        """
        logger.info("Performing startup tasks...")
        
        # Cleanup temp files
        cleanup_temp_files(self.config.paths.get('temp_dir'))
        
        # Backup database
        if self.config.backup.get('backup_on_startup', True):
            self.backup_manager.perform_backup_with_cleanup()
        
        # Reset interrupted items
        reset_count = self.queue_service.auto_reset_interrupted()
        if reset_count > 0:
            logger.info(f"Auto-reset {reset_count} interrupted items")
    
    def _initialize_model(self):
        """
        Initialize llama.cpp model with vision capabilities.
        """
        logger.info("Initializing VLM model...")
        
        if self._llm is not None:
            logger.info("Model already initialized")
            return
        
        try:
            # Get model paths from config
            processor_config = self.config.processor
            model_path = processor_config.get('model_path', 'models/Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf')
            mmproj_path = processor_config.get('mmproj_path', 'models/mmproj-Qwen2.5-VL-7B-Instruct-f16.gguf')
            
            # Get processing parameters
            n_threads = processor_config.get('threads', 8)
            n_batch = processor_config.get('batch_size', 2048)
            n_gpu_layers = processor_config.get('gpu_layers', 0)
            n_ctx = processor_config.get('context_size', 32768)
            
            # Initialize chat handler
            chat_handler = Llava15ChatHandler(clip_model_path=mmproj_path)
            
            # Load model
            self._llm = Llama(
                model_path=model_path,
                chat_handler=chat_handler,
                n_ctx=n_ctx,
                n_batch=n_batch,
                n_threads=n_threads,
                n_gpu_layers=n_gpu_layers,
                verbose=False,
            )
            
            logger.info(f"Model initialized successfully (threads={n_threads}, batch={n_batch}, gpu_layers={n_gpu_layers})")
            
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            raise
    
    def start(self, progress_callback: Optional[Callable] = None,
              notification_callback: Optional[Callable] = None):
        """
        Start background processing.
        
        Args:
            progress_callback: Callback for progress updates
            notification_callback: Callback for notifications
        """
        if self._is_running:
            logger.warning("Processor already running")
            return
        
        self.startup()
        self._initialize_model()
        
        # Start resource monitoring
        self.resource_monitor.start_monitoring(self._on_resource_mode_change)
        
        # Start worker thread
        self._is_running = True
        self.stats['started_at'] = datetime.now()
        
        # Log clear start message
        logger.info("="*80)
        logger.info(f"📅 INICIO DEL PROCESO: {self.stats['started_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*80)
        
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            args=(progress_callback, notification_callback),
            daemon=True
        )
        self._worker_thread.start()
        
        logger.info("Background processor started")
    
    def stop(self, force=False):
        """Stop background processing.
        
        Args:
            force: If True, interrupts current processing immediately
        """
        self._is_running = False
        if force:
            self._force_stop = True
            logger.warning("⚠️ STOP FORZADO - Interrumpiendo procesamiento actual...")
        
        self.resource_monitor.stop_monitoring()
        
        if self._worker_thread:
            self._worker_thread.join(timeout=10)
        
        self._force_stop = False  # Reset flag
        logger.info("Background processor stopped")
    
    def pause(self):
        """Pause processing."""
        self._is_paused = True
        logger.info("Processor paused")
    
    def resume(self):
        """Resume processing."""
        self._is_paused = False
        logger.info("Processor resumed")
    
    def _worker_loop(self, progress_callback, notification_callback):
        """
        Main worker loop - processes items from queue.
        
        Args:
            progress_callback: Called with stats after each item
            notification_callback: Called for important notifications
        """
        batch_start = datetime.now()
        batch_processed = 0
        
        while self._is_running:
            try:
                # Check if paused
                if self._is_paused:
                    logger.debug("⏸️  Processor paused, waiting...")
                    time.sleep(1)
                    continue
                
                # Get next item from queue
                logger.debug("🔍 Checking queue for next item...")
                item = self.queue_service.get_next_item()
                
                if not item:
                    logger.debug("📭 Queue is empty, waiting for items...")
                    time.sleep(2)
                    continue
                
                # Check for force stop before processing
                if self._force_stop:
                    logger.warning("⚠️ Force stop detected, aborting queue processing")
                    break
                
                # Process the item
                try:
                    result = self._process_item(item)
                    batch_processed += 1
                    
                    # Log result summary
                    if result:
                        logger.info(f"✅ {result}")
                    
                    # Call progress callback
                    if progress_callback:
                        try:
                            progress_callback(self.get_stats())
                        except Exception as e:
                            logger.error(f"Error in progress callback: {e}")
                    
                except Exception as e:
                    logger.error(f"❌ Error processing item {item.id}: {e}", exc_info=True)
                
                # Check if batch complete
                queue_stats = self.queue_service.get_queue_stats()
                if queue_stats['pending'] == 0 and batch_processed > 0:
                    end_time = datetime.now()
                    elapsed = (end_time - batch_start).total_seconds()
                    
                    logger.info("=" * 80)
                    logger.info(f"📅 FINALIZACIÓN DEL PROCESO: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.info(f"📊 RESUMEN:")
                    logger.info(f"   - Total procesados: {batch_processed}")
                    logger.info(f"   - Tiempo total: {elapsed:.1f}s")
                    logger.info(f"   - Promedio por recibo: {elapsed/batch_processed:.1f}s")
                    logger.info("=" * 80)
                    
                    if notification_callback:
                        try:
                            notification_callback(
                                "Batch Complete",
                                f"Processed {batch_processed} receipts successfully"
                            )
                        except Exception as e:
                            logger.error(f"Error in notification callback: {e}")
                    
                    # Reset batch counters
                    batch_start = datetime.now()
                    batch_processed = 0
                
            except Exception as e:
                logger.error(f"💥 Critical error in worker loop: {e}", exc_info=True)
                time.sleep(5)
        
        logger.info("🛑 Worker loop stopped")
    
    def _process_item(self, item) -> str:
        """
        Process a single queue item.
        
        Args:
            item: ProcessingQueueItem
            
        Returns:
            Status message string
        """
        img_path = Path(item.file_path)
        img_name = img_path.name
        start_time = datetime.now()
        temp_file = None
        
        logger.info("-" * 80)
        logger.info(f"📸 IMAGEN: {img_name}")
        logger.info(f"⏰ Inicio: {start_time.strftime('%H:%M:%S')}")
        
        try:
            # Mark as processing
            logger.debug(f"  ➜ Marking item {item.id} as processing...")
            self.queue_service.start_processing(item.id)
            
            # Check if file exists
            img_path = Path(item.file_path)
            if not img_path.exists():
                raise FileNotFoundError(f"Image not found: {item.file_path}")
            logger.debug(f"  ➜ Image file found: {img_path}")
            
            # Resize image if needed
            max_kb = self.config.processor.get('max_image_size_kb', 150)
            logger.debug(f"  ➜ Resizing image if needed (max: {max_kb}KB)...")
            file_to_process, is_temp = resize_image_if_needed(str(img_path), max_kb)
            if is_temp:
                temp_file = file_to_process
                logger.debug(f"  ➜ Created temp resized image: {temp_file}")
            
            # Encode to base64
            logger.debug(f"  ➜ Encoding image to base64...")
            data_uri = f"data:image/jpeg;base64,{image_to_base64(file_to_process)}"
            
            # Check for force stop before expensive VLM call
            if self._force_stop:
                raise InterruptedError("Procesamiento interrumpido por stop forzado")
            
            # Prepare prompt
            prompt = self._get_extraction_prompt()
            
            # Call VLM
            logger.info(f"  ➜ Calling VLM model for extraction...")
            response = self._llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": "Eres un experto en extracción de datos de recibos."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_uri}}
                        ]
                    }
                ],
                max_tokens=self.config.processor.get('max_tokens', 512),
                temperature=self.config.processor.get('temperature', 0.1),
                top_p=0.9
            )
            
            # Parse response
            logger.debug(f"  ➜ Parsing VLM response...")
            response_text = response["choices"][0]["message"]["content"]
            logger.debug(f"  ➜ VLM response: {response_text[:200]}...")
            
            # Check for force stop before continuing
            if self._force_stop:
                raise InterruptedError("Procesamiento interrumpido por stop forzado")
            
            extracted_data = self._parse_json_response(response_text)
            
            if not extracted_data:
                raise ValueError("Failed to extract JSON from response")
            
            logger.debug(f"  ➜ Extracted data: {extracted_data}")
            
            # Normalize data
            logger.debug(f"  ➜ Normalizing data...")
            self._normalize_data(extracted_data)
            
            # Deduce receipt type
            receipt_type = self.receipt_service.deduce_receipt_type(extracted_data)
            logger.debug(f"  ➜ Deduced receipt type: {receipt_type}")
            
            # Generate filename
            fecha_obj = self._parse_fecha(extracted_data.get('fecha', '01/01/2000'))
            importe_decimal = self._parse_importe(extracted_data.get('total', '0,00'))
            
            base_name = generar_nombre_archivo(fecha_obj, importe_decimal, receipt_type)
            output_dir = Path(self.config.paths.get('output_dir', './result'))
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Check for duplicates
            from src.utils.formatters import deduplicar_nombre_archivo
            existing = [f.name for f in output_dir.iterdir() if f.is_file()]
            final_name = deduplicar_nombre_archivo(f"{base_name}{img_path.suffix}", existing)
            
            logger.debug(f"  ➜ Generated filename: {final_name}")
            
            # Copy file to output
            import shutil
            output_path = output_dir / final_name
            shutil.copy2(str(img_path), str(output_path))
            logger.debug(f"  ➜ Copied to output: {output_path}")
            
            # Get description from empresa field if available
            description = extracted_data.get('empresa', '') or ''
            
            # Create Receipt in database
            receipt = Receipt(
                file_path=str(output_path),
                original_filename=img_path.name,
                date=fecha_obj,
                amount=importe_decimal,
                receipt_type=receipt_type,
                description=description,
                extracted_data=extracted_data,
                processing_successful=True
            )
            
            saved_receipt = self.receipt_service.create_receipt(receipt)
            
            # Mark as completed
            self.queue_service.complete_item(item.id)
            self.stats['processed'] += 1
            
            # Calculate elapsed time
            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            
            # Validate extracted data
            tiene_fecha = bool(extracted_data.get('fecha'))
            tiene_importe = bool(extracted_data.get('total'))
            
            logger.info(f"⏰ Fin: {end_time.strftime('%H:%M:%S')}")
            logger.info(f"⏱️  Tiempo: {elapsed:.1f}s")
            logger.info(f"💾 Guardado como: {final_name}")
            logger.info(f"📊 Datos extraídos:")
            logger.info(f"   - Fecha: {'✓' if tiene_fecha else '✗ FALTANTE'} {extracted_data.get('fecha', 'N/A')}")
            logger.info(f"   - Importe: {'✓' if tiene_importe else '✗ FALTANTE'} {extracted_data.get('total', 'N/A')}")
            logger.info(f"   - Tipo: {receipt_type}")
            
            status_msg = f"Procesado exitosamente en {elapsed:.1f}s"
            if not tiene_fecha or not tiene_importe:
                status_msg += " (⚠️ Datos incompletos)"
            
            # Reset model context
            self._llm.reset()
            
            return status_msg
            
        except Exception as e:
            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            logger.info(f"⏰ Fin: {end_time.strftime('%H:%M:%S')}")
            logger.info(f"⏱️  Tiempo: {elapsed:.1f}s")
            logger.error(f"❌ ERROR: {str(e)}")
            logger.error(f"Detalles del error:", exc_info=True)
            try:
                self.queue_service.fail_item(item.id, str(e))
            except Exception as fail_error:
                logger.error(f"Error marking item as failed: {fail_error}")
            self.stats['failed'] += 1
            return None
        
        finally:
            # Cleanup temp file
            if temp_file:
                logger.debug(f"  ➜ Cleaning up temp file: {temp_file}")
                try:
                    Path(temp_file).unlink(missing_ok=True)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temp file: {cleanup_error}")
    
    def _get_extraction_prompt(self) -> str:
        """Get the extraction prompt for VLM."""
        return """Extrae los datos del recibo. Completa solo los campos que encuentres:

{
  "empresa": "Nombre de la empresa",
  "nif": "NIF/CIF de la empresa",
  "total": "Importe total con moneda , o import taxim (si es taxi , uber o similar)",
  "fecha": "Fecha del servicio",
  "hora": "Hora del servicio",
  "clase": "Clase del vehículo (si es una autopista)",
  "autopista": "Nombre de la autopista (si es una autopista)",  
  "descripcion": "Descripción del servicio",
  "origen": "Punto de origen (si es taxi , uber o similar)",
  "destino": "Punto de destino (si es taxi , uber o similar)",
  "distancia": "Kilómetros (si es taxi , uber o similar)",
  "licencia": "Número de licencia/conductor (si es taxi , uber o similar)",
  "matricula": "Matrícula vehículo (si es taxi , uber o similar)",
  "ciudad_parking": "Ciudad (si es parking)",
  "nombre_hotel": "Nombre hotel (si es hotel)",
  "cliente": "Nombre cliente (si es hotel)",
  "llegada": "Fecha llegada (si es hotel)",
  "salida": "Fecha salida (si es hotel)",
  "nombre_restaurante": "Nombre restaurante (si es comida)",
  "camarero": "Nombre camarero (si es comida)",
  "cubiertos": "Número cubiertos (si es comida)",
  "comensales": "Número comensales (si es comida)",
  "clase": "clase del vehículo (si es peaje)",
  "mesa": "Número mesa (si es comida)",
  "litros_combustible": "Litros combustible (si es gasolina)",
  "empresa_alquiler": "Empresa alquiler (si es coche alquiler)",
  "compañia_aerea": "Compañía aérea (si es vuelo)",
  "empresa_ferroviaria": "Empresa tren (si es tren)",
  "compañia_telefonia": "Compañía teléfono (si es teléfono)",
  "estacion_peaje": "Estación peaje (si es peaje)",
  "empresa_mensajeria": "Empresa mensajería (si es envío)",
  "numero_factura": "Número de factura (si está disponible)"
  "restaurante": "Indica si el recibo es de restaurante/comida",
  "parking": "Indica si el recibo es de parking",
  "gasolina": "Indica si el recibo es de repostaje de gasolina o gasóleo",
  "taxi": "Indica si el recibo es de taxi, uber o similar",
  "hotel": "Indica si el recibo es de hotel",
  "peaje": "Indica si el recibo es de peaje de autopista",
  "vuelo": "Indica si el recibo es de vuelo aéreo",
  "tren": "Indica si el recibo es de billete de tren",
  "telefono": "Indica si el recibo es de factura de teléfono",
  "alquiler_coche": "Indica si el recibo es de alquiler de coche",
  "mensajeria": "Indica si el recibo es de mensajería o envío"
}


Responde SOLO en formato JSON. Omite campos vacíos."""
    
    def _parse_json_response(self, response_text: str) -> Optional[dict]:
        """Parse JSON from model response, handling markdown code blocks."""
        try:
            text = response_text
            
            # Clean markdown code blocks
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                if end != -1:
                    text = text[start:end].strip()
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                if end != -1:
                    text = text[start:end].strip()
            
            # Extract JSON object
            start_idx = text.find('{')
            end_idx = text.find('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_text = text[start_idx:end_idx]
                return json.loads(json_text)
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
        
        return None
    
    def _on_resource_mode_change(self, new_mode: str):
        """
        Callback when resource mode changes (normal <-> idle-boost).
        
        Args:
            new_mode: "normal" or "idle-boost"
        """
        logger.info(f"Resource mode changed to: {new_mode}")
        # Note: llama.cpp doesn't support dynamic thread adjustment after initialization
    
    def get_stats(self) -> dict:
        """Get processing statistics."""
        queue_stats = self.queue_service.get_queue_stats()
        resource_usage = self.resource_monitor.get_current_usage()
        
        return {
            **self.stats,
            'queue': queue_stats,
            'resources': resource_usage,
            'is_running': self._is_running,
            'is_paused': self._is_paused,
        }
    
    def _normalize_data(self, data: dict):
        """Normalize extracted data (dates and amounts)."""
        # Normalize date
        fecha_raw = data.get('fecha', data.get('Fecha', ''))
        if fecha_raw:
            from src.utils.formatters import normalizar_fecha
            normalized = normalizar_fecha(fecha_raw)
            if normalized:
                data['fecha'] = normalized.strftime('%d/%m/%Y')
        
        # Normalize amount
        importe_raw = data.get('total', data.get('Total', data.get('Importe Total', '')))
        if importe_raw:
            from src.utils.formatters import normalizar_monto
            normalized = normalizar_monto(importe_raw)
            if normalized:
                # Format as string with comma separator
                data['total'] = str(normalized).replace('.', ',')
    
    def _parse_fecha(self, fecha_str: str) -> datetime:
        """Parse date string to datetime."""
        from src.utils.formatters import normalizar_fecha
        result = normalizar_fecha(fecha_str)
        return result if result else datetime(2000, 1, 1)
    
    def _parse_importe(self, importe_str: str) -> Decimal:
        """Parse amount string to Decimal."""
        from src.utils.formatters import normalizar_monto
        from decimal import Decimal
        result = normalizar_monto(importe_str)
        return result if result else Decimal('0.00')
