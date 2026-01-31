"""
PyInstaller spec for Dashboard executable.
"""

# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Collect all Streamlit components (critical for web assets)
streamlit_datas, streamlit_binaries, streamlit_hiddenimports = collect_all('streamlit')
plotly_datas, plotly_binaries, plotly_hiddenimports = collect_all('plotly')

# Additional data files
extra_datas = [
    # Include src package
    ('../src', 'src'),
    # Include config
    ('../config.yaml', '.'),
]

a = Analysis(
    ['../app_dashboard.py'],
    pathex=[],
    binaries=streamlit_binaries + plotly_binaries,
    datas=extra_datas + streamlit_datas + plotly_datas,
    hiddenimports=[
        *streamlit_hiddenimports,
        *plotly_hiddenimports,
        'pandas',
        'openpyxl',
        'PIL',
        'yaml',
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
    name='RecibosDashboard',
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
    icon=None,  # TODO: Add icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RecibosDashboard',
)
