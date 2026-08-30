"""Packaging und Release-Weg passen zueinander.

Diese Tests laufen ohne Netz. Sie pruefen nicht, ob eine Installation
funktioniert - das geht nur auf einer echten Windows-Maschine -, sondern ob
die Stellen zusammenpassen, die auseinanderlaufen koennen: die
PyInstaller-Spec, das Inno-Skript, install.ps1 und release.py.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

INSTALL_PS1 = WURZEL / "install.ps1"
ISS = WURZEL / "packaging" / "lernapp.iss"
RELEASE = WURZEL / "packaging" / "release.py"
SPEC = WURZEL / "packaging" / "lernapp.spec"

PS1 = INSTALL_PS1.read_text(encoding="utf-8")
ISS_TEXT = ISS.read_text(encoding="utf-8")
SPEC_TEXT = SPEC.read_text(encoding="utf-8")


def test_bundle_ist_onedir_nicht_onefile():
    """Ein Ordner, keine selbstentpackende Einzeldatei.

    --onefile entpackt bei jedem Start 2000 Dateien nach %TEMP%: langsamer
    Start, und Virenscanner mustern jedes Mal frisch. Der Unterschied steht
    nicht als Flag in der Spec, sondern in zwei Details: EXE bekommt die
    Binaries NICHT mit (exclude_binaries=True), und ein COLLECT sammelt sie
    danach in einen Ordner. Faellt eines davon weg, ist es --onefile.
    """
    assert "exclude_binaries=True" in SPEC_TEXT
    assert "coll = COLLECT(" in SPEC_TEXT
    assert "a.binaries," in SPEC_TEXT.split("coll = COLLECT(")[1]


def test_bundle_hat_kein_konsolenfenster():
    """console=False ist --noconsole.

    Sonst steht hinter der App ein schwarzes Fenster, das der Nutzer nicht
    schliessen darf, weil damit die App stirbt.
    """
    assert "console=False" in SPEC_TEXT
    assert "console=True" not in SPEC_TEXT


def test_installer_verteilt_das_bundle_als_ordner():
    """Das Inno-Skript packt genau den COLLECT-Ordner ein."""
    assert "recursesubdirs createallsubdirs" in ISS_TEXT
    assert r'QuellVerzeichnis "..\dist\LernApp"' in ISS_TEXT


def test_installskript_ist_reines_ascii():
    """Windows PowerShell 5.1 dekodiert UTF-8 ohne BOM falsch.

    Ein Umlaut in dieser Datei wird beim lokalen Aufruf zu Kauderwelsch.
    Deshalb ist sie durchgehend mit ae/oe/ue geschrieben.
    """
    unerlaubt = {
        nummer: zeile
        for nummer, zeile in enumerate(PS1.splitlines(), start=1)
        if not zeile.isascii()
    }
    assert not unerlaubt, f"Nicht-ASCII-Zeichen in install.ps1: {unerlaubt}"


def test_appid_stimmt_mit_inno_skript_ueberein():
    """Weichen die GUIDs ab, findet install.ps1 eine Installation nicht."""
    aus_iss = re.search(r"AppId=\{\{([0-9A-Fa-f-]{36})\}", ISS_TEXT)
    aus_ps1 = re.search(r"\$AppId\s*=\s*'\{([0-9A-Fa-f-]{36})\}'", PS1)
    assert aus_iss and aus_ps1
    assert aus_iss.group(1) == aus_ps1.group(1)


def _release_modul():
    """release.py per Pfad laden.

    Nicht ueber `import packaging.release`: der Ordnername kollidiert mit der
    gleichnamigen Bibliothek aus dem venv, und ein __init__.py wollen wir
    dort nicht.
    """
    spec = importlib.util.spec_from_file_location("lernapp_release", RELEASE)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def test_manifestfelder_stimmen_mit_release_skript_ueberein(tmp_path):
    """install.ps1 verlangt genau die Felder, die release.py schreibt."""
    release = _release_modul()
    release.MANIFEST = tmp_path / "latest.json"
    daten = release.manifest_schreiben("a" * 64, 123)

    assert json.loads(release.MANIFEST.read_text(encoding="utf-8")) == daten

    verlangt = set(re.search(r"foreach \(\$feld in ([^)]+)\)", PS1).group(1)
                   .replace("'", "").replace(" ", "").split(","))
    fehlend = verlangt - set(daten)
    assert not fehlend, f"install.ps1 verlangt Felder, die release.py nicht schreibt: {fehlend}"


def test_manifest_url_zeigt_auf_das_release_der_eigenen_version(tmp_path):
    release = _release_modul()
    release.MANIFEST = tmp_path / "latest.json"
    daten = release.manifest_schreiben("b" * 64, 1)
    assert daten["url"].startswith("https://github.com/")
    assert daten["url"].endswith(f"LernApp-Setup-{daten['version']}.exe")
    assert f"/v{daten['version']}/" in daten["url"]


def test_setupname_folgt_dem_inno_muster():
    """release.py sucht die Datei, die Inno tatsaechlich erzeugt."""
    muster = re.search(r"OutputBaseFilename=(\S+)", ISS_TEXT).group(1)
    assert muster == "LernApp-Setup-{#AppVersion}"
    quelltext = RELEASE.read_text(encoding="utf-8")
    assert 'f"LernApp-Setup-{__version__}.exe"' in quelltext


def test_installskript_prueft_die_pruefsumme_vor_dem_ausfuehren():
    """Die Reihenfolge ist die Sicherheitseigenschaft, nicht die Zeile."""
    pruefen = PS1.index("Pruefe-Pruefsumme $setup")
    starten = PS1.index("Start-Process -FilePath $setup")
    assert pruefen < starten, "Das Setup wird gestartet, bevor die Summe stimmt"
    assert "Remove-Item $Datei -Force" in PS1, "Eine falsche Datei muss weg"


def test_installskript_liegt_an_der_stelle_die_es_selbst_nennt():
    """Die kurze URL zeigt auf die Wurzel - dort muss die Datei auch liegen.

    Sonst laedt der Einzeiler eine Datei, die es nicht gibt, oder eine
    veraltete Kopie.
    """
    treffer = re.search(r"raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(\S+?)\)", PS1)
    assert treffer, "Keine Roh-URL in install.ps1 gefunden"
    besitzer, repo, zweig, pfad = treffer.groups()
    assert pfad == "install.ps1", f"URL zeigt auf '{pfad}', Datei liegt in der Wurzel"

    release = _release_modul()
    assert (besitzer, repo, zweig) == (release.BESITZER, release.REPO, release.ZWEIG)


def test_manifest_liegt_im_repo_nicht_im_build():
    """latest.json gehoert unter Versionskontrolle, nicht nach dist/."""
    release = _release_modul()
    assert release.MANIFEST.parent == release.WURZEL
    assert release.MANIFEST.name == "latest.json"


def test_installskript_verlangt_https():
    assert "-notmatch '^https://'" in PS1


@pytest.mark.skipif(shutil.which("powershell") is None,
                    reason="PowerShell nicht verfuegbar")
def test_installskript_ist_syntaktisch_gueltig():
    """Ein Tippfehler faellt sonst erst beim Klassenkameraden auf."""
    befehl = (
        "$f=$null; $e=$null; "
        f"[System.Management.Automation.Language.Parser]::ParseFile("
        f"'{INSTALL_PS1}', [ref]$f, [ref]$e) | Out-Null; "
        "if ($e.Count) { $e | ForEach-Object { $_.ToString() }; exit 1 }"
    )
    ergebnis = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", befehl],
        capture_output=True, text=True,
    )
    assert ergebnis.returncode == 0, ergebnis.stdout + ergebnis.stderr
