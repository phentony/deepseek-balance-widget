# build.py
import subprocess
import sys
from pathlib import Path

spec_content = """# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['PySide6.QtNetwork'],
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
    a.binaries,
    a.datas,
    [],
    name='DeepSeek-Balance-Widget',
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
    icon=None,
)
"""

def build():
    root = Path(__file__).parent
    spec_path = root / "DeepSeekBalance.spec"
    spec_path.write_text(spec_content)

    subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(spec_path), "--distpath", str(root / "dist")],
        cwd=str(root),
        check=True,
    )
    print(f"Build complete: {root / 'dist' / 'DeepSeek-Balance-Widget.exe'}")

if __name__ == "__main__":
    build()
