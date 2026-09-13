# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Adventist Bible Study Tool (WP-029, ADR-024).

Zero-Python standalone distribution:
- Builds a standalone executable for the local engine + web server + TUI mode.
- Bundles static web assets (web/) and internal data fixtures (search/fixtures/).
- Sidecar databases (bible.db, macula.db, lexicons/) live adjacent to the binary in data/ (ADR-024).
"""

block_cipher = None

# Hidden imports needed for dynamic driver loading in Textual (including textual-web / remote mode)
hiddenimports = [
    "textual.drivers.linux_driver",
    "textual.drivers.windows_driver",
    "textual.drivers.headless_driver",
    "textual.drivers.web_driver",
    "textual.drivers._input_reader_linux",
    "textual.drivers._input_reader_windows",
    "sqlite3",
]

# Static web files and packaged data fixtures
datas = [
    ("web", "web"),
    ("search/fixtures", "search/fixtures"),
    ("data/prophetic_lexicon.json", "data"),
]

a = Analysis(
    ["search/ui/web.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "scipy",
        "pandas",
        "pytest",
    ],
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
    name="bible-study",
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="bible-study",
)
