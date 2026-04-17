# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for MazeWorld -- macOS .app bundle.

Entry point: launcher.py (forces offline_static mode).
One-folder mode. Excludes heavy generation-only packages to keep the
bundle lean (~445MB vs ~2GB+ with torch/transformers).
"""

block_cipher = None


a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("data", "data"),
        ("assets", "assets"),
    ],
    hiddenimports=[
        "pygame",
        "pydantic",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Local LLM / image generation
        "torch",
        "torchvision",
        "transformers",
        "diffusers",
        "accelerate",
        "sentencepiece",
        # API backends
        "anthropic",
        "fal_client",
        "google.genai",
        "elevenlabs",
        # Generation-only utilities
        "weasyprint",
        "markdown",
        "tqdm",
        # Dev tooling
        "pytest",
        "ruff",
        "pre_commit",
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
    name="MazeWorld",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.icns",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MazeWorld",
)

app = BUNDLE(
    coll,
    name="MazeWorld.app",
    icon="assets/icon.icns",
    bundle_identifier="com.wolfgangblack.mazeworld",
    info_plist={
        "CFBundleName": "MazeWorld",
        "CFBundleDisplayName": "MazeWorld",
        "CFBundleIdentifier": "com.wolfgangblack.mazeworld",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "0.1.0",
        "NSHighResolutionCapable": True,
    },
)
