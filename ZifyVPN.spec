# -*- mode: python ; coding: utf-8 -*-
import os

ROOT = SPECPATH

a = Analysis(
    [os.path.join(ROOT, "vpn_configurator", "main.py")],
    pathex=[ROOT],
    binaries=[
        (os.path.join(ROOT, "vpn_configurator", "bin", "xray.exe"), "bin"),
        (os.path.join(ROOT, "vpn_configurator", "bin", "wintun.dll"), "bin"),
        (os.path.join(ROOT, "vpn_configurator", "bin", "geoip.dat"), "bin"),
        (os.path.join(ROOT, "vpn_configurator", "bin", "geosite.dat"), "bin"),
    ],
    datas=[],
    hiddenimports=[
        "vpn_configurator.core.xray_stats_pb2",
        "vpn_configurator.core.xray_stats_pb2_grpc",
        "grpc._cython.cygrpc",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt5", "tkinter", "matplotlib"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ZifyClient",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version="file_version_info.txt",
    manifest=None,
)
