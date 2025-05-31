# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['pat.py'],
    pathex=[],
    binaries=[
        (r'D:\Anaconda\envs\pat_env\Library\bin\poppler.dll', '.'),
        (r'D:\Anaconda\envs\pat_env\Library\bin\pdftocairo.exe', '.'),
        (r'D:\Anaconda\envs\pat_env\Library\bin\pdfinfo.exe', '.')
    ],
    datas=[
        (r'resources\*', 'resources'),  # 包含所有资源文件
        (r'D:\Anaconda\envs\pat_env\Lib\site-packages\doclayout_yolo\cfg\default.yaml', 'doclayout_yolo/cfg')  # 从环境中复制配置文件
    ],
    hiddenimports=[
        'utils',       # 工具函数
        'pdf2image',   # PDF 转图像模块
        'doclayout_yolo'  # YOLO模型
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hook-runtime.py'],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
    debug=False  # 禁用调试信息以避免控制台窗口
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # 这将创建一个目录而不是单个文件
    name='pat',
    debug=False,  # 禁用调试以避免控制台窗口
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/logo.ico',  # 添加图标
    version='version_info.txt'
)

# 创建包含所有依赖的目录
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pat'
)
