"""Reproduzierbarer Windows-Build.

    .venv/Scripts/python.exe packaging/build_windows.py

Prueft zuerst die Voraussetzungen, baut dann ueber packaging/lernapp.spec und
meldet am Ende Groesse und Inhalt. Es wird nichts nachtraeglich geloescht -
nicht benoetigte Qt-Module sind gar nicht erst installiert.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
from lernapp import __version__  # noqa: E402

SPEC = WURZEL / "packaging" / "lernapp.spec"
ISS = WURZEL / "packaging" / "lernapp.iss"
DIST = WURZEL / "dist"
# Arbeitsordner UND fertiges Bundle liegen ausserhalb des Projekts. Das
# Projekt liegt in OneDrive, und der Sync-Dienst greift sich jede der 2000
# Dateien sofort - das bremst den Build und laesst ihn beim naechsten Lauf am
# Aufraeumen scheitern (WinError 5, obwohl nichts laeuft). Beides ist reiner
# Zwischenstand und gehoert nirgends hin, wo es gesichert wird.
#
# In dist/ landet nur die fertige Setup-Datei - eine einzelne Datei, die der
# Sync problemlos vertraegt, und genau die, die release.py hochlaedt.
WORK = Path(tempfile.gettempdir()) / "lernapp-pyinstaller"
BUNDLE = Path(tempfile.gettempdir()) / "lernapp-bundle"
ZIEL = BUNDLE / "LernApp"

# So oft wird ein gesperrter Ordner erneut angefasst, bevor aufgegeben wird.
# Das Projekt liegt in OneDrive, und der Sync haelt nach einem Build gern
# noch Sekunden lang einen Handle auf die 2000 frisch geschriebenen Dateien.
VERSUCHE = 6

# Diese Qt-Bibliotheken laedt die App zur Laufzeit. Fehlt eine davon im
# Bundle, ist der Build kaputt - unabhaengig davon, ob er durchlaeuft.
ERWARTETE_QT_MODULE = [
    "Qt6Core.dll", "Qt6Gui.dll", "Qt6Qml.dll", "Qt6Quick.dll",
    "Qt6QuickControls2.dll", "Qt6QuickTemplates2.dll", "Qt6QuickLayouts.dll",
    "Qt6QmlModels.dll", "Qt6Network.dll", "Qt6OpenGL.dll", "Qt6Svg.dll",
    "Qt6QuickDialogs2.dll", "Qt6QuickDialogs2QuickImpl.dll",
]

# Diese duerfen NIE auftauchen - sie stecken in PySide6-Addons.
VERBOTENE_QT_MODULE = [
    "Qt6WebEngineCore.dll", "Qt63DCore.dll", "Qt6Charts.dll",
    "Qt6DataVisualization.dll", "Qt6Multimedia.dll",
]


def fehler(text: str) -> None:
    print(f"FEHLER: {text}", file=sys.stderr)
    raise SystemExit(1)


def pruefe_umgebung() -> None:
    try:
        import PySide6  # noqa: F401
    except ImportError:
        fehler("PySide6 fehlt. requirements.txt installieren.")

    site = Path(sys.prefix) / "Lib" / "site-packages" / "PySide6"
    if (site / "Qt6WebEngineCore.dll").exists():
        fehler(
            "PySide6-Addons ist installiert - das Bundle wuerde 194 MB WebEngine "
            "mitschleppen.\n       pip uninstall PySide6 PySide6_Addons\n"
            "       pip install --force-reinstall --no-deps PySide6-Essentials"
        )
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        fehler("PyInstaller fehlt. requirements-dev.txt installieren.")


def _aufraeumen(ordner: Path) -> None:
    """Inhalt loeschen, den Ordner selbst stehen lassen.

    Auf einem OneDrive-Laufwerk haelt der Sync-Dienst gern einen Handle auf
    das Verzeichnis; ein rmtree auf den Ordner selbst scheitert dann mit
    WinError 5, obwohl der Inhalt loeschbar ist.
    """
    if not ordner.exists():
        return
    for eintrag in list(ordner.iterdir()):
        for versuch in range(VERSUCHE):
            try:
                if eintrag.is_dir():
                    shutil.rmtree(eintrag)
                else:
                    eintrag.unlink()
                break
            except PermissionError:
                if versuch == VERSUCHE - 1:
                    fehler(
                        f"{eintrag} laesst sich nicht loeschen.\n"
                        "       Laeuft die App noch? Sonst haelt der OneDrive-Sync\n"
                        "       den Ordner fest - kurz warten und erneut starten."
                    )
                # Wachsende Wartezeit: der Sync gibt den Ordner nach ein paar
                # Sekunden von selbst frei, ein starres Intervall trifft das
                # Fenster oft nicht.
                time.sleep(1.0 + versuch)


def bauen() -> float:
    _aufraeumen(ZIEL)
    _aufraeumen(WORK)
    start = time.perf_counter()
    ergebnis = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
         "--distpath", str(BUNDLE), "--workpath", str(WORK), str(SPEC)],
        cwd=str(WURZEL),
    )
    if ergebnis.returncode != 0:
        fehler(f"PyInstaller endete mit Code {ergebnis.returncode}")
    return time.perf_counter() - start


def groesse_mb(pfad: Path) -> float:
    return sum(f.stat().st_size for f in pfad.rglob("*") if f.is_file()) / 1024 / 1024


def pruefe_ergebnis() -> None:
    exe = ZIEL / "LernApp.exe"
    if not exe.exists():
        fehler("LernApp.exe wurde nicht erzeugt")

    vorhandene = {f.name for f in ZIEL.rglob("*.dll")}
    fehlend = [m for m in ERWARTETE_QT_MODULE if m not in vorhandene]
    if fehlend:
        fehler(f"Qt-Module fehlen im Bundle: {', '.join(fehlend)}")

    verboten = [m for m in VERBOTENE_QT_MODULE if m in vorhandene]
    if verboten:
        fehler(f"Nicht benoetigte Qt-Module im Bundle: {', '.join(verboten)}")

    qml = ZIEL / "_internal" / "qml"
    if not (qml / "Main.qml").exists():
        fehler("Main.qml fehlt im Bundle")
    if not (qml / "theme" / "qmldir").exists():
        fehler("theme/qmldir fehlt - der Theme-Singleton wuerde nicht laden")


def _iscc() -> Path | None:
    """Inno-Setup-Compiler suchen."""
    aus_pfad = shutil.which("ISCC")
    if aus_pfad:
        return Path(aus_pfad)
    for basis in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles")):
        if not basis:
            continue
        for version in ("6", "5"):
            kandidat = Path(basis) / f"Inno Setup {version}" / "ISCC.exe"
            if kandidat.exists():
                return kandidat
    return None


def installer_bauen() -> Path:
    iscc = _iscc()
    if iscc is None:
        fehler("Inno Setup nicht gefunden. winget install JRSoftware.InnoSetup")
    ergebnis = subprocess.run(
        [str(iscc), f"/DAppVersion={__version__}",
         f"/DQuellVerzeichnis={ZIEL}", str(ISS)],
        cwd=str(WURZEL / "packaging"),
    )
    if ergebnis.returncode != 0:
        fehler(f"Inno Setup endete mit Code {ergebnis.returncode}")
    setup = DIST / f"LernApp-Setup-{__version__}.exe"
    if not setup.exists():
        fehler(f"{setup.name} wurde nicht erzeugt")
    return setup


def main() -> int:
    argumente = argparse.ArgumentParser(description="Windows-Build fuer LernApp")
    argumente.add_argument("--installer", action="store_true",
                           help="zusaetzlich den Inno-Setup-Installer bauen")
    optionen = argumente.parse_args()

    print(f"LernApp {__version__}")
    print("Voraussetzungen pruefen ...")
    pruefe_umgebung()
    print("Bauen ...")
    dauer = bauen()
    print("Ergebnis pruefen ...")
    pruefe_ergebnis()

    gesamt = groesse_mb(ZIEL)
    qt = sum(f.stat().st_size for f in ZIEL.rglob("Qt6*.dll")) / 1024 / 1024
    print()
    print(f"  Build          {dauer:.0f} s")
    print(f"  Bundle         {gesamt:.0f} MB   (davon Qt-DLLs {qt:.0f} MB)")
    print(f"  Ausgabe        {ZIEL}")

    if optionen.installer:
        print()
        print("Installer bauen ...")
        setup = installer_bauen()
        print()
        print(f"  Installer      {setup.stat().st_size / 1024 / 1024:.0f} MB")
        print(f"  Ausgabe        {setup}")
    print()
    print("  Der Build gilt erst als getestet, wenn die .exe gestartet und eine")
    print("  echte Lernrunde inklusive Neustart durchgespielt wurde.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
