"""
Manual test for PDF conversion and processing logic.
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.file_helpers import convert_pdf_to_image, get_image_files

def test_pdf_conversion():
    print("="*60)
    print("🧪 PDF CONVERSION TEST")
    print("="*60)
    
    # Check dependencies
    try:
        import fitz
        print(f"✅ PyMuPDF (fitz) is installed. Version: {fitz.version}")
    except ImportError:
        print("❌ PyMuPDF is NOT installed. Please run: pip install pymupdf")
        return

    # Check input files
    pdf_path = Path('./doc/examples/tiket.pdf')
    pdf_path2 = Path('./doc/examples/tiket2.pdf')
    temp_dir = Path('./temp/test_pdf_conversion')
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    pdfs_to_test = []
    if pdf_path.exists(): pdfs_to_test.append(pdf_path)
    else: print(f"⚠️ Warning: {pdf_path} not found")
    
    if pdf_path2.exists(): pdfs_to_test.append(pdf_path2)
    else: print(f"⚠️ Warning: {pdf_path2} not found")
    
    if not pdfs_to_test:
        print("❌ No test PDFs found in ./doc/examples/")
        return

    for pdf in pdfs_to_test:
        print(f"\n📄 Testing: {pdf.name}")
        try:
            converted_path, success = convert_pdf_to_image(str(pdf), str(temp_dir))
            
            if success:
                print(f"  ✅ Conversion success!")
                print(f"  📂 Output: {converted_path}")
                
                # Check file size
                size_kb = Path(converted_path).stat().st_size / 1024
                print(f"  📏 Size: {size_kb:.2f} KB")
                
                # Verify it is an image
                from PIL import Image
                img = Image.open(converted_path)
                print(f"  🖼️  Dimensions: {img.size} (Width x Height)")
                print(f"  ℹ️  Format: {img.format}")
            else:
                print(f"  ❌ Conversion failed (returned success=False)")
                
        except Exception as e:
            print(f"  💥 Error during conversion: {e}")

    print("\n" + "="*60)
    print("Test Complete. Check './temp/test_pdf_conversion' for results.")
    print("="*60)

if __name__ == "__main__":
    test_pdf_conversion()
