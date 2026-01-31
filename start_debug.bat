@echo off
REM Script de depuración con información detallada

echo ============================================================
echo Receipt Management System - Modo DEBUG
echo ============================================================
echo.

REM Activar entorno virtual
if exist .venv\Scripts\activate.bat (
    echo [*] Activando entorno virtual...
    call .venv\Scripts\activate.bat
) else (
    echo [ERROR] No se encontró el entorno virtual .venv
    echo Por favor ejecuta: python -m venv .venv
    pause
    exit /b 1
)

echo.
echo [*] Información del sistema:
echo    Python: 
python --version
echo    Streamlit:
python -c "import streamlit; print('   ', streamlit.__version__)" 2>nul || echo     [ERROR] No instalado

echo.
echo [*] Verificando dependencias críticas:
python -c "import llama_cpp; print('    llama_cpp: OK')" 2>nul || echo     llama_cpp: [ERROR]
python -c "import pandas; print('    pandas: OK')" 2>nul || echo     pandas: [ERROR]
python -c "import PIL; print('    PIL: OK')" 2>nul || echo     PIL: [ERROR]
python -c "import yaml; print('    yaml: OK')" 2>nul || echo     yaml: [ERROR]

echo.
echo [*] Verificando archivos:
if exist app.py (echo     app.py: OK) else (echo     app.py: [ERROR] No encontrado)
if exist config.yaml (echo     config.yaml: OK) else (echo     config.yaml: [ERROR] No encontrado)

echo.
echo ============================================================
echo Iniciando aplicación con logging detallado...
echo ============================================================
echo.

REM Ejecutar con variables de entorno de debug
set STREAMLIT_LOG_LEVEL=debug
streamlit run app.py --logger.level=debug

echo.
echo ============================================================
echo La aplicación ha terminado.
if errorlevel 1 (
    echo [ERROR] La aplicación terminó con errores.
    echo Código de salida: %errorlevel%
)
echo ============================================================
echo.
pause
