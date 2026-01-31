@echo off
REM ============================================================
REM Package Builder - Creates full distribution package
REM Creates a ready-to-distribute folder with all necessary files
REM ============================================================

echo ============================================================
echo Receipt Management System - Package Builder
echo ============================================================
echo.

set PACKAGE_DIR=dist\RecibosPackage
set APP_DIR=dist\RecibosApp
set SETUP_DIR=dist\ConfigSetup

REM Check if build exists
if not exist "%APP_DIR%\RecibosApp.exe" (
    echo ERROR: RecibosApp.exe not found!
    echo Please run build.bat first to create the executables.
    pause
    exit /b 1
)

REM Clean previous package
if exist "%PACKAGE_DIR%" (
    echo Cleaning previous package...
    rmdir /s /q "%PACKAGE_DIR%"
)

REM Create package structure
echo Creating package structure...
mkdir "%PACKAGE_DIR%"
mkdir "%PACKAGE_DIR%\models"
mkdir "%PACKAGE_DIR%\img"
mkdir "%PACKAGE_DIR%\result"
mkdir "%PACKAGE_DIR%\exports"
mkdir "%PACKAGE_DIR%\logs"
mkdir "%PACKAGE_DIR%\backups"
mkdir "%PACKAGE_DIR%\temp"
mkdir "%PACKAGE_DIR%\workers"
mkdir "%PACKAGE_DIR%\doc"

REM Copy main application
echo Copying main application...
xcopy /E /I /Y "%APP_DIR%\*" "%PACKAGE_DIR%\app\"

REM Copy config setup utility
if exist "%SETUP_DIR%\ConfigSetup.exe" (
    echo Copying config utility...
    xcopy /E /I /Y "%SETUP_DIR%\*" "%PACKAGE_DIR%\setup\"
)

REM Copy models (if they exist in dist)
if exist "%APP_DIR%\*.gguf" (
    echo Copying GGUF models...
    copy "%APP_DIR%\*.gguf" "%PACKAGE_DIR%\models\" >nul
) else (
    echo WARNING: GGUF models not found in %APP_DIR%
    echo You'll need to copy them manually to %PACKAGE_DIR%\models\
)

REM Copy configuration
if exist "%APP_DIR%\config.yaml" (
    echo Copying configuration...
    copy "%APP_DIR%\config.yaml" "%PACKAGE_DIR%\config.yaml" >nul
) else if exist "config.yaml" (
    copy "config.yaml" "%PACKAGE_DIR%\config.yaml" >nul
)

REM Copy documentation
echo Copying documentation...
copy README.md "%PACKAGE_DIR%\README.md" >nul
copy USER_GUIDE.md "%PACKAGE_DIR%\USER_GUIDE.md" >nul
copy DEVELOPER_GUIDE.md "%PACKAGE_DIR%\doc\DEVELOPER_GUIDE.md" >nul

REM Create startup script
echo Creating startup script...
(
echo @echo off
echo REM Launcher for Receipt Management System
echo echo ============================================================
echo echo Receipt Management System - Starting...
echo echo ============================================================
echo echo.
echo.
echo cd /d "%%~dp0"
echo.
echo REM Check if database exists
echo if not exist "receipts.db" ^(
echo     echo First run detected - initializing database...
echo     echo Database will be created automatically on first use.
echo     echo.
echo ^)
echo.
echo REM Start the application
echo echo Starting RecibosApp...
echo start "" "app\RecibosApp.exe"
echo.
echo echo Application started!
echo echo Check the browser window that should open automatically.
echo echo If browser doesn't open, navigate to: http://localhost:8501
echo echo.
echo echo Press any key to close this window...
echo pause ^>nul
) > "%PACKAGE_DIR%\START_APP.bat"

REM Create config setup script
if exist "%PACKAGE_DIR%\setup\ConfigSetup.exe" (
    echo Creating config setup script...
    (
    echo @echo off
    echo REM Configuration Setup Utility
    echo echo ============================================================
    echo echo Configuration Setup Utility
    echo echo ============================================================
    echo echo.
    echo cd /d "%%~dp0"
    echo setup\ConfigSetup.exe
    echo echo.
    echo echo Configuration complete!
    echo pause
    ) > "%PACKAGE_DIR%\SETUP_CONFIG.bat"
)

REM Create README for package
echo Creating package README...
(
echo # Receipt Management System - Distribution Package
echo.
echo ## Quick Start
echo.
echo 1. **First Time Setup**:
echo    - Double-click `SETUP_CONFIG.bat` to configure the system ^(optional^)
echo    - Or use the default `config.yaml` included
echo.
echo 2. **Run Application**:
echo    - Double-click `START_APP.bat`
echo    - Wait for the browser to open automatically
echo    - If it doesn't open, navigate to: http://localhost:8501
echo.
echo 3. **IMPORTANT**: GGUF Models Required
echo    - Models should be in the `models\` folder
echo    - Required files:
echo      * Qwen_Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf
echo      * mmproj-Qwen2.5-VL-7B-Instruct-Q8_0.gguf
echo    - Download from: https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct-GGUF
echo.
echo ## Folder Structure
echo.
echo - `app\` - Main application executable and dependencies
echo - `setup\` - Configuration setup utility
echo - `models\` - AI models ^(GGUF files^)
echo - `img\` - Input images for processing
echo - `result\` - Processed receipts
echo - `exports\` - Excel/CSV exports
echo - `logs\` - Application logs
echo - `backups\` - Database backups
echo - `workers\` - ROC Skincare worker data
echo - `doc\` - Documentation
echo - `config.yaml` - Main configuration file
echo.
echo ## Documentation
echo.
echo - `README.md` - General overview
echo - `USER_GUIDE.md` - Complete user guide
echo - `doc\DEVELOPER_GUIDE.md` - Technical documentation
echo.
echo ## Support
echo.
echo For issues or questions, refer to the documentation files.
) > "%PACKAGE_DIR%\PACKAGE_README.txt"

REM Create uninstall info
(
echo To uninstall:
echo 1. Delete this entire folder
echo 2. No registry entries or system files are created
echo.
echo Your data ^(database, exports, etc.^) is contained within this folder.
echo Make backups before deleting if you want to preserve your data.
) > "%PACKAGE_DIR%\UNINSTALL_INFO.txt"

echo.
echo ============================================================
echo Package Creation Summary
echo ============================================================
echo.
echo Package created successfully at: %PACKAGE_DIR%
echo.
echo Contents:
echo   - Main application (RecibosApp.exe)
echo   - Configuration utility
echo   - Startup scripts
echo   - Directory structure
echo   - Documentation
echo.
echo IMPORTANT - Manual Steps Required:
echo.
echo 1. Verify GGUF models are in: %PACKAGE_DIR%\models\
echo    If not, copy them from your models\ folder
echo.
echo 2. Review config.yaml and adjust paths if needed
echo.
echo 3. Test the package:
echo    - Navigate to %PACKAGE_DIR%
echo    - Run START_APP.bat
echo.
echo 4. To distribute:
echo    - Compress %PACKAGE_DIR% to ZIP
echo    - Share the ZIP file with end users
echo.
echo ============================================================
pause
