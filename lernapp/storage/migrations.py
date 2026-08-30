"""Schema-Migrationen.

Regeln:
  * idempotent    - zweimal laufen ändert nichts
  * deterministisch bis auf neu vergebene UUIDs für fehlende IDs
  * nie löschend - unbekannte Felder bleiben unangetastet erhalten

Aktueller Stand: v1 (kein schema_version-Feld) -> v2.
"""
from __future__ import annotations

import uuid

from ..core.progress import SCHEMA_VERSION, SetProgress

DATA_SCHEMA_VERSION = 2


def migriere_data(roh: dict) -> dict:
    """Lernset-Datei auf den aktuellen Stand bringen."""
    daten = dict(roh)
    daten.setdefault("folders", {})

    for fdata in daten["folders"].values():
        if not isinstance(fdata, dict):
            continue
        for ls in fdata.get("lernsets", []):
            # Fehlende ID nachtragen - ohne stabile ID gibt es keinen Fortschritt.
            if not ls.get("id"):
                ls["id"] = str(uuid.uuid4())
            ls.setdefault("name", "Ohne Namen")
            ls.setdefault("items", [])

    daten["schema_version"] = DATA_SCHEMA_VERSION
    return daten


def migriere_progress(roh: dict) -> dict:
    """Fortschrittsdatei auf den aktuellen Stand bringen.

    Läuft jeden Eintrag durch SetProgress, wodurch best_combo und
    total_errors ergänzt werden, ohne bestehende Werte zu verlieren.
    """
    if not roh:
        return {}

    ergebnis: dict = {}
    for schluessel, wert in roh.items():
        if schluessel == "schema_version":
            continue
        if not isinstance(wert, dict):
            ergebnis[schluessel] = wert
            continue
        ergebnis[schluessel] = SetProgress.from_legacy(wert).to_legacy()

    ergebnis["schema_version"] = SCHEMA_VERSION
    return ergebnis
