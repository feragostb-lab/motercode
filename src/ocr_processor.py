"""OCR Processor - Background processing of receipts using VLM."""
import logging
import threading
import time
import json
import os
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from datetime import datetime
from decimal import Decimal

from llama_cpp import Llama
from llama_cpp.llama_chat_format import Qwen25VLChatHandler

from src.core.config import get_config
from src.core.database import get_database
from src.core.backup_manager import BackupManager
from src.core.resource_manager import ResourceMonitor
from src.services.queue_service import QueueService
from src.services.receipt_service import ReceiptService
from src.services.config_service import ConfigService
from src.utils.file_helpers import resize_image_if_needed, image_to_base64, cleanup_temp_files
from src.utils.formatters import normalizar_fecha, normalizar_monto, generar_nombre_archivo
from src.models.domain import Receipt, ProcessingStatus

logger = logging.getLogger(__name__)

# Thread and PID tracking for processor state persistence
PROCESSOR_THREAD_NAME = "BackgroundOCRProcessor-Worker"
PROCESSOR_PID_KEY = "processor_pid"


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
        self.config_service = ConfigService(config_path)
        
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
        
        # Sync state with actual running status
        self._sync_running_state()
    
    def _sync_running_state(self):
        """
        Synchronize _is_running state with actual thread status.
        Detects if processor is already running from a previous session.
        """
        # Check if worker thread exists in current process
        for thread in threading.enumerate():
            if thread.name == PROCESSOR_THREAD_NAME and thread.is_alive():
                self._is_running = True
                self._worker_thread = thread
                logger.info("🔄 Detected running processor thread from previous session")
                return
        
        # Check if another process is running (via PID in database)
        stored_pid = self.config_service.get_system_config(PROCESSOR_PID_KEY)
        current_pid = os.getpid()
        
        if stored_pid:
            try:
                stored_pid_int = int(stored_pid)
                # Check if process exists and has processing items
                if stored_pid_int != current_pid:
                    queue_stats = self.queue_service.get_queue_stats()
                    if queue_stats.get('processing', 0) > 0:
                        logger.warning(f"⚠️ Another process (PID {stored_pid_int}) may be running the processor")
                        # We don't set _is_running=True here because it's another process
                    else:
                        # Clear stale PID
                        self.config_service.set_system_config(PROCESSOR_PID_KEY, None)
            except (ValueError, TypeError):
                pass
    
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
            
            # Initialize chat handler for Qwen2.5-VL
            chat_handler = Qwen25VLChatHandler(clip_model_path=mmproj_path)
            
            # Load model (tokenizer is embedded in GGUF)
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
        
        # Save PID to database
        self.config_service.set_system_config(PROCESSOR_PID_KEY, str(os.getpid()))
        
        # Log clear start message
        logger.info("="*80)
        logger.info(f"📅 INICIO DEL PROCESO: {self.stats['started_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"🔢 PID: {os.getpid()}")
        logger.info("="*80)
        
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            args=(progress_callback, notification_callback),
            daemon=True,
            name=PROCESSOR_THREAD_NAME
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
        
        # Clear PID from database
        self.config_service.set_system_config(PROCESSOR_PID_KEY, None)
        
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
                # Check if paused - don't get new items while paused
                if self._is_paused:
                    logger.info("⏸️  Processor is paused - not processing new items")
                    time.sleep(1)
                    continue
                
                # Get next item from queue for the active period
                logger.debug("🔍 Checking queue for next item...")
                _, period_id = self._get_active_worker_and_period()
                item = self.queue_service.get_next_item(period_id)
                
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
                    
                    # After processing, check if pause was requested
                    if self._is_paused:
                        logger.info("⏸️  Pause requested - stopping after completing current item")
                        # Don't break, just continue to top of loop where it will wait
                    
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
                queue_stats = self.queue_service.get_queue_stats(period_id)
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
            
            # Get image preprocessing config
            img_config = self.config.processor.get('image_preprocessing', {})
            enable_grayscale = img_config.get('enable_grayscale', False)
            resize_factor = img_config.get('resize_factor', 0)
            
            file_to_process = img_path
            
            # Step 1: Apply resize and/or grayscale if configured
            if resize_factor > 0 or enable_grayscale:
                logger.debug(f"  ➜ Applying image preprocessing (grayscale={enable_grayscale}, resize_factor={resize_factor})...")
                from src.utils.file_helpers import resize_to_factor
                
                processed_path, was_processed = resize_to_factor(
                    str(img_path),
                    resize_factor=resize_factor,
                    to_grayscale=enable_grayscale,
                    temp_dir=self.config.paths.get('temp_dir', './temp')
                )
                
                if was_processed:
                    temp_file = processed_path  # Mark for cleanup
                    file_to_process = Path(processed_path)
                    logger.debug(f"  ➜ Image preprocessed: {temp_file}")
                else:
                    logger.debug(f"  ➜ No preprocessing applied")
            else:
                logger.debug(f"  ➜ Image preprocessing disabled, using original image")
            
            # Step 2: Resize if still too large (KB size limit)
            max_kb = self.config.processor.get('max_image_size_kb', 600)
            logger.debug(f"  ➜ Checking size limit (max: {max_kb}KB)...")
            from src.utils.file_helpers import resize_image_if_needed
            resized_path, is_temp = resize_image_if_needed(file_to_process, max_kb)
            
            if is_temp:
                if temp_file and temp_file != file_to_process:
                    # Clean up previous temp and use new one
                    try:
                        Path(temp_file).unlink(missing_ok=True)
                    except:
                        pass
                temp_file = resized_path
                file_to_process = Path(resized_path)
                logger.debug(f"  ➜ Image resized to meet size limit: {temp_file}")
            
            logger.debug(f"  ➜ Final image for processing: {file_to_process}")
            
            # Encode to base64
            logger.debug(f"  ➜ Encoding image to base64...")
            data_uri = f"data:image/jpeg;base64,{image_to_base64(file_to_process)}"
            
            # Check for force stop before expensive VLM call
            if self._force_stop:
                raise InterruptedError("Procesamiento interrumpido por stop forzado")
            
            # JSON STRATEGY WITH SINGLE CATEGORY:
            # Stage 1: Extract basic fields + single category in JSON format
            # If no category detected, retry with original non-optimized image
            # Stage 2: If category detected, ask auxiliary fields via TEXT-ONLY
            
            logger.info("  📋 STAGE 1: Extracting basic fields + category (JSON format)...")
            raw_response = self._extract_with_simple_response(data_uri, stage=1)
            
            if not raw_response:
                error_msg = "Failed to extract data in Stage 1"
                logger.error(f"  💥 {error_msg}")
                raise ValueError(error_msg)
            
            # Parse JSON response to structured data
            extracted_data = self._parse_simple_response_to_dict(raw_response, stage=1)
            logger.info(f"  ✅ Stage 1 complete: {len(extracted_data)} fields extracted")
            
            # Check if categories were detected
            detected_categories = extracted_data.get('_detected_categories', [])
            detected_category = extracted_data.get('_detected_category')
            
            if not detected_categories:
                logger.warning("  ⚠️ No categories detected with optimized image")
                logger.info("  🔄 Retrying with ORIGINAL image (no grayscale, no resize)...")
                
                # Re-encode original image without any optimization (no grayscale, no resize)
                original_data_uri = f"data:image/jpeg;base64,{image_to_base64(img_path)}"
                raw_response_retry = self._extract_with_simple_response(original_data_uri, stage=1)
                
                if raw_response_retry:
                    extracted_data_retry = self._parse_simple_response_to_dict(raw_response_retry, stage=1)
                    logger.info(f"  ✅ Retry complete: {len(extracted_data_retry)} fields extracted")
                    
                    # Use retry data if categories detected, otherwise keep original
                    if extracted_data_retry.get('_detected_categories'):
                        detected_cats = extracted_data_retry.get('_detected_categories', [])
                        logger.info(f"  🎯 Categories detected in retry: {', '.join(detected_cats)}")
                        extracted_data = extracted_data_retry
                        detected_categories = extracted_data.get('_detected_categories', [])
                        detected_category = extracted_data.get('_detected_category')
                    else:
                        logger.warning("  ⚠️ Still no categories detected, continuing with basic data")
                else:
                    logger.error("  💥 Retry failed")
            
            # Get detected types for auxiliary field extraction
            detected_types = self._detect_yes_responses(extracted_data)
            
            # Stage 2 logic:
            # - If 2+ categories detected: Ask auxiliary fields to disambiguate
            # - If 1 category: Skip Stage 2 (not needed)
            # - If 0 categories: Skip Stage 2 (nothing to ask)
            if len(detected_types) >= 2:
                logger.info(f"  🎯 Detected {len(detected_types)} categories: {', '.join(detected_types)}")
                logger.info(f"  📋 STAGE 2: Asking auxiliary fields to disambiguate...")
                
                # Stage 2: Text-only follow-up (no image, just conversation with model)
                auxiliary_response = self._ask_auxiliary_fields_text_only(detected_types, extracted_data)
                
                if auxiliary_response:
                    logger.info(f"  ✅ Stage 2 complete: {len(auxiliary_response)} additional fields")
                    extracted_data.update(auxiliary_response)
                else:
                    logger.warning("  ⚠️ Stage 2 failed, continuing with Stage 1 data only")
            elif len(detected_types) == 1:
                logger.info(f"  ✅ Category detected: {detected_types[0]} (no Stage 2 needed)")
            else:
                logger.info("  ℹ️ No categories detected, skipping Stage 2")
            
            logger.debug(f"  ➜ Extracted data: {extracted_data}")
            
            # Normalize data
            logger.debug(f"  ➜ Normalizing data...")
            self._normalize_data(extracted_data)
            
            # Deduce receipt type
            receipt_type = self.receipt_service.deduce_receipt_type(extracted_data)
            logger.debug(f"  ➜ Deduced receipt type: {receipt_type}")
            
            # Generate filename
            fecha_obj = self._parse_fecha(extracted_data.get('fecha', '01/01/2000'))
            importe_decimal = self._parse_importe(extracted_data.get('importe', '0,00'))
            
            base_name = generar_nombre_archivo(fecha_obj, importe_decimal, receipt_type, extension="")
            
            # Get description from empresa field if available
            description = extracted_data.get('empresa', '') or ''
            
            # ===== ROC SKINCARE: Multi-worker period support =====
            # Determine worker and period for this receipt
            worker_id, period_id = self._get_active_worker_and_period()
            
            # Determine output directory based on active period
            output_dir = None
            if worker_id and period_id:
                from src.repositories.period_repository import PeriodRepository
                from src.repositories.worker_repository import WorkerRepository
                from src.utils.file_helpers import get_period_paths
                
                period_repo = PeriodRepository(self.db)
                worker_repo = WorkerRepository(self.db)
                
                period = period_repo.get_by_id(period_id)
                worker = worker_repo.get_by_id(worker_id)
                
                if period and worker:
                    # Use period-specific result directory
                    paths = get_period_paths(worker.nombre, period.month_year)
                    output_dir = paths['result']
                    logger.debug(f"  ➜ Using period directory: {output_dir}")
            
            # Fallback to default output directory if no active period
            if output_dir is None:
                output_dir = Path(self.config.paths.get('output_dir', './result'))
                logger.debug(f"  ➜ Using default directory: {output_dir}")
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Check for duplicates
            from src.utils.formatters import deduplicar_nombre_archivo
            existing = [f.name for f in output_dir.iterdir() if f.is_file()]
            final_name = deduplicar_nombre_archivo(f"{base_name}{img_path.suffix}", existing)
            
            logger.debug(f"  ➜ Generated filename: {final_name}")
            
            # Copy file to output (only once)
            import shutil
            output_path = output_dir / final_name
            shutil.copy2(str(img_path), str(output_path))
            logger.debug(f"  ➜ Copied to: {output_path}")
            
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
            
            # Link receipt to worker/period if available
            if worker_id and period_id and saved_receipt:
                from src.repositories.receipt_repository import ReceiptRepository
                receipt_repo = ReceiptRepository(self.db)
                receipt_repo.update_worker_and_period(saved_receipt.id, worker_id, period_id)
                logger.debug(f"  ➜ Linked receipt to worker {worker_id}, period {period_id}")
            
            # Mark as completed
            self.queue_service.complete_item(item.id)
            self.stats['processed'] += 1
            
            # Calculate elapsed time
            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            
            # Validate extracted data
            tiene_fecha = bool(extracted_data.get('fecha'))
            tiene_importe = bool(extracted_data.get('importe'))
            
            logger.info(f"⏰ Fin: {end_time.strftime('%H:%M:%S')}")
            logger.info(f"⏱️  Tiempo: {elapsed:.1f}s")
            logger.info(f"💾 Guardado como: {final_name}")
            logger.info(f"📊 Datos extraídos:")
            logger.info(f"   - Fecha: {'✓' if tiene_fecha else '✗ FALTANTE'} {extracted_data.get('fecha', 'N/A')}")
            logger.info(f"   - Importe: {'✓' if tiene_importe else '✗ FALTANTE'} {extracted_data.get('importe', 'N/A')}")
            logger.info(f"   - Tipo: {receipt_type}")
            
            status_msg = f"Procesado exitosamente en {elapsed:.1f}s"
            if not tiene_fecha or not tiene_importe:
                status_msg += " (⚠️ Datos incompletos)"
            
            # Reset model context
            self._llm.reset()
            
            return status_msg
            
        except InterruptedError as e:
            # Stop forzado - devolver item a pending
            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            logger.warning(f"⏰ Fin: {end_time.strftime('%H:%M:%S')}")
            logger.warning(f"⏱️  Tiempo: {elapsed:.1f}s")
            logger.warning(f"⚠️ PROCESAMIENTO INTERRUMPIDO: {str(e)}")
            try:
                # Mark as interrupted, which will reset to pending
                self.queue_service.interrupt_item(item.id)
                logger.info(f"  ➜ Item {item.id} marcado como interrupted (devuelto a pending)")
            except Exception as interrupt_error:
                logger.error(f"Error marking item as interrupted: {interrupt_error}")
            return None
        
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

    def analyze_image_for_test(self, image_path: str) -> dict[str, Any]:
        """Analyze a single receipt image without persisting the result."""

        img_path = Path(image_path)
        if not img_path.exists():
            raise FileNotFoundError(f"Imagen no encontrada: {image_path}")

        logger.info(f"🧪 Ejecutando OCR de prueba en: {img_path.name}")
        self._initialize_model()
        
        temp_file = None

        try:
            # Get image preprocessing config
            img_config = self.config.processor.get('image_preprocessing', {})
            enable_grayscale = img_config.get('enable_grayscale', False)
            resize_factor = img_config.get('resize_factor', 0)
            
            file_to_process = img_path
            
            # Step 1: Apply resize and/or grayscale if configured
            if resize_factor > 0 or enable_grayscale:
                logger.debug(f"  ➜ Applying image preprocessing (grayscale={enable_grayscale}, resize_factor={resize_factor})...")
                from src.utils.file_helpers import resize_to_factor
                
                processed_path, was_processed = resize_to_factor(
                    str(img_path),
                    resize_factor=resize_factor,
                    to_grayscale=enable_grayscale,
                    temp_dir=self.config.paths.get('temp_dir', './temp')
                )
                
                if was_processed:
                    temp_file = processed_path  # Mark for cleanup
                    file_to_process = Path(processed_path)
                    logger.debug(f"  ➜ Image preprocessed: {temp_file}")
                else:
                    logger.debug(f"  ➜ No preprocessing applied")
            else:
                logger.debug(f"  ➜ Image preprocessing disabled, using original image")
            
            # Step 2: Resize if still too large (KB size limit)
            max_kb = self.config.processor.get('max_image_size_kb', 600)
            logger.debug(f"  ➜ Checking size limit (max: {max_kb}KB)...")
            from src.utils.file_helpers import resize_image_if_needed
            resized_path, is_temp = resize_image_if_needed(file_to_process, max_kb)
            
            if is_temp:
                if temp_file and temp_file != file_to_process:
                    # Clean up previous temp and use new one
                    try:
                        Path(temp_file).unlink(missing_ok=True)
                    except:
                        pass
                temp_file = resized_path
                file_to_process = Path(resized_path)
                logger.debug(f"  ➜ Image resized to meet size limit: {temp_file}")
            
            logger.debug(f"  ➜ Final image for processing: {file_to_process}")
            
            data_uri = f"data:image/jpeg;base64,{image_to_base64(file_to_process)}"
            model_response = self._extract_with_simple_response(data_uri, stage=1)

            if not model_response:
                raise ValueError("No se obtuvo respuesta del modelo")

            parsed_fields = self._parse_simple_response_to_dict(model_response, stage=1)
            stage1_fields = parsed_fields.copy()

            detected_categories = parsed_fields.get('_detected_categories') or []
            if not detected_categories:
                detected_categories = self._detect_yes_responses(parsed_fields)

            auxiliary_fields: dict[str, Any] = {}
            if len(detected_categories) >= 2:
                auxiliary_result = self._ask_auxiliary_fields_text_only(detected_categories, parsed_fields)
                if auxiliary_result:
                    auxiliary_fields = auxiliary_result
                    parsed_fields.update(auxiliary_result)

            self._normalize_data(parsed_fields)
            final_fields = parsed_fields.copy()

            deduced_type = self.receipt_service.deduce_receipt_type(parsed_fields)

            return {
                'model_response': model_response,
                'stage1_fields': stage1_fields,
                'auxiliary_fields': auxiliary_fields,
                'final_fields': final_fields,
                'detected_categories': detected_categories,
                'deduced_type': deduced_type
            }

        finally:
            # Cleanup temp file
            if temp_file:
                logger.debug(f"  ➜ Cleaning up temp file: {temp_file}")
                try:
                    Path(temp_file).unlink(missing_ok=True)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temp file: {cleanup_error}")
            
            if self._llm:
                try:
                    self._llm.reset()
                except Exception as reset_error:
                    logger.warning(f"Error resetting VLM context after test run: {reset_error}")
    
    def _extract_with_simple_response(self, data_uri: str, stage: int) -> Optional[str]:
        """
        Call VLM model expecting JSON response.
        Format: {"basicos": {...}, "categoria": "..."}
        
        Args:
            data_uri: Base64 encoded image data URI
            stage: 1 for basic+category
            
        Returns:
            Raw JSON text response or None
        """
        base_max_tokens = self.config.processor.get('max_tokens', 2048)
        base_temperature = self.config.processor.get('temperature', 0.1)
        max_retries = 3
        
        prompt = self._get_extraction_prompt_simple(stage=1)
        
        for retry_attempt in range(max_retries):
            current_max_tokens = base_max_tokens * (2 ** retry_attempt)
            current_temperature = base_temperature + (retry_attempt * 0.05)
            
            if retry_attempt > 0:
                logger.warning(f"  🔄 Retry {retry_attempt}/{max_retries - 1} (tokens={current_max_tokens})")
            else:
                logger.info(f"  ➜ Calling VLM model (tokens={current_max_tokens})...")
            
            if self._force_stop:
                raise InterruptedError("Procesamiento interrumpido por stop forzado")
            
            response = self._llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": "Eres un experto en extracción de datos de recibos. Tu salida debe ser exclusivamente JSON válido sin texto adicional."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_uri}}
                        ]
                    }
                ],
                max_tokens=current_max_tokens,
                temperature=current_temperature,
                top_p=0.9
            )
            
            response_text = response["choices"][0]["message"]["content"].strip()
            
            if self._force_stop:
                raise InterruptedError("Procesamiento interrumpido por stop forzado")
            
            # Log the complete model response
            logger.info(f"  📝 Model response:\n{response_text}")
            
            # Validate response has JSON structure
            if "{" in response_text and "}" in response_text and len(response_text) > 10:
                if retry_attempt > 0:
                    logger.info(f"  ✅ Success after {retry_attempt} retries")
                return response_text
            else:
                logger.error(f"  ❌ Invalid response format on attempt {retry_attempt + 1}")
                
                if retry_attempt < max_retries - 1:
                    logger.warning("  ⏳ Retrying...")
                    time.sleep(2)
        
        logger.error("  💥 Failed to get valid response after retries")
        return None
    
    def _parse_simple_response_to_dict(self, response_text: str, stage: int) -> dict:
        """
        Parse JSON response to dictionary.
        
        Args:
            response_text: Raw JSON response with {"basicos": {...}, "categoria": "..."} or flat JSON
            stage: 1 for basic+category
            
        Returns:
            Dictionary with parsed data
        """
        try:
            # Parse JSON
            parsed = self._parse_json_response(response_text)
            if not parsed:
                logger.error("Failed to parse JSON response")
                return {}
            
            result = {}
            
            # Field mapping from JSON keys to database keys
            field_mapping = {
                'empresa': 'empresa',
                'nif': 'nif',
                'total': 'importe',
                'importe': 'importe',  # Handle both 'total' and 'importe'
                'moneda': 'moneda',
                'fecha': 'fecha',
                'hora': 'hora',
                'desc': 'descripcion',
                'descripcion': 'descripcion',  # Handle both 'desc' and 'descripcion'
                'factura': 'numero_factura',
                'numero_factura': 'numero_factura'  # Handle both formats
            }
            
            # Check if response has nested "basicos" structure
            if 'basicos' in parsed and isinstance(parsed['basicos'], dict):
                basicos = parsed['basicos']
                for json_key, db_key in field_mapping.items():
                    if json_key in basicos and basicos[json_key]:
                        value = basicos[json_key]
                        if str(value).upper() not in ['N/A', 'NULL', 'NONE', '']:
                            result[db_key] = value
                
                # Extract categories from nested structure (supports both 'categoria' and 'categorias')
                categorias_raw = parsed.get('categorias') or parsed.get('categoria')
                if categorias_raw:
                    categorias_str = str(categorias_raw)
                    if categorias_str and categorias_str.upper() not in ['N/A', 'NULL', 'NONE', 'OTROS', 'UNKNOWN', '']:
                        # Split by comma and process each category
                        categorias_list = [cat.strip() for cat in categorias_str.split(',') if cat.strip()]
                        
                        enabled_types = self.config_service.get_enabled_type_definitions()
                        detected_categories = []
                        
                        for categoria in categorias_list:
                            # Find matching type and set its indicator
                            for type_def in enabled_types:
                                if type_def.name.lower() == categoria.lower():
                                    if type_def.direct_indicator:
                                        field_key = type_def.direct_indicator.get('field_key')
                                        if field_key:
                                            result[field_key] = True
                                            detected_categories.append(type_def.name)
                                    break
                        
                        # Store all detected categories
                        if detected_categories:
                            result['_detected_categories'] = detected_categories
                            # Keep backward compatibility with single category
                            result['_detected_category'] = detected_categories[0]
            else:
                # Flat JSON structure - extract fields directly
                for json_key, db_key in field_mapping.items():
                    if json_key in parsed and parsed[json_key]:
                        value = parsed[json_key]
                        if str(value).upper() not in ['N/A', 'NULL', 'NONE', '']:
                            # Avoid duplicate fields (e.g., both 'total' and 'importe')
                            if db_key not in result:
                                result[db_key] = value
                
                # Look for category indicators in flat structure
                # Check for boolean type fields (e.g., "parking": true)
                enabled_types = self.config_service.get_enabled_type_definitions()
                detected_categories = []
                
                # First check boolean indicators
                for type_def in enabled_types:
                    if type_def.direct_indicator:
                        field_key = type_def.direct_indicator.get('field_key')
                        # Check if this type's indicator field exists and is true
                        if field_key and field_key in parsed and parsed[field_key] is True:
                            result[field_key] = True
                            detected_categories.append(type_def.name)
                
                # Then check for categorias/categoria field (supports multiple)
                categorias_raw = parsed.get('categorias') or parsed.get('categoria')
                if categorias_raw:
                    categorias_str = str(categorias_raw)
                    if categorias_str and categorias_str.upper() not in ['N/A', 'NULL', 'NONE', 'OTROS', 'UNKNOWN', '']:
                        categorias_list = [cat.strip() for cat in categorias_str.split(',') if cat.strip()]
                        
                        for categoria in categorias_list:
                            for type_def in enabled_types:
                                if type_def.name.lower() == categoria.lower():
                                    if type_def.direct_indicator:
                                        field_key = type_def.direct_indicator.get('field_key')
                                        if field_key and field_key not in result:
                                            result[field_key] = True
                                            if type_def.name not in detected_categories:
                                                detected_categories.append(type_def.name)
                                    break
                
                # Store detected categories
                if detected_categories:
                    result['_detected_categories'] = detected_categories
                    result['_detected_category'] = detected_categories[0]
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing JSON response: {e}")
            return {}
    
    def _detect_yes_responses(self, data: dict) -> list:
        """
        Detect which type fields have YES/True responses.
        
        Returns:
            List of type names that got YES
        """
        enabled_types = self.config_service.get_enabled_type_definitions()
        detected = []
        
        for type_def in enabled_types:
            if type_def.direct_indicator:
                field_key = type_def.direct_indicator.get('field_key')
                if field_key in data and data[field_key] is True:
                    detected.append(type_def.name)
        
        return detected
    
    def _ask_auxiliary_fields_text_only(self, detected_types: list, base_data: dict) -> Optional[dict]:
        """
        Ask for auxiliary fields via TEXT-ONLY conversation (no image reprocessing).
        
        Args:
            detected_types: List of type names detected
            base_data: Data from stage 1
            
        Returns:
            Dictionary with auxiliary fields or None
        """
        enabled_types = self.config_service.get_enabled_type_definitions()
        
        # Collect auxiliary fields for detected types
        aux_field_keys = []
        aux_field_questions = []
        
        for type_def in enabled_types:
            if type_def.name in detected_types:
                for field_key, field_config in type_def.auxiliary_fields.items():
                    if field_key not in aux_field_keys:
                        aux_field_keys.append(field_key)
                        aux_field_questions.append(field_config.get('question', field_key))
        
        if not aux_field_keys:
            return None
        
        # Build context from base_data
        context = "Datos ya extraídos del recibo:\n"
        for k, v in base_data.items():
            if v and v is not True and v is not False:
                context += f"- {k}: {v}\n"
        
        # Build text-only prompt
        prompt = f"{context}\nBasado en estos datos, responde las siguientes preguntas adicionales. "
        prompt += "Si no conoces una respuesta, responde 'N/A'. "
        prompt += f"Responde con {len(aux_field_keys)} valores separados por '/\\/' en este orden:\n\n"
        
        for i, question in enumerate(aux_field_questions, 1):
            prompt += f"{i}. {question}\n"
        
        prompt += "\nFormato de respuesta: valor1/\\/valor2/\\/valor3/..."
        
        # Text-only follow-up (uses conversation context, no new image)
        try:
            response = self._llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": "Eres un experto en análisis de recibos."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=512,
                temperature=0.1
            )
            
            response_text = response["choices"][0]["message"]["content"].strip()
            values = response_text.split(r"/\/")
            
            result = {}
            for i, value in enumerate(values):
                if i < len(aux_field_keys):
                    cleaned = value.strip()
                    if cleaned and cleaned.upper() not in ['N/A', 'NULL', 'NONE', '']:
                        result[aux_field_keys[i]] = cleaned
            
            return result if result else None
            
        except Exception as e:
            logger.error(f"Error in text-only auxiliary extraction: {e}")
            return None
    
    def _extract_with_retry(self, data_uri: str, stage: int, categories: list = None, base_data: dict = None) -> Optional[dict]:
        """
        Call VLM model with retry logic.
        
        Args:
            data_uri: Base64 encoded image data URI
            stage: 1 for common+weight10, 2 for auxiliary fields
            categories: List of category names for stage 2
            base_data: Base data from stage 1 (for stage 2 prompt context)
            
        Returns:
            Extracted data dictionary or None
        """
        base_max_tokens = self.config.processor.get('max_tokens', 2048)
        base_temperature = self.config.processor.get('temperature', 0.1)
        max_retries = 3
        extracted_data = None
        last_response_text = None
        
        # Generate prompt based on stage
        if stage == 1:
            prompt = self._get_extraction_prompt(stage=1)
        else:
            prompt = self._get_extraction_prompt(stage=2, categories=categories, base_data=base_data)
        
        for retry_attempt in range(max_retries):
            # Increase max_tokens on each retry: 2048 -> 4096 -> 8192
            current_max_tokens = base_max_tokens * (2 ** retry_attempt)
            # Slightly increase temperature on retries
            current_temperature = base_temperature + (retry_attempt * 0.05)
            
            if retry_attempt > 0:
                logger.warning(f"  🔄 Retry attempt {retry_attempt}/{max_retries - 1} with max_tokens={current_max_tokens}, temperature={current_temperature:.2f}")
            else:
                logger.info(f"  ➜ Calling VLM model (max_tokens={current_max_tokens})...")
            
            # Check for force stop
            if self._force_stop:
                raise InterruptedError("Procesamiento interrumpido por stop forzado")
            
            # Call VLM
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
                max_tokens=current_max_tokens,
                temperature=current_temperature,
                top_p=0.9
            )
            
            # Parse response
            logger.debug(f"  ➜ Parsing VLM response...")
            response_text = response["choices"][0]["message"]["content"]
            last_response_text = response_text
            logger.debug(f"  ➜ VLM response preview: {response_text[:200]}...")
            
            # Check for force stop
            if self._force_stop:
                raise InterruptedError("Procesamiento interrumpido por stop forzado")
            
            extracted_data = self._parse_json_response(response_text)
            
            if extracted_data:
                if retry_attempt > 0:
                    logger.info(f"  ✅ Successful extraction after {retry_attempt} retries")
                break
            else:
                logger.error(f"  ❌ Failed to extract JSON on attempt {retry_attempt + 1}/{max_retries}")
                logger.error(f"  📄 Raw VLM response ({len(response_text)} chars):")
                logger.error(f"  {response_text}")
                logger.error(f"  🔍 Response analysis:")
                logger.error(f"     - Contains '{{': {'{' in response_text}")
                logger.error(f"     - Contains '}}': {'}' in response_text}")
                logger.error(f"     - Contains 'json': {'json' in response_text.lower()}")
                logger.error(f"     - Empty response: {not response_text or not response_text.strip()}")
                
                if retry_attempt < max_retries - 1:
                    logger.warning(f"  ⏳ Will retry with increased parameters...")
                    time.sleep(2)
        
        if not extracted_data:
            logger.error(f"  💥 Failed to extract JSON after {max_retries} attempts")
            logger.error(f"  📊 Final attempt details:")
            logger.error(f"     - Max tokens used: {current_max_tokens}")
            logger.error(f"     - Temperature: {current_temperature:.2f}")
            logger.error(f"     - Response length: {len(last_response_text) if last_response_text else 0} chars")
        
        return extracted_data
    
    def _detect_categories_from_data(self, data: dict) -> list:
        """
        Detect which categories have 2+ weight-10 indicator fields answered.
        
        Args:
            data: Extracted data from stage 1
            
        Returns:
            List of category names that were detected
        """
        enabled_types = self.config_service.get_enabled_type_definitions()
        detected = []
        
        for type_def in enabled_types:
            if not type_def.direct_indicator:
                continue
            
            field_key = type_def.direct_indicator.get('field_key')
            
            # Check if this field was answered (not None, not empty string, not null/false for booleans)
            if field_key in data:
                value = data[field_key]
                # Consider answered if: non-empty string, True boolean, or any non-null value
                if value and str(value).strip().lower() not in ['null', 'none', 'false', 'no', 'n/a']:
                    detected.append(type_def.name)
                    logger.debug(f"  ✓ Category '{type_def.name}' detected via field '{field_key}' = '{value}'")
        
        # Only return categories if we have at least 1 strong indicator
        # (The user asked for 2+, but with single direct_indicator per type, we check if answered)
        return detected
    
    def _get_extraction_prompt_simple(self, stage: int = 1) -> str:
        """
        Get extraction prompt for Stage 1 with JSON response format.
        
        Returns:
            Prompt string requesting JSON response with basic fields and single category
        """
        enabled_types = self.config_service.get_enabled_type_definitions()
        
        # Build category list
        categories = [type_def.name for type_def in enabled_types]
        categories_str = ", ".join(categories)
        
        prompt = (
            "Analiza el recibo y clasifícalo según esta lista: "
            f"[{categories_str}].\n\n"
            "Regla: Solo incluye categorías con un nivel de confianza superior al 9%.\n\n"
            "Devuelve exclusivamente este formato JSON (sin texto adicional):\n"
            "{\n"
            '    "categorias": "lista de categorías separadas por comas"\n'
            "}"
        )
        
        return prompt
    
    def _get_extraction_prompt(self, stage: int = 1, categories: list = None, base_data: dict = None) -> str:
        """
        Get the extraction prompt for VLM with smart conditional field selection.
        
        Args:
            stage: Always 1 now (single-stage extraction)
            categories: Not used anymore
            base_data: Not used anymore
            
        Returns:
            Formatted JSON prompt string with conditional instructions
        """
        logger.debug("Building smart conditional prompt...")
        
        common_fields = self.config_service.get_common_fields()
        enabled_types = self.config_service.get_enabled_type_definitions()
        
        # Build common fields section
        common_section = {}
        for field_key, field_config in common_fields.items():
            common_section[field_key] = field_config.get('question', field_key)
        
        # Build type identification section (weight 10 indicators)
        type_indicators = {}
        type_auxiliary_map = {}  # Maps type name to its auxiliary fields
        
        for type_def in enabled_types:
            if type_def.direct_indicator:
                weight = type_def.direct_indicator.get('weight', 0)
                if weight == 10:
                    field_key = type_def.direct_indicator.get('field_key')
                    question = type_def.direct_indicator.get('question')
                    if field_key and question:
                        type_indicators[field_key] = question
                        # Store auxiliary fields for this type
                        type_auxiliary_map[type_def.name] = {
                            'indicator': field_key,
                            'fields': type_def.auxiliary_fields
                        }
        
        # Build conditional instructions for auxiliary fields
        conditional_instructions = "\n\n**IMPORTANTE**: Si identificas el tipo de recibo, incluye TAMBIÉN estos campos adicionales según corresponda:\n"
        
        for type_name, type_info in type_auxiliary_map.items():
            if type_info['fields']:
                conditional_instructions += f"\n• Si es **{type_name}** (campo '{type_info['indicator']}' = sí/true), incluye:\n"
                for aux_key, aux_config in type_info['fields'].items():
                    aux_question = aux_config.get('question', aux_key)
                    conditional_instructions += f"  - \"{aux_key}\": \"{aux_question}\"\n"
        
        # Build final prompt
        prompt = "Analiza el recibo e identifica su tipo. Extrae los datos básicos Y los campos específicos del tipo detectado.\n\n"
        prompt += "**CAMPOS BÁSICOS** (siempre extraer):\n{\n"
        
        basic_items = [f'  "{k}": "{v}"' for k, v in common_section.items()]
        basic_items.extend([f'  "{k}": "{v}"' for k, v in type_indicators.items()])
        
        prompt += ",\n".join(basic_items)
        prompt += "\n}\n"
        prompt += conditional_instructions
        prompt += "\n\nResponde en formato JSON con TODOS los campos encontrados (básicos + específicos del tipo). Omite campos vacíos."
        
        logger.debug(f"Smart prompt built with {len(common_section)} common fields + {len(type_indicators)} type indicators + conditional auxiliary fields")
        return prompt
    
    def _parse_json_response(self, response_text: str) -> Optional[dict]:
        """Parse JSON from model response, handling markdown code blocks."""
        try:
            text = response_text
            
            # Check for empty response
            if not text or not text.strip():
                logger.error("  ⚠️ VLM returned empty response")
                return None
            
            # Clean markdown code blocks
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                if end != -1:
                    text = text[start:end].strip()
                    logger.debug(f"  ➜ Extracted from ```json block")
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                if end != -1:
                    text = text[start:end].strip()
                    logger.debug(f"  ➜ Extracted from ``` block")
            
            # Extract JSON object with proper brace matching
            start_idx = text.find('{')
            if start_idx == -1:
                logger.error(f"  ⚠️ No opening brace '{{' found in response")
                return None
            
            # Find matching closing brace
            brace_count = 0
            end_idx = -1
            in_string = False
            escape_next = False
            
            for i in range(start_idx, len(text)):
                char = text[i]
                
                if escape_next:
                    escape_next = False
                    continue
                    
                if char == '\\':
                    escape_next = True
                    continue
                    
                if char == '"':
                    in_string = not in_string
                    continue
                    
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
            
            if end_idx == -1:
                logger.error(f"  ⚠️ No matching closing brace '}}' found (unclosed JSON object)")
                logger.error(f"  ℹ️ Opening brace at position {start_idx}, searched {len(text) - start_idx} chars")
                return None
            
            json_text = text[start_idx:end_idx]
            logger.debug(f"  ➜ Extracted JSON: {json_text[:100]}..." if len(json_text) > 100 else f"  ➜ Extracted JSON: {json_text}")
            
            parsed_data = json.loads(json_text)
            logger.debug(f"  ✓ Successfully parsed JSON with {len(parsed_data)} fields")
            return parsed_data
        
        except json.JSONDecodeError as e:
            logger.error(f"  ❌ JSON decode error at line {e.lineno}, column {e.colno}: {e.msg}")
            logger.error(f"  📄 Problematic JSON excerpt: {json_text[max(0, e.pos-50):e.pos+50] if 'json_text' in locals() else 'N/A'}")
        except Exception as e:
            logger.error(f"  ❌ Unexpected error parsing response: {type(e).__name__}: {e}")
        
        return None
    
    def _on_resource_mode_change(self, new_mode: str):
        """
        Callback when resource mode changes (normal <-> idle-boost).
        
        Args:
            new_mode: "normal" or "idle-boost"
        """
        logger.info(f"Resource mode changed to: {new_mode}")
        # Note: llama.cpp doesn't support dynamic thread adjustment after initialization
    
    def _get_active_worker_and_period(self) -> tuple[Optional[int], Optional[int]]:
        """
        Get the currently active worker and period for processing.
        
        Returns:
            Tuple of (worker_id, period_id) or (None, None) if no active period
        """
        try:
            from src.repositories.period_repository import PeriodRepository
            period_repo = PeriodRepository(self.db)
            
            # Get the active processing period
            active_period = period_repo.get_active_processing_period()
            
            if active_period:
                return (active_period.worker_id, active_period.id)
            else:
                logger.debug("No active processing period found")
                return (None, None)
                
        except Exception as e:
            logger.error(f"Error getting active worker/period: {e}")
            return (None, None)
    
    def is_actually_running(self) -> bool:
        """
        Check if processor is actually running (not just _is_running flag).
        
        Returns:
            True if worker thread is alive
        """
        if self._worker_thread and self._worker_thread.is_alive():
            return True
        
        # Check if any thread with our name exists
        for thread in threading.enumerate():
            if thread.name == PROCESSOR_THREAD_NAME and thread.is_alive():
                self._worker_thread = thread
                self._is_running = True
                return True
        
        # If we thought we were running but thread is dead, update state
        if self._is_running:
            logger.warning("⚠️ Processor marked as running but thread is dead - correcting state")
            self._is_running = False
            self.config_service.set_system_config(PROCESSOR_PID_KEY, None)
        
        return False
    
    def get_stats(self) -> dict:
        """Get processing statistics."""
        _, period_id = self._get_active_worker_and_period()
        queue_stats = self.queue_service.get_queue_stats(period_id)
        resource_usage = self.resource_monitor.get_current_usage()
        
        # Update running state based on actual thread status
        actual_running = self.is_actually_running()
        
        return {
            **self.stats,
            'queue': queue_stats,
            'resources': resource_usage,
            'is_running': actual_running,
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
                # Format as string with dot separator (consistent with Decimal format)
                data['total'] = str(normalized)
    
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
