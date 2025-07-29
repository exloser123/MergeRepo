# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main_window.py'],
    pathex=[],
    binaries=[],
    datas=[('settings.json', '.'), ('icon_cache', 'icon_cache'), ('ui', 'ui'),('img', 'img'),('RepoIndex.txt', '.')],
    hiddenimports=['ui', 'json', 'requests', 'PIL', 'PIL.Image'],
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
    name='main_window',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    onefile=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# 取消注释下面的COLLECT部分
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main_window',
)