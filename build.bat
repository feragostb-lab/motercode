@echo off
REM Build script for creating Windows executables with PyInstaller

echo ============================================================
echo Building Receipt Processing System Executables
echo ============================================================
echo.

REM Check if virtual environment is activated
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found in PATH
    echo Please activate the virtual environment first
    pause
    exit /b 1
)

REM Install/update PyInstaller
echo Installing PyInstaller...
pip install --upgrade pyinstaller
echo.

REM Build Processor
echo ============================================================
echo Building RecibosProcessor.exe...
echo ============================================================
pyinstaller build_config\processor.spec --clean --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Processor build failed
    pause
    exit /b 1
)
echo Processor build completed!
echo.

REM Build Dashboard
echo ============================================================
echo Building RecibosDashboard.exe...
echo ============================================================
pyinstaller build_config\dashboard.spec --clean --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Dashboard build failed
    pause
    exit /b 1
)
echo Dashboard build completed!
echo.

REM Build Setup
echo ============================================================
echo Building ConfigSetup.exe...
echo ============================================================
pyinstaller build_config\setup.spec --clean --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Setup build failed
    pause
    exit /b 1
)
echo Setup build completed!
echo.

echo ============================================================
echo Build Summary
echo ============================================================
echo All executables built successfully in dist\ folder:
echo   - RecibosProcessor.exe
echo   - RecibosDashboard.exe
echo   - ConfigSetup.exe
echo.
echo Next steps:
echo 1. Copy models\ folder to dist\
echo 2. Copy config.yaml to dist\
echo 3. Run installer.bat to create full package
echo ============================================================
pause
