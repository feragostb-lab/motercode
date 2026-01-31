@echo off
REM Script de verificación pre-build

echo ============================================================
echo Verificacion Pre-Build - Receipt Management System
echo ============================================================
echo.

set ERROR_COUNT=0

REM Verificar entorno virtual
if exist .venv\Scripts\activate.bat (
    echo [OK] Entorno virtual encontrado
    call .venv\Scripts\activate.bat
) else (
    echo [ERROR] No se encontro el entorno virtual .venv
    set /a ERROR_COUNT+=1
)
echo.

REM Verificar Python
echo Verificando Python...
python --version 2>nul
if errorlevel 1 (
    echo [ERROR] Python no encontrado
    set /a ERROR_COUNT+=1
) else (
    echo [OK] Python encontrado
)
echo.

REM Verificar dependencias críticas
echo Verificando dependencias criticas...
echo.

python -c "import streamlit; print('[OK] Streamlit:', streamlit.__version__)" 2>nul || (
    echo [ERROR] Streamlit no instalado
    set /a ERROR_COUNT+=1
)

python -c "import llama_cpp; print('[OK] llama_cpp instalado')" 2>nul || (
    echo [ERROR] llama_cpp no instalado
    set /a ERROR_COUNT+=1
)

python -c "import pandas; print('[OK] pandas instalado')" 2>nul || (
    echo [ERROR] pandas no instalado
    set /a ERROR_COUNT+=1
)

python -c "import PIL; print('[OK] PIL instalado')" 2>nul || (
    echo [ERROR] PIL no instalado
    set /a ERROR_COUNT+=1
)

python -c "import yaml; print('[OK] yaml instalado')" 2>nul || (
    echo [ERROR] yaml no instalado
    set /a ERROR_COUNT+=1
)

python -c "import openpyxl; print('[OK] openpyxl instalado')" 2>nul || (
    echo [ERROR] openpyxl no instalado
    set /a ERROR_COUNT+=1
)

python -c "import plotly; print('[OK] plotly instalado')" 2>nul || (
    echo [ERROR] plotly no instalado
    set /a ERROR_COUNT+=1
)

echo.
echo Verificando PyInstaller y hooks...
python -c "import PyInstaller; print('[OK] PyInstaller:', PyInstaller.__version__)" 2>nul || (
    echo [ERROR] PyInstaller no instalado
    set /a ERROR_COUNT+=1
)

python -c "from PyInstaller.utils.hooks import collect_all; print('[OK] PyInstaller hooks disponibles')" 2>nul || (
    echo [ADVERTENCIA] PyInstaller hooks pueden no estar disponibles
)

echo.
REM Verificar archivos necesarios
echo Verificando archivos necesarios...
if exist app.py (echo [OK] app.py) else (echo [ERROR] app.py no encontrado & set /a ERROR_COUNT+=1)
if exist config.yaml (echo [OK] config.yaml) else (echo [ERROR] config.yaml no encontrado & set /a ERROR_COUNT+=1)
if exist build_config\app.spec (echo [OK] build_config\app.spec) else (echo [ERROR] app.spec no encontrado & set /a ERROR_COUNT+=1)
if exist src (echo [OK] Carpeta src/) else (echo [ERROR] Carpeta src/ no encontrada & set /a ERROR_COUNT+=1)
if exist modules (echo [OK] Carpeta modules/) else (echo [ERROR] Carpeta modules/ no encontrada & set /a ERROR_COUNT+=1)

echo.
echo ============================================================
echo Resumen de Verificacion
echo ============================================================
if %ERROR_COUNT% EQU 0 (
    echo.
    echo [EXITO] Todas las verificaciones pasaron!
    echo Puedes ejecutar build.bat ahora.
    echo.
) else (
    echo.
    echo [ERROR] Se encontraron %ERROR_COUNT% problema(s)
    echo Por favor, resuelve los errores antes de ejecutar build.bat
    echo.
    echo Soluciones comunes:
    echo - Si faltan paquetes Python, ejecuta: pip install -r requirements.txt
    echo - Si falta el entorno virtual, ejecuta: python -m venv .venv
    echo.
)
echo ============================================================
pause
