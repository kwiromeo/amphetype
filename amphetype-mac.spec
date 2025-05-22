# -*- mode: python ; coding: utf-8 -*-
# Spec file equivalent to pyinstaller --windowed --onefile -w
from PyInstaller.utils.hooks import collect_data_files
import sys
from pathlib import Path

block_cipher = None

# Get the version from the VERSION file
version_path = Path('amphetype/VERSION')
if version_path.exists():
    VERSION = version_path.open('r').read().strip()
else:
    VERSION = '1.0.0'  # Default version if file not found

# Collect all data files from the package
datas = collect_data_files('amphetype', include_py_files=False)

# Make sure we explicitly include important data folders
additional_datas = [
    ('amphetype/data/texts', 'amphetype/data/texts'),
    ('amphetype/data/css', 'amphetype/data/css'),
    ('amphetype/data/wordlists', 'amphetype/data/wordlists'),
    ('amphetype/VERSION', 'amphetype'),
    ('amphetype/data/about.html', 'amphetype/data')
]

# Add the additional data files to our collection
for src, dst in additional_datas:
    if Path(src).exists():
        datas.append((src, dst))

a = Analysis(
    ['bootstrap.py'],  # Use our bootstrap script as the entry point
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['PyQt5.QtPrintSupport', 'amphetype.main'],  # Include the main module
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Amphetype',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # This is equivalent to --windowed or -w
    windowed=True,  # Explicitly set windowed mode
    disable_windowed_traceback=False,
    argv_emulation=True,  # Important for macOS
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

app = BUNDLE(
    exe,
    name='Amphetype.app',
    icon='amphetype/data/amphetype_mac_icon.icns',  # If you have an icon file, specify its path here
    bundle_identifier='com.franksh.amphetype',
    info_plist={
        'CFBundleShortVersionString': VERSION,
        'CFBundleVersion': VERSION,
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': True,
        'CFBundleName': 'Amphetype',
        'CFBundleDisplayName': 'Amphetype',
        'CFBundleGetInfoString': 'Advanced typing practice program',
        'NSHumanReadableCopyright': '© Frank S. Hestvik',
    },
)
