# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['pat.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('/home/qi-1940/.unioncode/miniforge/envs/pat_env/lib/python3.11/site-packages/doclayout_yolo/cfg/default.yaml', 'doclayout_yolo/cfg'),  # 打包依赖包的配置文件
        ('resources/*', 'resources'),
    ],
    hiddenimports=[],
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
    name='mini-GUI',
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
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='mini-GUI',
)
