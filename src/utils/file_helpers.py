"""File handling utilities."""
import base64
import io
from pathlib import Path
from PIL import Image
from typing import Tuple, Optional, Dict
import logging

logger = logging.getLogger(__name__)


def optimize_image_for_vlm(image_path: str, target_size: int = 672, 
                           to_grayscale: bool = True, temp_dir: str = './temp') -> Tuple[str, bool]:
    """
    Optimize image for VLM processing: grayscale conversion + resize to target dimensions.
    Reduces computational load by ~50% while maintaining text readability.
    
    Args:
        image_path: Path to the image file
        target_size: Target size for longest dimension (default 672px)
        to_grayscale: Convert to grayscale (default True)
        temp_dir: Directory for temporary optimized images
        
    Returns:
        Tuple of (path_to_optimized_image, was_optimized)
    """
    try:
        # Create temp directory if it doesn't exist
        Path(temp_dir).mkdir(parents=True, exist_ok=True)
        
        # Open image
        img = Image.open(image_path)
        original_size = img.size
        
        # Convert to grayscale if requested (reduces color channels 3->1)
        if to_grayscale:
            img = img.convert('L')  # Convert to grayscale
            img = img.convert('RGB')  # Convert back to RGB for VLM compatibility (3 channels)
        
        # Resize maintaining aspect ratio with longest side = target_size
        width, height = img.size
        if max(width, height) > target_size:
            if width > height:
                new_width = target_size
                new_height = int(height * (target_size / width))
            else:
                new_height = target_size
                new_width = int(width * (target_size / height))
            
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            img_resized = img  # Already smaller than target
        
        # Save optimized image
        temp_filename = f"vlm_opt_{Path(image_path).stem}.jpg"
        temp_path = str(Path(temp_dir) / temp_filename)
        img_resized.save(temp_path, 'JPEG', quality=85, optimize=True)
        
        # Calculate reduction
        original_pixels = original_size[0] * original_size[1]
        new_pixels = img_resized.size[0] * img_resized.size[1]
        reduction = (1 - (new_pixels / original_pixels)) * 100 if original_pixels > new_pixels else 0
        
        logger.info(f"VLM optimization: {original_size} -> {img_resized.size} "
                   f"({'grayscale' if to_grayscale else 'color'}, ~{reduction:.1f}% reduction)")
        
        return temp_path, True
        
    except Exception as e:
        logger.warning(f"Failed to optimize image for VLM: {e}, using original")
        return image_path, False


def convert_pdf_to_image(pdf_path: str, temp_dir: str = './temp') -> Tuple[str, bool]:
    """
    Convert PDF to image (stitches pages vertically if multiple).
    
    Args:
        pdf_path: Path to PDF file
        temp_dir: Directory for temporary images
        
    Returns:
        Tuple of (path_to_image, was_converted)
    """
    if not str(pdf_path).lower().endswith('.pdf'):
        return pdf_path, False

    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF (fitz) not found. Cannot convert PDF. Install 'pymupdf'.")
        return pdf_path, False

    try:
        # Create temp directory
        Path(temp_dir).mkdir(parents=True, exist_ok=True)
        
        doc = fitz.open(pdf_path)
        if doc.page_count == 0:
            return pdf_path, False
            
        images = []
        total_height = 0
        max_width = 0
        
        # Render each page to an image
        for page in doc:
            # Zoom = 2.0 for better quality (roughly 144 dpi)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            images.append(img)
            
            total_height += img.height
            max_width = max(max_width, img.width)
            
        doc.close()
        
        # Stitch images if multiple, otherwise use the single one
        if len(images) > 1:
            stitched_img = Image.new('RGB', (max_width, total_height), (255, 255, 255))
            y_offset = 0
            for img in images:
                # Center image if smaller than max width
                x_offset = (max_width - img.width) // 2
                stitched_img.paste(img, (x_offset, y_offset))
                y_offset += img.height
            final_img = stitched_img
        else:
            final_img = images[0]
            
        # Save as JPG
        temp_filename = f"pdf_conv_{Path(pdf_path).stem}.jpg"
        temp_path = str(Path(temp_dir) / temp_filename)
        final_img.save(temp_path, 'JPEG', quality=90)
        
        logger.info(f"Converted PDF {Path(pdf_path).name} to image {temp_filename} (pages={len(images)})")
        return temp_path, True
        
    except Exception as e:
        logger.error(f"Error converting PDF {pdf_path}: {e}")
        return pdf_path, False


def remove_white_lines(image_path: str, temp_dir: str = './temp', threshold: int = 50) -> Tuple[str, bool]:
    """
    Elimina grandes bloques de espacio horizontal blanco dentro de la imagen.
    
    Args:
        image_path: Ruta a la imagen
        temp_dir: Directorio para imágenes temporales
        threshold: Número mínimo de filas blancas consecutivas para ser consideradas un espacio a borrar.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        logger.error("OpenCV/Numpy missing")
        return image_path, False

    try:
        img = cv2.imread(image_path)
        if img is None:
            return image_path, False

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Binarize (Invertir: texto=blanco, fondo=negro)
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        
        # Proyección horizontal
        # Si la suma de píxeles blancos en una fila es 0 (o muy bajo), es una línea vacía
        horizontal_sum = np.sum(thresh, axis=1)
        
        # Definimos qué es "contenido": filas que superan el 1% de 'ruido'
        has_content = horizontal_sum > (thresh.shape[1] * 0.01 * 255)
        
        height = img.shape[0]
        
        # Máscara global de filas a mantener
        mask = np.ones(height, dtype=bool)
        
        # Iterar para encontrar gaps consecutivos
        empty_count = 0
        for i in range(height):
            if not has_content[i]:
                empty_count += 1
            else:
                # Si veníamos de un hueco grande y encontramos contenido
                if empty_count > threshold:
                    # Marcamos para borrar (False) el hueco, dejando un pequeño margen (padding)
                    padding = 20
                    start_gap = i - empty_count + padding
                    end_gap = i - padding
                    
                    if end_gap > start_gap:
                        mask[start_gap:end_gap] = False
                
                empty_count = 0
                
        # Si la imagen termina en un gran espacio en blanco, borrarlo también
        if empty_count > threshold:
            start_gap = height - empty_count + 20
            mask[start_gap:height] = False

        # Si no hemos borrado nada, devolvemos false
        if np.all(mask):
            return image_path, False
            
        # Construir la nueva imagen usando la máscara
        new_img = img[mask, :]

        # Guardar
        Path(temp_dir).mkdir(parents=True, exist_ok=True)
        temp_filename = f"stitched_{Path(image_path).stem}.jpg"
        temp_path = str(Path(temp_dir) / temp_filename)
        
        cv2.imwrite(temp_path, new_img)
        logger.info(f"Removed internal whitespace: {img.shape[0]}h -> {new_img.shape[0]}h")
        
        return temp_path, True
        
    except Exception as e:
        logger.error(f"Error removing white lines from {image_path}: {e}")
        return image_path, False


def resize_image_if_needed(image_path: str, max_size_kb: int = 150, 
                          temp_dir: str = './temp') -> Tuple[str, bool]:
    """
    Resize image if it exceeds max_size_kb.
    
    Args:
        image_path: Path to the image file
        max_size_kb: Maximum size in KB
        temp_dir: Directory for temporary resized images
        
    Returns:
        Tuple of (path_to_use, was_resized)
    """
    file_size_kb = Path(image_path).stat().st_size / 1024
    
    if file_size_kb <= max_size_kb:
        return image_path, False
    
    # Create temp directory if it doesn't exist
    Path(temp_dir).mkdir(parents=True, exist_ok=True)
    
    # Open and resize image
    try:
        img = Image.open(image_path)
        
        # Calculate new size (reduce by ratio to get under max_size_kb)
        ratio = (max_size_kb / file_size_kb) ** 0.5  # Square root for area reduction
        new_width = int(img.width * ratio)
        new_height = int(img.height * ratio)
        
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save to temp file
        temp_filename = f"temp_resized_{Path(image_path).name}"
        temp_path = str(Path(temp_dir) / temp_filename)
        img_resized.save(temp_path, quality=85, optimize=True)
        
        logger.info(f"Resized {image_path} from {file_size_kb:.1f}KB to ~{max_size_kb}KB")
        return temp_path, True
        
    except Exception as e:
        logger.error(f"Error resizing image {image_path}: {e}")
        return image_path, False


def resize_to_factor(image_path: str, resize_factor: int, to_grayscale: bool = False,
                    temp_dir: str = './temp') -> Tuple[str, bool]:
    """
    Resize image adjusting the longest side to resize_factor (must be multiple of 28).
    Maintains aspect ratio.
    
    Args:
        image_path: Path to the image file
        resize_factor: Target size for longest side (must be multiple of 28, e.g., 672)
        to_grayscale: Convert to grayscale before resizing
        temp_dir: Directory for temporary resized images
        
    Returns:
        Tuple of (path_to_resized_image, was_resized)
    """
    if resize_factor <= 0:
        return image_path, False
    
    # Ensure resize_factor is multiple of 28
    if resize_factor % 28 != 0:
        resize_factor = round(resize_factor / 28) * 28
        logger.warning(f"Resize factor adjusted to nearest multiple of 28: {resize_factor}")
    
    try:
        # Create temp directory if it doesn't exist
        Path(temp_dir).mkdir(parents=True, exist_ok=True)
        
        # Open image
        img = Image.open(image_path)
        original_size = img.size
        width, height = img.size
        
        # Convert to grayscale if requested
        if to_grayscale:
            img = img.convert('L')  # Convert to grayscale
            img = img.convert('RGB')  # Convert back to RGB for VLM compatibility
        
        # Calculate new dimensions maintaining aspect ratio
        longest_side = max(width, height)
        
        # Skip if already at target size or smaller
        if longest_side <= resize_factor:
            if to_grayscale:
                # Still need to save the grayscale version
                temp_filename = f"resized_{resize_factor}_{Path(image_path).stem}.jpg"
                temp_path = str(Path(temp_dir) / temp_filename)
                img.save(temp_path, 'JPEG', quality=85, optimize=True)
                logger.info(f"Applied grayscale, no resize needed: {original_size}")
                return temp_path, True
            return image_path, False
        
        # Calculate new size
        if width > height:
            new_width = resize_factor
            new_height = int(height * (resize_factor / width))
        else:
            new_height = resize_factor
            new_width = int(width * (resize_factor / height))
        
        # Resize image
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save resized image
        temp_filename = f"resized_{resize_factor}_{Path(image_path).stem}.jpg"
        temp_path = str(Path(temp_dir) / temp_filename)
        img_resized.save(temp_path, 'JPEG', quality=85, optimize=True)
        
        logger.info(f"Resized image: {original_size} -> {img_resized.size} "
                   f"(factor={resize_factor}, {'grayscale' if to_grayscale else 'color'})")
        
        return temp_path, True
        
    except Exception as e:
        logger.warning(f"Failed to resize image: {e}, using original")
        return image_path, False


def image_to_base64(image_path: str) -> Optional[str]:
    """
    Convert image file to base64 string.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Base64 encoded string or None if error
    """
    try:
        with open(image_path, 'rb') as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except Exception as e:
        logger.error(f"Error encoding image {image_path}: {e}")
        return None


def cleanup_temp_files(temp_dir: str = './temp', pattern: str = 'temp_resized_*'):
    """
    Clean up temporary files matching pattern.
    
    Args:
        temp_dir: Directory containing temp files
        pattern: Glob pattern to match files
    """
    temp_path = Path(temp_dir)
    if not temp_path.exists():
        return
    
    deleted_count = 0
    for temp_file in temp_path.glob(pattern):
        try:
            temp_file.unlink()
            deleted_count += 1
        except Exception as e:
            logger.warning(f"Failed to delete {temp_file}: {e}")
    
    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} temporary files")


def ensure_directory_exists(directory: str):
    """
    Create directory if it doesn't exist.
    
    Args:
        directory: Path to directory
    """
    Path(directory).mkdir(parents=True, exist_ok=True)


def get_file_extension(filename: str) -> str:
    """
    Get file extension including the dot.
    
    Args:
        filename: Name of the file
        
    Returns:
        Extension (e.g., '.jpeg', '.jpg')
    """
    return Path(filename).suffix


def get_image_files(directory: str, extensions: Tuple[str, ...] = ('.jpg', '.jpeg', '.png', '.webp', '.pdf')) -> list:
    """
    Get all image files from a directory.
    
    Args:
        directory: Path to directory
        extensions: Tuple of valid extensions (default includes .pdf)
        
    Returns:
        List of image file paths
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        return []
    
    image_files = []
    for ext in extensions:
        image_files.extend(dir_path.glob(f'*{ext}'))
        image_files.extend(dir_path.glob(f'*{ext.upper()}'))
    
    return [str(f) for f in sorted(image_files)]


def get_period_paths(worker_name: str, month_year: str) -> Dict[str, Path]:
    """
    Get all paths for a worker's period.
    
    Args:
        worker_name: Worker name
        month_year: Period in format "MMYYYY"
        
    Returns:
        Dict with keys: 'base', 'img', 'result', 'csv'
    """
    base = Path('./workers') / worker_name / month_year
    
    return {
        'base': base,
        'img': base / 'img',
        'result': base / 'result',
        'csv': base / 'csv',
    }


def validate_worker_name(name: str) -> bool:
    """
    Validate worker name (alphanumeric only).
    
    Args:
        name: Name to validate
        
    Returns:
        True if valid
    """
    import re
    return bool(re.match(r'^[a-zA-Z0-9]+$', name))

