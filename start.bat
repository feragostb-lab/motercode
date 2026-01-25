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

echo [*] Iniciando aplicación unificada...
echo.
echo La aplicación se abrirá en tu navegador en http://localhost:8501
echo.
echo Presiona Ctrl+C para detener la aplicación
echo.

streamlit run app.py

pause
