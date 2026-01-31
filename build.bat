@echo off
REM Build script for creating Windows executables with PyInstaller

echo ============================================================
echo Building Receipt Processing System Executables
echo ============================================================
echo.


REM 2. Limpieza de compilaciones previas (User Request)
echo Limpiando carpetas temporales...
if exist build rd /s /q build
if exist dist rd /s /q dist

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
pip install py-cpuinfo
echo.

REM 1. Forzar compilacion para PC Antiguo (SSE2, sin AVX/FMA)
echo Limpiando cache de pip para asegurar recompilacion limpia...
pip cache purge

echo Configurando flags de compilacion Legacy (SSE2)...
REM Estos flags fuerzan a MSVC a usar SSE2 y desactivan optimizaciones modernas que crashean en CPUs viejas
set CMAKE_ARGS=-DGGML_NATIVE=OFF -DGGML_AVX=OFF -DGGML_AVX2=OFF -DGGML_AVX512=OFF -DGGML_FMA=OFF -DGGML_F16C=OFF -DGGML_OPENMP=OFF -DCMAKE_C_FLAGS="/arch:SSE2" -DCMAKE_CXX_FLAGS="/arch:SSE2" -DGGML_CPU_ALL_VARIANTS=OFF

echo Instalando llama-cpp-python con soporte Legacy...
pip install llama-cpp-python --force-reinstall --no-cache-dir --verbose
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Fallo la compilacion de llama-cpp-python
    pause
    exit /b 1
)
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

REM Build Hardware Diagnostic Tool
echo ============================================================
echo Building Hardware Check Utility...
echo ============================================================
pyinstaller --onefile --name check_ai_hardware scripts\check_ai_hardware.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Hardware Check build failed
    pause
    exit /b 1
)

REM Move Hardware Check to App folder and create launcher
if exist dist\check_ai_hardware.exe (
    echo Moving check_ai_hardware.exe to dist\RecibosApp...
    move /Y dist\check_ai_hardware.exe dist\RecibosApp\
    
    echo Creating Diagnostic Launcher...
    (
        echo @echo off
        echo echo Iniciando Diagnostico de Hardware...
        echo check_ai_hardware.exe
        echo pause
    ) > dist\RecibosApp\DIAGNOSTICO_HARDWARE.bat
)

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
