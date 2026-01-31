"""
PyInstaller spec for OCR Processor executable.

TODO: Customize paths and includes based on actual dependencies.
This is a template - adjust as needed during implementation.
"""

# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Collect all Streamlit components (critical for web assets)
streamlit_datas, streamlit_binaries, streamlit_hiddenimports = collect_all('streamlit')

# Additional data files
extra_datas = [
    # Include src package
    ('../src', 'src'),
    # Include config example
    ('../config.yaml', '.'),
]

a = Analysis(
    ['../app_processor.py'],
    pathex=[],
    binaries=streamlit_binaries,
    datas=extra_datas + streamlit_datas,
    hiddenimports=[
        *streamlit_hiddenimports,
        'llama_cpp',
        'llama_cpp.llama_chat_format',
        'pystray',
        'psutil',
        'win10toast',
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
    name='RecibosProcessor',
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
    name='RecibosProcessor',
)
