@echo off
REM Batch script to run receipt processing tests
REM 
REM This script activates the virtual environment and runs the test suite

echo.
echo ================================================================================
echo Receipt Processing Test Runner
echo ================================================================================
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run this script from the project root directory.
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Check if test script exists
if not exist "tests_receipt_processing.py" (
    echo ERROR: Test script not found!
    echo Expected: test_receipt_processing.py
    echo.
    pause
    exit /b 1
)

REM Check if test images directory exists
if not exist "tests\receipt_test_examples" (
    echo WARNING: Test images directory not found!
    echo Creating directory: tests\receipt_test_examples
    mkdir "tests\receipt_test_examples"
    echo.
    echo Please add test receipt images to: tests\receipt_test_examples
    echo Supported formats: .jpg, .jpeg, .png
    echo.
    echo TIP: You can copy some images from workers directory for testing:
    echo   copy workers\david\012026\img\*.jpeg tests\receipt_test_examples\
    echo.
    pause
    exit /b 0
)

REM Run the test script
echo.
echo Starting tests...
echo.
python test_receipt_processing.py

REM Check exit code
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Tests failed with error code %errorlevel%
    echo.
    pause
    exit /b %errorlevel%
)

echo.
echo ================================================================================
echo Tests completed successfully!
echo ================================================================================
echo.
echo Check the following for results:
echo   - Console output above
echo   - logs/receipt_test.log for complete logs
echo   - result/ directory for processed receipts
echo.
pause
