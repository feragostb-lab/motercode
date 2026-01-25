@echo off
REM Scripts de inicio - Receipt Management System

:menu
cls
echo ========================================
echo Receipt Management System
echo ========================================
echo.
echo Seleccione la aplicación a ejecutar:
echo.
echo 1. Aplicación Unificada (Recomendado)
echo 2. OCR Processor (Solo)
echo 3. Dashboard (Solo)
echo 4. ROC Skincare (Solo)
echo 5. Salir
echo.
set /p choice="Opción (1-5): "

if "%choice%"=="1" goto unified
if "%choice%"=="2" goto processor
if "%choice%"=="3" goto dashboard
if "%choice%"=="4" goto rocskincare
if "%choice%"=="5" goto end
goto menu

:unified
cls
echo [*] Iniciando Aplicación Unificada...
call .venv\Scripts\activate.bat
streamlit run app.py
goto menu

:processor
cls
echo [*] Iniciando OCR Processor...
call .venv\Scripts\activate.bat
streamlit run app_processor.py
goto menu

:dashboard
cls
echo [*] Iniciando Dashboard...
call .venv\Scripts\activate.bat
streamlit run app_dashboard.py
goto menu

:rocskincare
cls
echo [*] Iniciando ROC Skincare...
call .venv\Scripts\activate.bat
streamlit run app_rocskincare.py
goto menu

:end
echo.
echo Gracias por usar Receipt Management System
echo.
pause
