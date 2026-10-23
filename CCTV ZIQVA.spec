# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[('E:\\ANTI GRAVITY\\MULTI CCTV\\build\\installer-assets\\bin\\ffmpeg.exe', 'bin')],
    datas=[('templates', 'templates'), ('static', 'static'), ('cctv_icon.ico', '.'), ('E:\\ANTI GRAVITY\\MULTI CCTV\\build\\installer-assets\\defaults', 'defaults'), ('E:\\ANTI GRAVITY\\MULTI CCTV\\build\\installer-assets\\browsers', 'browsers')],
    hiddenimports=['discover_streams'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CCTV ZIQVA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['cctv_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CCTV ZIQVA',
)
