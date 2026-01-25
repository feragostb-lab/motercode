# Receipt Processing Test Suite

This directory contains test images and scripts for testing the receipt processing pipeline.

## Quick Start

1. **Add test images** to the `receipt_test_examples/` directory:
   - Supported formats: JPG, JPEG, PNG
   - Any receipt images you want to test

2. **Run the test script**:
   ```bash
   # Windows
   .\run_tests.bat
   
   # Or directly with Python
   python test_receipt_processing.py
   ```

3. **View results**:
   - Check the console output for detailed logs
   - Check `logs/receipt_test.log` for complete log file
   - Processed receipts will be in the `result/` directory

## Test Script Features

The test script provides:

- ✅ **Complete logging** of the entire processing pipeline
- ✅ **Detailed metrics** for each image processed
- ✅ **Success/failure tracking** for each receipt
- ✅ **Performance measurements** (processing time per image)
- ✅ **Summary report** with statistics

## Example Output

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    RECEIPT PROCESSING TEST SUITE                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

Test Directory: C:\WORKSPACE\gguf\test\receipt_test_examples
Start Time: 2026-01-25 14:30:00

================================================================================
SETTING UP TEST ENVIRONMENT
================================================================================
✓ Found 5 test images
  - taxi_receipt_1.jpg (245.3 KB)
  - hotel_receipt_1.jpg (189.7 KB)
  - restaurant_receipt_1.jpg (156.2 KB)
  - parking_receipt_1.jpg (98.5 KB)
  - toll_receipt_1.jpg (112.8 KB)

================================================================================
ENQUEUEING TEST IMAGES
================================================================================
✓ Enqueued 5 images for processing

================================================================================
STARTING RECEIPT PROCESSING
================================================================================
Processing 5 pending items...
VLM Model: models/Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf
Max Tokens: 512
Temperature: 0.1

--------------------------------------------------------------------------------
📸 PROCESSING ITEM 1/5
   File: taxi_receipt_1.jpg
   Queue ID: 1
--------------------------------------------------------------------------------
✅ SUCCESS - Completed in 142.3s
   📊 Receipt Details:
      Type: Taxis
      Date: 2026-01-15
      Amount: 25.50
      File: result/260115_2550_Taxis.jpg

[... more items ...]

================================================================================
TEST SUMMARY
================================================================================

📊 Queue Statistics:
   Completed: 4
   Failed: 1
   Pending: 0

📄 Receipt Statistics:
   Total Receipts: 4
   By Type:
      - Taxis: 1
      - Hoteles: 1
      - Comidas: 1
      - Estacionamiento: 1

✨ Success Rate: 80.0% (4/5)

================================================================================
TEST COMPLETE
================================================================================
```

## Adding Test Images

To add test images to this test suite:

1. Place receipt images in `receipt_test_examples/` directory
2. Supported formats: `.jpg`, `.jpeg`, `.png`
3. Images can be:
   - Taxi receipts
   - Hotel invoices
   - Restaurant bills
   - Parking tickets
   - Toll receipts
   - Any other expense receipt

## Customization

You can customize the test by passing arguments:

```bash
# Use a different test directory
python test_receipt_processing.py --test-dir ./my_test_images
```

## Troubleshooting

**No images found:**
- Make sure images are in the correct directory
- Check that files have proper extensions (.jpg, .jpeg, .png)

**Processing fails:**
- Check that the VLM model is properly configured in `config.yaml`
- Ensure the model files exist in the `models/` directory
- Check logs in `logs/receipt_test.log` for detailed error messages

**Slow processing:**
- Each image takes ~120-180 seconds with the current model
- Consider using "Turbo Mode" for faster processing
- Ensure sufficient CPU/RAM resources

## Output Files

After running tests, you'll find:

- **`result/`** - Processed receipt images with standardized names
- **`logs/receipt_test.log`** - Complete processing log
- **Database** - Receipt data stored in SQLite database
- **Console output** - Real-time progress and summary
