"""
Manual test for whitespace trimming/removal feature.
"""
import sys
import os
from pathlib import Path
import cv2

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.file_helpers import remove_white_lines

def test_trim_whitespace():
    print("="*60)
    print("✂️  WHITESPACE TRIM TEST")
    print("="*60)
    
    # Check dependencies
    try:
        import cv2
        import numpy as np
        print(f"✅ OpenCV version: {cv2.__version__}")
        print(f"✅ Numpy version: {np.__version__}")
    except ImportError:
        print("❌ OpenCV or Numpy NOT installed. Please run: pip install opencv-python-headless numpy")
        return

    # Check input file
    input_path = Path('./doc/examples/imageToTrim.jpg')
    temp_dir = Path('./temp/test_trim')
    
    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        # Try to find any jpg in doc/examples as fallback
        fallback = list(Path('./doc/examples').glob('*.jpg'))
        if fallback:
            input_path = fallback[0]
            print(f"⚠️  Using fallback file: {input_path}")
        else:
            return

    print(f"\n📄 Processing: {input_path.name}")
    
    # Get original dimensions
    img = cv2.imread(str(input_path))
    if img is None:
        print("❌ Failed to load image with OpenCV")
        return
        
    h, w, _ = img.shape
    print(f"  📏 Original Size: {w}x{h} px")
    
    try:
        # Run trimming
        output_path, was_trimmed = remove_white_lines(str(input_path), str(temp_dir))
        
        if was_trimmed:
            print(f"  ✅ Trimming success!")
            print(f"  📂 Output: {output_path}")
            
            # Verify result
            out_img = cv2.imread(output_path)
            oh, ow, _ = out_img.shape
            print(f"  📏 New Size:      {ow}x{oh} px")
            
            reduction = (1 - (oh/h)) * 100
            print(f"  📉 Height reduced by: {reduction:.1f}% ({h} -> {oh} px)")
        else:
            print(f"  ⚠️  No trimming performed (was_trimmed=False)")
            print(f"      - This might mean the image has no significant empty horizontal bands.")
            print(f"      - Or the threshold (2%) wasn't met.")

    except Exception as e:
        print(f"  💥 Error during trimming: {e}")

    print("\n" + "="*60)
    print(f"Test Complete. Check '{temp_dir}' for results.")
    print("="*60)

if __name__ == "__main__":
    test_trim_whitespace()
