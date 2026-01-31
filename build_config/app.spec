"""
PyInstaller spec for Unified Application (app.py).
This builds the modular app with all integrated components.
"""

# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['../app.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include src package
        ('../src', 'src'),
        # Include modules package
        ('../modules', 'modules'),
        # Include config
        ('../config.yaml', '.'),
    ],
    hiddenimports=[
        # Streamlit
        'streamlit',
        'streamlit.runtime.scriptrunner.magic_funcs',
        'streamlit.elements.arrow_altair',
        # OCR/AI
        'llama_cpp',
        'llama_cpp.llama_chat_format',
        # Data processing
        'pandas',
        'openpyxl',
        'plotly',
        'plotly.graph_objs',
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
