"""Ein Release veröffentlichen.

    .venv/Scripts/python.exe packaging/release.py                  # nur vorbereiten
    .venv/Scripts/python.exe packaging/release.py --veröffentlichen

Ohne Flag geht nichts nach aussen: das Skript prüft die gebaute Setup-Datei,
bildet die SHA-256-Summe, schreibt latest.json und meldet, was passieren
würde. Erst --veröffentlichen committet latest.json, schiebt den Zweig hoch
und legt das GitHub-Release mit der Setup-Datei an.

Reihenfolge ist Absicht: das Release mit der Datei entsteht ZUERST, latest.json
wird ZULETZT hochgeschoben. latest.json ist der Schalter, der eine Version für
alle scharf stellt - er darf nie auf eine Datei zeigen, die es noch nicht gibt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
from lernapp import __version__  # noqa: E402

BESITZER = "Larslllllll"
REPO = "Lernapp"
VOLLNAME = f"{BESITZER}/{REPO}"
ZWEIG = "main"

DIST = WURZEL / "dist"
# latest.json liegt im Repo, nicht in dist/: install.ps1 liest es über
# raw.githubusercontent, und so ist es genau eine Datei unter Versionskontrolle
# statt einer Kopie, die auseinanderlaufen kann.
MANIFEST = WURZEL / "latest.json"


def fehler(text: str) -> None:
    print(f"FEHLER: {text}", file=sys.stderr)
    raise SystemExit(1)


def lauf(*argumente: str, pruefen: bool = True) -> subprocess.CompletedProcess:
    ergebnis = subprocess.run(
        argumente, capture_output=True, text=True, encoding="utf-8", cwd=str(WURZEL)
    )
    if pruefen and ergebnis.returncode != 0:
        fehler(f"{' '.join(argumente)}\n{ergebnis.stderr.strip()}")
    return ergebnis


def gh(*argumente: str) -> str:
    if shutil.which("gh") is None:
        fehler("Die GitHub-CLI 'gh' fehlt. winget install GitHub.cli")
    return lauf("gh", *argumente).stdout


def setup_datei() -> Path:
    pfad = DIST / f"LernApp-Setup-{__version__}.exe"
    if not pfad.exists():
        fehler(
            f"{pfad.name} fehlt.\n"
            "       .venv/Scripts/python.exe packaging/build_windows.py --installer"
        )
    return pfad


def sha256(pfad: Path) -> str:
    summe = hashlib.sha256()
    with pfad.open("rb") as datei:
        for block in iter(lambda: datei.read(1024 * 1024), b""):
            summe.update(block)
    return summe.hexdigest()


def manifest_schreiben(pruefsumme: str, groesse: int) -> dict:
    """Das Manifest, das install.ps1 liest.

    Die Feldnamen sind öffentliche Schnittstelle: eine ältere install.ps1,
    die noch bei jemandem im Verlauf steht, muss sie weiter finden. Neue
    Felder dürfen dazukommen, vorhandene nicht verschwinden.
    """
    daten = {
        "version": __version__,
        "url": (
            f"https://github.com/{VOLLNAME}/releases/download/"
            f"v{__version__}/LernApp-Setup-{__version__}.exe"
        ),
        "sha256": pruefsumme,
        "groesse": groesse,
        "datum": date.today().isoformat(),
    }
    MANIFEST.write_text(json.dumps(daten, indent=2) + "\n", encoding="utf-8")
    return daten


def pruefe_zweig() -> None:
    zweig = lauf("git", "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if zweig != ZWEIG:
        fehler(f"Auf Zweig '{zweig}' statt '{ZWEIG}'. install.ps1 liest von '{ZWEIG}'.")


def release_anlegen(setup: Path) -> None:
    marke = f"v{__version__}"
    vorhanden = lauf("gh", "release", "view", marke, "--repo", VOLLNAME, pruefen=False)
    if vorhanden.returncode == 0:
        gh("release", "upload", marke, str(setup), "--repo", VOLLNAME, "--clobber")
        print(f"  Release        {marke} (Datei ersetzt)")
        return
    notizen = (
        f"LernApp {__version__} für Windows 11.\n\n"
        "Installation ohne Herunterladen und Doppelklick:\n\n"
        "```powershell\n"
        f"iex (irm https://raw.githubusercontent.com/{VOLLNAME}/{ZWEIG}/install.ps1)\n"
        "```\n"
    )
    gh("release", "create", marke, str(setup), "--repo", VOLLNAME,
       "--title", f"LernApp {__version__}", "--notes", notizen)
    print(f"  Release        {marke} (neu)")


def manifest_hochschieben() -> None:
    geaendert = lauf("git", "status", "--porcelain", "--", str(MANIFEST)).stdout.strip()
    if geaendert:
        lauf("git", "add", "--", str(MANIFEST))
        lauf("git", "commit", "-m", f"release: LernApp {__version__}", "--", str(MANIFEST))
        print("  latest.json    committet")
    else:
        print("  latest.json    unveraendert")
    lauf("git", "push", "origin", ZWEIG)
    print(f"  Push           origin/{ZWEIG}")


def main() -> int:
    argumente = argparse.ArgumentParser(description="LernApp-Release veroeffentlichen")
    argumente.add_argument("--veroeffentlichen", action="store_true",
                           help="Release anlegen, Datei hochladen, latest.json schieben")
    optionen = argumente.parse_args()

    setup = setup_datei()
    pruefsumme = sha256(setup)
    manifest_schreiben(pruefsumme, setup.stat().st_size)

    print(f"LernApp {__version__}")
    print()
    print(f"  Setup          {setup}")
    print(f"  Groesse        {setup.stat().st_size / 1024 / 1024:.0f} MB")
    print(f"  SHA-256        {pruefsumme}")
    print(f"  Manifest       {MANIFEST}")
    print()

    if not optionen.veroeffentlichen:
        print("  Nichts veroeffentlicht (Probelauf).")
        print("  Mit --veroeffentlichen wuerde passieren:")
        print(f"    - Release v{__version__} in {VOLLNAME} anlegen, {setup.name} hochladen")
        print(f"    - latest.json committen und nach origin/{ZWEIG} schieben")
        print()
        print("  Danach lautet der Befehl fuer die Klasse:")
        print(f"    iex (irm https://raw.githubusercontent.com/{VOLLNAME}/{ZWEIG}/install.ps1)")
        print()
        return 0

    print("  Veroeffentlichen ...")
    pruefe_zweig()
    release_anlegen(setup)
    manifest_hochschieben()
    print()
    print("  Fertig. Befehl fuer die Klasse:")
    print(f"    iex (irm https://raw.githubusercontent.com/{VOLLNAME}/{ZWEIG}/install.ps1)")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
