"""Laden und Speichern der lokalen JSON-Dateien.

Zwei Eigenschaften, die die Vorgaengerversion nicht hatte:

  Atomares Schreiben
      Bisher wurde direkt in data.json geschrieben. Ein Absturz mitten im
      json.dump hinterlaesst eine halbe Datei - bei 164 KB Lernsets ein realer
      Datenverlust. Jetzt wird in eine Temp-Datei geschrieben und erst danach
      per os.replace umgehaengt.

  Backup vor dem ersten Schreiben je Sitzung
      Damit ein fehlerhaftes Update nicht die einzige Kopie zerstoert.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.seed_data import standard_data
from . import paths
from .migrations import migriere_data, migriere_progress

_backup_gemacht: set[Path] = set()


def _lade_json(pfad: Path, standard: Any) -> Any:
    if not pfad.exists():
        return standard
    try:
        with pfad.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # Beschaedigte Datei nicht ueberschreiben - beiseitelegen und melden.
        beschaedigt = pfad.with_suffix(f".beschaedigt-{datetime.now():%Y%m%d-%H%M%S}.json")
        try:
            shutil.copy2(pfad, beschaedigt)
        except OSError:
            pass
        return standard


def _schreibe_json_atomar(pfad: Path, inhalt: Any) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=str(pfad.parent), prefix=pfad.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(inhalt, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, pfad)
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise


def _backup_einmalig(pfad: Path) -> None:
    if pfad in _backup_gemacht or not pfad.exists():
        _backup_gemacht.add(pfad)
        return
    ziel_dir = paths.backup_dir(pfad.parent)
    ziel_dir.mkdir(parents=True, exist_ok=True)
    ziel = ziel_dir / f"{pfad.stem}-{datetime.now():%Y%m%d-%H%M%S}{pfad.suffix}"
    try:
        shutil.copy2(pfad, ziel)
        _alte_backups_aufraeumen(ziel_dir, pfad.stem, behalten=10)
    except OSError:
        pass
    _backup_gemacht.add(pfad)


def _alte_backups_aufraeumen(ordner: Path, praefix: str, behalten: int) -> None:
    dateien = sorted(ordner.glob(f"{praefix}-*.json"))
    for alt in dateien[:-behalten]:
        try:
            alt.unlink()
        except OSError:
            pass


# -- Lernsets -----------------------------------------------------------------

def load_data(pfad: Path | None = None) -> dict:
    p = pfad or paths.data_file()
    roh = _lade_json(p, None)
    if roh is None:
        daten = standard_data()
        save_data(daten, p)
        return daten
    return migriere_data(roh)


def save_data(daten: dict, pfad: Path | None = None) -> None:
    p = pfad or paths.data_file()
    _backup_einmalig(p)
    _schreibe_json_atomar(p, daten)


# -- Fortschritt --------------------------------------------------------------

def load_prog(pfad: Path | None = None) -> dict:
    p = pfad or paths.prog_file()
    return migriere_progress(_lade_json(p, {}))


def save_prog(fortschritt: dict, pfad: Path | None = None) -> None:
    p = pfad or paths.prog_file()
    _backup_einmalig(p)
    _schreibe_json_atomar(p, fortschritt)


# -- Lernsets bearbeiten ------------------------------------------------------

def neues_lernset(name: str, items: list[dict] | None = None) -> dict:
    return {"id": str(uuid.uuid4()), "name": name, "items": list(items or [])}
