"""Benutzereinstellungen (settings.json).

Bewusst klein gehalten: nur was die Oberflaeche wirklich merken muss.
Unbekannte Schluessel bleiben beim Speichern erhalten, damit eine aeltere
Programmversion nichts verliert.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import paths
from .local_storage import _lade_json, _schreibe_json_atomar

SCHEMA_VERSION = 1

STANDARD: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "theme": "dark",          # "dark" | "light"
    "richtung": "⇄",          # VORWAERTS | RUECKWAERTS | GEMISCHT
    "sound": True,
    "fenster": {"breite": 1180, "hoehe": 760},
}


def settings_file(basis: Path | None = None) -> Path:
    return (basis or paths.datenverzeichnis()) / "settings.json"


def load_settings(pfad: Path | None = None) -> dict:
    p = pfad or settings_file()
    roh = _lade_json(p, {})
    if not isinstance(roh, dict):
        roh = {}
    zusammen = {**STANDARD, **roh}
    zusammen["schema_version"] = SCHEMA_VERSION
    # Verschachtelte Vorgabe ergaenzen, ohne Vorhandenes zu ueberschreiben.
    fenster = {**STANDARD["fenster"], **(roh.get("fenster") or {})}
    zusammen["fenster"] = fenster
    return zusammen


def save_settings(werte: dict, pfad: Path | None = None) -> None:
    p = pfad or settings_file()
    _schreibe_json_atomar(p, werte)
