"""
PyInstaller spec for Unified Application (app.py).
This builds the modular app with all integrated components.
"""

# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules
import sys
import os
import llama_cpp

block_cipher = None

# Custom collection for llama_cpp to preserve lib structure
llama_cpp_path = os.path.dirname(llama_cpp.__file__)
llama_lib_path = os.path.join(llama_cpp_path, 'lib')

# Collect all Streamlit components (critical for web assets)
streamlit_datas, streamlit_binaries, streamlit_hiddenimports = collect_all('streamlit')
altair_datas, altair_binaries, altair_hiddenimports = collect_all('altair')
plotly_datas, plotly_binaries, plotly_hiddenimports = collect_all('plotly')

# Additional data files
extra_datas = [
    # Include src package
    ('../src', 'src'),
    # Include modules package
    ('../modules', 'modules'),
    # Include config
    ('../config.yaml', '.'),
    # Include llama_cpp lib folder explicitly as data
    (llama_lib_path, 'llama_cpp/lib'),
    # Include app.py source code for Streamlit to run it
    ('../app.py', '.'),
]

a = Analysis(
    ['../app.py'],
    pathex=[],
    binaries=streamlit_binaries + altair_binaries + plotly_binaries,
    datas=extra_datas + streamlit_datas + altair_datas + plotly_datas,
    hiddenimports=[
        # Streamlit (comprehensive collection via collect_all)
        *streamlit_hiddenimports,
        *altair_hiddenimports,
        *plotly_hiddenimports,
        # Additional Streamlit runtime dependencies
        'streamlit.runtime.scriptrunner.magic_funcs',
        'streamlit.elements.arrow_altair',
        'streamlit.components.v1',
        'streamlit.runtime.caching',
        # OCR/AI
        'llama_cpp',
        # Data processing
        'pandas',
        'openpyxl',
        # Plotly already collected via collect_all
        # System
        'pystray',
        'psutil',
        'win10toast',
        'PIL',
        'PIL._tkinter_finder',
        # Config
        'yaml',
        # Database
        'sqlite3',
        # All module imports
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
    console=True,  # Keep console for logging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # TODO: Add icon file
)

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
