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

REM Verify critical dependencies
echo Verificando dependencias criticas...
python -c "import streamlit; print('  Streamlit:', streamlit.__version__)" || (
    echo ERROR: Streamlit no esta instalado
    echo Ejecuta: pip install -r requirements.txt
    pause
    exit /b 1
)
python -c "from PyInstaller.utils.hooks import collect_all; print('  PyInstaller hooks: OK')" 2>nul || (
    echo ADVERTENCIA: PyInstaller puede no tener todos los hooks
)
echo.

REM Install/update PyInstaller
echo Instalando/actualizando PyInstaller...
pip install --upgrade pyinstaller
echo.

REM Build Unified App (NEW - v2.0)
echo ============================================================
echo Building RecibosApp.exe (Unified Application)...
echo Usando archivo: build_config\app.spec
echo ============================================================
pyinstaller build_config\app.spec --clean --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Unified app build failed
    pause
    exit /b 1
)
echo Unified app build completed!
echo.

REM Build Setup (Config utility)
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

REM Optional: Build Legacy Apps (uncomment if needed)
REM echo ============================================================
REM echo Building Legacy Apps (optional)...
REM echo ============================================================
REM pyinstaller build_config\processor.spec --clean --noconfirm
REM pyinstaller build_config\dashboard.spec --clean --noconfirm
REM echo.

echo ============================================================
echo Build Summary
echo ============================================================
echo All executables built successfully in dist\ folder:
echo   - RecibosApp.exe       (Main unified application - v2.0)
echo   - ConfigSetup.exe      (Configuration utility)
echo.
echo NOTE: Legacy apps (RecibosProcessor.exe, RecibosDashboard.exe)
echo       are no longer built by default. Uncomment in build.bat if needed.
echo.
echo Next steps:
echo 1. Copy models\ folder to dist\RecibosApp\
echo 2. Verify config.yaml is in dist\RecibosApp\
echo 3. Run installer.bat to create full package (if available)
echo ============================================================
pause
