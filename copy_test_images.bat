@echo off
REM Helper script to copy test images from workers directory

echo.
echo ================================================================================
echo Copying Test Images
echo ================================================================================
echo.

REM Check if workers directory exists
if not exist "workers\david\012026\img" (
    echo ERROR: Source directory not found: workers\david\012026\img
    echo.
    echo Please ensure you have images in the workers directory first.
    pause
    exit /b 1
)

REM Create test directory if needed
if not exist "test\receipt_test_examples" (
    echo Creating test directory...
    mkdir "test\receipt_test_examples"
)

REM Copy 2-3 sample images for testing
echo Copying sample images for testing...
echo.

set count=0
for %%f in (workers\david\012026\img\*.jpeg) do (
    if !count! lss 2 (
        echo Copying: %%~nxf
        copy "%%f" "test\receipt_test_examples\" > nul
        set /a count+=1
    )
)

echo.
echo Copied %count% images to test\receipt_test_examples
echo.
dir /b test\receipt_test_examples
echo.
echo ================================================================================
echo Ready to test!
echo Run: run_tests.bat
echo ================================================================================
pause
