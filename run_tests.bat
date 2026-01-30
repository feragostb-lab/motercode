@echo off
REM Batch script to run ALL application tests using pytest
REM 
REM This script activates the virtual environment and runs the complete test suite

echo.
echo ================================================================================
echo Receipt Management System - Test Suite Runner
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

REM Check if tests directory exists
if not exist "tests" (
    echo ERROR: Tests directory not found!
    echo Expected: tests/
    echo.
    pause
    exit /b 1
)

REM Check if pytest is installed
python -m pytest --version >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: pytest is not installed!
    echo Installing pytest and pytest-cov...
    echo.
    pip install pytest pytest-cov
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install pytest
        pause
        exit /b 1
    )
    echo.
    echo ✓ pytest installed successfully
    echo.
)

REM Run the test suite with pytest
echo.
echo Running pytest test suite...
echo.
echo Tests include:
echo   - Unit tests (tests/unit/)
echo   - Integration tests (tests/integration/)
echo   - Coverage report will be generated in htmlcov/
echo.

python -m pytest

REM Check exit code
if %errorlevel% neq 0 (
    echo.
    echo ================================================================================
    echo Tests FAILED with error code %errorlevel%
    echo ================================================================================
    echo.
    pause
    exit /b %errorlevel%
)

echo.
echo ================================================================================
echo Tests completed successfully!
echo ================================================================================
echo.
echo Results:
echo   - Summary shown above
echo   - Coverage report: htmlcov\index.html
echo   - To view coverage: start htmlcov\index.html
echo.
echo Optional manual tests:
echo   - OCR End-to-End test: python old\test_receipt_processing.py
echo   - Transaction ID tests: python old\test_transaction_id_preservation.py
echo.
pause
