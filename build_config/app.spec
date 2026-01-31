# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Unified Application (app.py).
This builds the modular app with all integrated components and hybrid backend support.
"""

from PyInstaller.utils.hooks import collect_all
import os
import llama_cpp  # Necesario para localizar la ruta de instalación base

block_cipher = None

# --- 1. LOCALIZACIÓN DE LA BASE INSTALADA (LEGACY/SSE2) ---
# Esta ruta apunta a donde pip instaló la versión base
llama_cpp_root = os.path.dirname(llama_cpp.__file__)

# --- 2. RECOLECCIÓN DE DEPENDENCIAS (AQUÍ ESTÁ STREAMLIT) ---
# Recolectamos todo lo necesario para Streamlit, Altair y Plotly
streamlit_datas, streamlit_binaries, streamlit_hiddenimports = collect_all('streamlit')
altair_datas, altair_binaries, altair_hiddenimports = collect_all('altair')
plotly_datas, plotly_binaries, plotly_hiddenimports = collect_all('plotly')

# --- 3. DEFINICIÓN DE ARCHIVOS DE DATOS ---
# Usamos '../' porque el archivo .spec está dentro de la carpeta 'build_config'
extra_datas = [
    # Código fuente y configuración
    ('../src', 'src'),
    ('../modules', 'modules'),
    ('../config.yaml', '.'),
    
    # APP PRINCIPAL
    ('../app.py', '.'),

    # --- MOTOR DE IA HÍBRIDO ---
    # A) Versión Base (Legacy/SSE2) -> Se copia a la raíz de la librería
    (llama_cpp_root, 'llama_cpp'),
    
    # B) Variantes Optimizadas -> Se copian a carpetas ocultas para inyección
    # Nota: Asumimos que la carpeta 'libs_variants' está en la raíz del proyecto
    ('../libs_variants/avx2/*.dll', 'llama_cpp/variants/avx2'),
    ('../libs_variants/avx512/*.dll', 'llama_cpp/variants/avx512'),
]

# --- 4. ANÁLISIS ---
a = Analysis(
    ['../app.py'],
    pathex=[],
    # AQUÍ SE USAN LAS VARIABLES DEFINIDAS ARRIBA
    binaries=streamlit_binaries + altair_binaries + plotly_binaries,
    datas=extra_datas + streamlit_datas + altair_datas + plotly_datas,
    hiddenimports=[
        # Dependencias recolectadas automáticamente
        *streamlit_hiddenimports,
        *altair_hiddenimports,
        *plotly_hiddenimports,
        
        # Streamlit Runtime extra
        'streamlit.runtime.scriptrunner.magic_funcs',
        'streamlit.elements.arrow_altair',
        'streamlit.components.v1',
        'streamlit.runtime.caching',
        
        # Librerías críticas
        'llama_cpp',
        'cpuinfo',    # CRÍTICO: Para detectar el hardware en tiempo de ejecución
        'pandas',
        'openpyxl',
        'pystray',
        'psutil',
        'win10toast',
        'PIL',
        'PIL._tkinter_finder',
        'yaml',
        'sqlite3',
        
        # Tus módulos de la aplicación
        'modules.processor_page',
        'modules.dashboard_receipts',
        'modules.dashboard_bank_transactions',
        'modules.dashboard_export',
        'modules.dashboard_statistics',
        'modules.dashboard_common',
        'modules.rocskincare_workers',
        'modules.rocskincare_periods',
        'modules.rocskincare_period_closure',
        'modules.rocskincare_csv_upload',
        'modules.rocskincare_image_upload',
        'modules.rocskincare_visualization',
        'modules.admin_page',
        'modules.admin_test_receipt',
        'modules.failed_items_page',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# --- 5. EJECUTABLE (SOLO CONSOLA) ---
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RecibosApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# --- 6. COLECCIÓN (CARPETA FINAL) ---
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RecibosApp',
)