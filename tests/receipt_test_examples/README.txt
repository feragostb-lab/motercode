# Add Your Test Images Here

This directory is for testing the receipt processing pipeline.

## Instructions

1. **Copy receipt images to this directory**
   - Drag and drop your test receipt images here
   - Supported formats: `.jpg`, `.jpeg`, `.png`

2. **Run the tests**
   - Go back to the project root directory
   - Run: `run_tests.bat` (Windows) or `python test_receipt_processing.py`

3. **View results**
   - Check console output for real-time progress
   - Find processed receipts in `result/` directory
   - Review logs in `logs/receipt_test.log`

## Example Test Images

Good test cases include:
- ✅ Clear, high-quality scans
- ✅ Photos of receipts with good lighting
- ✅ Various types: taxi, hotel, restaurant, parking, toll
- ✅ Different languages (Spanish preferred)
- ✅ Various date formats

Challenging test cases:
- ⚠️ Blurry or low-quality images
- ⚠️ Rotated or skewed images
- ⚠️ Handwritten receipts
- ⚠️ Faded or low-contrast text
- ⚠️ Complex multi-page invoices

## What Gets Tested

The test script will:
1. Load each image
2. Process it through the VLM model
3. Extract receipt data (company, date, amount, type)
4. Save the processed receipt
5. Generate a detailed report

## Expected Processing Time

- **Per image**: ~120-180 seconds (2-3 minutes)
- **5 images**: ~10-15 minutes total
- **Turbo mode**: Can be faster with higher resource usage

## Need Help?

If you encounter issues:
1. Check `logs/receipt_test.log` for detailed error messages
2. Ensure VLM model is properly configured in `config.yaml`
3. Verify images are valid (not corrupted)
4. Make sure you have enough disk space and memory

---

**Currently: No test images**

Please add receipt images to this directory to begin testing.
