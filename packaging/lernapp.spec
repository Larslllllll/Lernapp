# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller-Beschreibung fuer LernApp (Windows).

Bewusst KEIN nachtraegliches Loeschen von DLLs: die nicht benoetigten
Qt-Module sind gar nicht erst installiert, weil requirements.txt
PySide6-Essentials statt PySide6 verlangt. Was hier ausgeschlossen wird,
sind nur Python-Pakete, die PyInstaller sonst spekulativ mitnimmt.

Bauen:  python packaging/build_windows.py
"""
from pathlib import Path

WURZEL = Path(SPECPATH).parent
QML = WURZEL / "lernapp" / "gui" / "qml"
ICON = WURZEL / "ico.ico"

# Alle QML-Dateien inklusive qmldir des Theme-Singletons.
qml_datas = [
    (str(pfad), str(Path("qml") / pfad.relative_to(QML).parent))
    for pfad in QML.rglob("*")
    if pfad.is_file()
]

a = Analysis(
    [str(WURZEL / "LernApp.py")],
    pathex=[str(WURZEL)],
    binaries=[],
    datas=qml_datas + [(str(ICON), ".")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Die alte Oberflaeche gehoert nicht ins Bundle.
        "customtkinter",
        "tkinter",
        "lernapp.gui_ctk",
        # Von PyInstaller gern spekulativ eingesammelt.
        "pytest",
        "unittest",
        "pydoc",
        "numpy",
        "PIL",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LernApp",
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
    icon=str(ICON),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="LernApp",
)
