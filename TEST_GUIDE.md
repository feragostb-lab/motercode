# Receipt Processing Test Guide

## Overview

A comprehensive test suite for validating the receipt processing pipeline using Vision Language Model (VLM) OCR.

## Files Created

```
test/
├── receipt_test_examples/        # Directory for test images
│   └── README.txt               # Instructions for adding test images
└── README.md                    # Test documentation

test_receipt_processing.py        # Main test script
run_tests.bat                     # Windows batch runner
```

## Quick Start

### 1. Add Test Images

Copy receipt images to `test/receipt_test_examples/`:

```bash
# Example
copy your_receipts\*.jpg test\receipt_test_examples\
```

### 2. Run Tests

**Option A - Using Batch Script (Recommended for Windows):**
```batch
run_tests.bat
```

**Option B - Direct Python:**
```bash
python test_receipt_processing.py
```

**Option C - Custom Directory:**
```bash
python test_receipt_processing.py --test-dir ./my_custom_test_images
```

## What the Test Script Does

### Phase 1: Environment Setup
- ✅ Verifies test directory exists
- ✅ Lists all test images found
- ✅ Shows file sizes and counts

### Phase 2: Queue Preparation
- ✅ Clears existing queue items
- ✅ Enqueues test images for processing

### Phase 3: Processing
- ✅ Loads VLM model
- ✅ Processes each image sequentially
- ✅ Logs detailed progress for each item
- ✅ Captures timing metrics
- ✅ Handles errors gracefully

### Phase 4: Results Summary
- ✅ Queue statistics (completed, failed, pending)
- ✅ Receipt statistics (total, by type)
- ✅ Detailed per-image results
- ✅ Success rate calculation

## Sample Test Output

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    RECEIPT PROCESSING TEST SUITE                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

Test Directory: C:\WORKSPACE\gguf\test\receipt_test_examples
Start Time: 2026-01-25 14:30:00

================================================================================
SETTING UP TEST ENVIRONMENT
================================================================================
✓ Found 3 test images
  - taxi_receipt.jpg (245.3 KB)
  - hotel_invoice.jpg (189.7 KB)
  - restaurant_bill.jpg (156.2 KB)

Clearing existing queue items...
  ✓ Queue is empty

================================================================================
ENQUEUEING TEST IMAGES
================================================================================
✓ Enqueued 3 images for processing

================================================================================
STARTING RECEIPT PROCESSING
================================================================================
Processing 3 pending items...
VLM Model: models/Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf
Max Tokens: 512
Temperature: 0.1

--------------------------------------------------------------------------------
📸 PROCESSING ITEM 1/3
   File: taxi_receipt.jpg
   Queue ID: 1
--------------------------------------------------------------------------------
Loading VLM model (first time)...
✅ SUCCESS - Completed in 142.3s
   📊 Receipt Details:
      Type: Taxis
      Date: 2026-01-15
      Amount: 25.50
      File: result/260115_2550_Taxis.jpg

--------------------------------------------------------------------------------
📸 PROCESSING ITEM 2/3
   File: hotel_invoice.jpg
   Queue ID: 2
--------------------------------------------------------------------------------
✅ SUCCESS - Completed in 156.7s
   📊 Receipt Details:
      Type: Hoteles
      Date: 2026-01-14
      Amount: 89.00
      File: result/260114_8900_Hoteles.jpg

--------------------------------------------------------------------------------
📸 PROCESSING ITEM 3/3
   File: restaurant_bill.jpg
   Queue ID: 3
--------------------------------------------------------------------------------
❌ FAILED - Failed to extract JSON from response
   Duration: 158.2s

================================================================================
PROCESSING COMPLETE
================================================================================
Total time: 457.2s
Processed: 3 items
Average: 152.4s per item

================================================================================
TEST SUMMARY
================================================================================

📊 Queue Statistics:
   Completed: 2
   Failed: 1
   Pending: 0

📄 Receipt Statistics:
   Total Receipts: 2
   By Type:
      - Hoteles: 1
      - Taxis: 1

📋 Detailed Results:
   1. ✅ taxi_receipt.jpg
      Duration: 142.3s
      Type: Taxis
      Amount: 25.50
   2. ✅ hotel_invoice.jpg
      Duration: 156.7s
      Type: Hoteles
      Amount: 89.00
   3. ❌ restaurant_bill.jpg
      Duration: 158.2s
      Error: Failed to extract JSON from response

✨ Success Rate: 66.7% (2/3)

================================================================================
TEST COMPLETE
================================================================================
```

## Understanding Results

### Success Indicators
- ✅ **Green checkmark** - Receipt processed successfully
- **Duration** - Time taken to process the image
- **Receipt Details** - Extracted type, date, and amount
- **Output File** - Location of processed receipt

### Failure Indicators
- ❌ **Red X** - Processing failed
- **Error message** - Reason for failure
- Common errors:
  - `Failed to extract JSON from response` - Model couldn't parse the image
  - `File not found` - Image path invalid
  - `VLM returned empty response` - Model confused by image

### Success Rate
- **Target**: >90% for good quality images
- **Acceptable**: >80% for mixed quality images
- **Needs Attention**: <70% success rate

## Interpreting Logs

### Complete Logs
Check `logs/receipt_test.log` for:
- Full VLM responses
- Detailed extraction attempts
- Resource usage metrics
- Error stack traces

### Key Log Sections
1. **Model loading** - VLM initialization time
2. **Image processing** - Per-image detailed steps
3. **Data extraction** - JSON parsing attempts
4. **Error details** - Stack traces for failures

## Troubleshooting

### No Images Found
```
⚠️ No images found in test/receipt_test_examples
```
**Solution**: Add `.jpg`, `.jpeg`, or `.png` images to the test directory

### VLM Model Not Found
```
ERROR: Model file not found
```
**Solution**: Verify `config.yaml` has correct model path

### Processing Takes Too Long
Each image takes 2-3 minutes with current settings.
**Solutions**:
- Use fewer test images initially
- Enable "Turbo Mode" for faster processing
- Check CPU/RAM usage isn't maxed out

### High Failure Rate
If >30% of images fail:
1. Check image quality (resolution, contrast)
2. Verify images aren't corrupted
3. Review VLM model configuration
4. Check log files for common error patterns

## Best Practices

### Test Image Selection
1. **Start small**: Test with 2-3 images first
2. **Vary types**: Include different receipt types
3. **Quality mix**: Include both clear and challenging images
4. **Known data**: Use receipts where you know the correct values

### Running Tests
1. **Single run**: For quick validation
2. **Batch run**: For comprehensive testing
3. **Monitor logs**: Watch for patterns in failures
4. **Compare results**: Validate extracted data accuracy

### After Testing
1. Review success/failure patterns
2. Investigate failed images
3. Adjust VLM parameters if needed
4. Re-test problematic images

## Advanced Usage

### Custom Test Directory
```bash
python test_receipt_processing.py --test-dir ./production_samples
```

### Automated Testing
Integrate into CI/CD pipeline:
```bash
# Run tests and capture exit code
python test_receipt_processing.py
if [ $? -eq 0 ]; then
    echo "Tests passed"
else
    echo "Tests failed"
    exit 1
fi
```

### Performance Benchmarking
Track processing times over multiple runs to:
- Identify performance regressions
- Optimize VLM parameters
- Monitor resource usage trends

## Support

For issues or questions:
1. Check `logs/receipt_test.log` for detailed errors
2. Review test summary output
3. Verify configuration in `config.yaml`
4. Test with known-good images first

---

**Ready to test?**

1. Add images to `test/receipt_test_examples/`
2. Run `run_tests.bat`
3. Review results and logs
