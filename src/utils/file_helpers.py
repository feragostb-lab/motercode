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


def get_image_files(directory: str, extensions: Tuple[str, ...] = ('.jpg', '.jpeg', '.png')) -> list:
    """
    Get all image files from a directory.
    
    Args:
        directory: Path to directory
        extensions: Tuple of valid extensions
        
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

