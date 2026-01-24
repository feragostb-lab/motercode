"""File handling utilities."""
import base64
import io
from pathlib import Path
from PIL import Image
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


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
