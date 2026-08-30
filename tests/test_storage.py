"""Tests für Speicherung und Migrationen.

Alle Tests arbeiten in tmp_path - die echten Nutzerdaten werden nie angefasst.
"""
import json

import pytest

from lernapp.core.progress import SCHEMA_VERSION, SetProgress
from lernapp.storage import local_storage as store
from lernapp.storage.migrations import (
    DATA_SCHEMA_VERSION,
    migriere_data,
    migriere_progress,
)

ALTE_DATA = {
    "folders": {
        "Franzoesisch": {
            "lernsets": [
                {"id": "abc", "name": "Unite 4", "items": [{"q": "la maison", "a": "das haus"}]}
            ]
        }
    }
}

ALTER_PROGRESS = {
    "abc": {
        "xp": 460, "correct": 23, "wrong": 7,
        "errors": {"la maison": 2}, "combo": 12,
        "streaks": {"la maison": 1},
    }
}


@pytest.fixture(autouse=True)
def _kein_backup_zustand():
    """Backup-Merker zwischen Tests zurücksetzen."""
    store._backup_gemacht.clear()
    yield
    store._backup_gemacht.clear()


# -- Speichern / Laden --------------------------------------------------------

def test_speichern_und_laden_erhaelt_die_lernsets(tmp_path):
    ziel = tmp_path / "data.json"
    store.save_data(ALTE_DATA, ziel)
    zurueck = store.load_data(ziel)
    assert zurueck["folders"]["Franzoesisch"]["lernsets"][0]["items"] == [
        {"q": "la maison", "a": "das haus"}
    ]


def test_fehlende_datei_legt_startdaten_an(tmp_path):
    ziel = tmp_path / "data.json"
    daten = store.load_data(ziel)
    assert ziel.exists()
    assert daten["folders"]["Verben"]["lernsets"][0]["items"], "Startset ist nicht leer"


def test_schreiben_ist_atomar_keine_temp_reste(tmp_path):
    ziel = tmp_path / "data.json"
    store.save_data(ALTE_DATA, ziel)
    store.save_data(ALTE_DATA, ziel)
    uebrig = [p.name for p in tmp_path.iterdir() if p.suffix == ".tmp"]
    assert uebrig == [], f"Temp-Dateien liegen geblieben: {uebrig}"


def test_backup_wird_vor_dem_ersten_ueberschreiben_angelegt(tmp_path):
    ziel = tmp_path / "data.json"
    store.save_data(ALTE_DATA, ziel)
    store._backup_gemacht.clear()          # neue Sitzung simulieren
    store.save_data({"folders": {}}, ziel)
    backups = list((tmp_path / "backups").glob("data-*.json"))
    assert len(backups) == 1
    gesichert = json.loads(backups[0].read_text(encoding="utf-8"))
    assert gesichert["folders"]["Franzoesisch"], "Backup enthaelt den alten Stand"


def test_beschaedigte_datei_wird_nicht_ueberschrieben(tmp_path):
    ziel = tmp_path / "data.json"
    ziel.write_text("{das ist kein json", encoding="utf-8")
    store.load_data(ziel)
    beiseite = list(tmp_path.glob("data.beschaedigt-*.json"))
    assert len(beiseite) == 1, "kaputte Datei muss gesichert werden"
    assert beiseite[0].read_text(encoding="utf-8") == "{das ist kein json"


def test_umlaute_ueberleben_den_roundtrip(tmp_path):
    ziel = tmp_path / "data.json"
    daten = {"folders": {"Französisch": {"lernsets": [
        {"id": "x", "name": "Unregelmäßige Verben",
         "items": [{"q": "être", "a": "sein"}]}]}}}
    store.save_data(daten, ziel)
    zurueck = store.load_data(ziel)
    assert "Französisch" in zurueck["folders"]
    ls = zurueck["folders"]["Französisch"]["lernsets"][0]
    assert ls["name"] == "Unregelmäßige Verben"
    assert ls["items"][0]["q"] == "être"


def test_fortschritt_roundtrip(tmp_path):
    ziel = tmp_path / "progress.json"
    store.save_prog(migriere_progress(ALTER_PROGRESS), ziel)
    zurueck = store.load_prog(ziel)
    assert zurueck["abc"]["xp"] == 460


# -- Migration data.json ------------------------------------------------------

def test_data_migration_setzt_schema_version():
    assert migriere_data(ALTE_DATA)["schema_version"] == DATA_SCHEMA_VERSION


def test_data_migration_ist_idempotent():
    einmal = migriere_data(ALTE_DATA)
    zweimal = migriere_data(einmal)
    assert einmal == zweimal


def test_data_migration_traegt_fehlende_id_nach():
    kaputt = {"folders": {"F": {"lernsets": [{"name": "Ohne ID", "items": []}]}}}
    ls = migriere_data(kaputt)["folders"]["F"]["lernsets"][0]
    assert ls["id"], "ohne ID gibt es keinen Fortschritt"


def test_data_migration_loescht_keine_unbekannten_felder():
    mit_extra = {"folders": {"F": {"lernsets": [
        {"id": "a", "name": "N", "items": [], "eigenes_feld": "behalten"}]}}}
    ls = migriere_data(mit_extra)["folders"]["F"]["lernsets"][0]
    assert ls["eigenes_feld"] == "behalten"


def test_data_migration_erhaelt_alle_karten():
    ergebnis = migriere_data(ALTE_DATA)
    assert ergebnis["folders"]["Franzoesisch"]["lernsets"][0]["items"] == [
        {"q": "la maison", "a": "das haus"}
    ]


# -- Migration progress.json --------------------------------------------------

def test_progress_migration_ergaenzt_neue_felder():
    neu = migriere_progress(ALTER_PROGRESS)
    assert neu["schema_version"] == SCHEMA_VERSION
    assert neu["abc"]["best_combo"] == 12
    assert neu["abc"]["total_errors"] == {"la maison": 2}


def test_progress_migration_verliert_keine_xp():
    neu = migriere_progress(ALTER_PROGRESS)
    assert neu["abc"]["xp"] == 460
    assert neu["abc"]["correct"] == 23
    assert neu["abc"]["wrong"] == 7
    assert neu["abc"]["streaks"] == {"la maison": 1}


def test_progress_migration_ist_idempotent():
    einmal = migriere_progress(ALTER_PROGRESS)
    zweimal = migriere_progress(einmal)
    assert einmal == zweimal


def test_progress_migration_bricht_laufende_combo_ab():
    """Gespeicherte combo=12 darf nach Neustart nicht wieder x3 geben."""
    neu = migriere_progress(ALTER_PROGRESS)
    assert neu["abc"]["combo"] == 0
    assert neu["abc"]["best_combo"] == 12


def test_progress_migration_vertraegt_leere_datei():
    assert migriere_progress({}) == {}


def test_progress_migration_bleibt_lesbar_fuer_alte_version():
    """Additive Migration: die alten Schlüssel müssen erhalten bleiben."""
    neu = migriere_progress(ALTER_PROGRESS)["abc"]
    for schluessel in ("xp", "correct", "wrong", "errors", "combo", "streaks"):
        assert schluessel in neu


# -- Zusammenspiel ------------------------------------------------------------

def test_migrierter_fortschritt_laedt_in_setprogress():
    neu = migriere_progress(ALTER_PROGRESS)
    p = SetProgress.from_legacy(neu["abc"])
    assert p.xp == 460
    assert p.best_combo == 12
    assert p.current_combo == 0
