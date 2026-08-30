"""Speicherorte.

Phase 1 ändert bewusst NICHTS am Ablageort: die Daten bleiben in
``~/.lernapp``, damit bestehende Nutzerdaten unverändert weiterverwendet
werden. Die plattformspezifischen Zielpfade (%LOCALAPPDATA% bzw.
~/Library/Application Support) sind hier bereits benannt, werden aber erst in
Phase 2 aktiviert - eine Verschiebung ist eine Migration mit echtem Risiko und
gehört nicht in einen reinen Core-Refactor.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "LernApp"

# Historischer Ablageort - aktuell der einzige aktive.
LEGACY_DIR = Path.home() / ".lernapp"


def plattform_datenverzeichnis() -> Path:
    """Der plattformübliche Ort. Noch nicht aktiv - siehe Modul-Docstring."""
    if sys.platform == "win32":
        basis = os.environ.get("LOCALAPPDATA")
        return Path(basis) / APP_NAME if basis else LEGACY_DIR
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_NAME


def datenverzeichnis() -> Path:
    """Aktiv genutztes Verzeichnis.

    LERNAPP_DATA_DIR lenkt den Ablageort um - gedacht für Entwicklung und
    Tests, damit nie versehentlich gegen die echten Nutzerdaten gearbeitet
    wird. Ohne die Variable bleibt alles beim historischen Ort.
    """
    override = os.environ.get("LERNAPP_DATA_DIR")
    if override:
        return Path(override)
    return LEGACY_DIR


def data_file(basis: Path | None = None) -> Path:
    return (basis or datenverzeichnis()) / "data.json"


def prog_file(basis: Path | None = None) -> Path:
    return (basis or datenverzeichnis()) / "progress.json"


def backup_dir(basis: Path | None = None) -> Path:
    return (basis or datenverzeichnis()) / "backups"
