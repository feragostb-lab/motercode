@echo off
REM Inicio rápido de la aplicación unificada

echo ========================================
echo Receipt Management System - Inicio
echo ========================================
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

echo [*] Verificando instalacion de Streamlit...
python -c "import streamlit; print('  Streamlit version:', streamlit.__version__)" 2>nul
if errorlevel 1 (
    echo [ERROR] Streamlit no esta instalado correctamente
    echo Ejecuta: pip install -r requirements.txt
    pause
    exit /b 1
)

echo [*] Iniciando aplicación unificada...
echo.
echo La aplicación se abrirá en tu navegador en http://localhost:8501
echo.
echo Presiona Ctrl+C para detener la aplicación
echo.
echo ============================================================
echo.

streamlit run app.py

echo.
echo ============================================================
echo La aplicacion ha terminado.
if errorlevel 1 (
    echo [ERROR] La aplicacion termino con errores.
    echo Revisa los mensajes de error arriba.
)
echo ============================================================
echo.
pause
