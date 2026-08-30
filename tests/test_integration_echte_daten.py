"""Integrationstest gegen die echten Nutzerdaten.

Ausschliesslich lesend - data.json und progress.json werden nie geschrieben.
Wird übersprungen, wenn keine lokalen Daten vorhanden sind (z.B. auf einem
frischen Rechner oder in CI).
"""
import json
import random

import pytest

from lernapp.core.cards import parse_items
from lernapp.core.learning_engine import VORWAERTS, LearningSession, SessionZustand
from lernapp.core.progress import SetProgress
from lernapp.storage import paths
from lernapp.storage.migrations import migriere_data, migriere_progress

DATA = paths.data_file()
PROG = paths.prog_file()

pytestmark = pytest.mark.skipif(
    not DATA.exists(), reason="keine lokalen Nutzerdaten vorhanden"
)


def _lade(pfad, standard):
    if not pfad.exists():
        return standard
    return json.loads(pfad.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def echte_daten():
    return migriere_data(_lade(DATA, {"folders": {}}))


@pytest.fixture(scope="module")
def alle_lernsets(echte_daten):
    return [
        (fname, ls)
        for fname, fdata in echte_daten["folders"].items()
        for ls in fdata.get("lernsets", [])
    ]


# -- Parsing ------------------------------------------------------------------

def test_alle_karten_parsen_verlustfrei(alle_lernsets):
    """Jede Karte muss exakt in ihr Ursprungsformat zurückschreibbar sein."""
    abweichungen = []
    for _fname, ls in alle_lernsets:
        for original, karte in zip(ls["items"], parse_items(ls["items"])):
            if karte.legacy_item() != original:
                abweichungen.append((ls["name"], original, karte.legacy_item()))
    assert abweichungen == []


def test_jedes_triple_paket_ist_vollstaendig(alle_lernsets):
    """Jedes Paket braucht genau drei Karten mit revealed 0, 1 und 2.

    Vorher zerfielen can/could/been able und must/had to in je zwei Pakete.
    """
    unvollstaendig = []
    for _fname, ls in alle_lernsets:
        karten = parse_items(ls["items"])
        pakete: dict = {}
        for k in karten:
            if k.is_triple:
                pakete.setdefault(k.package_key, []).append(k)
        for key, gruppe in pakete.items():
            if sorted(c.revealed for c in gruppe) != [0, 1, 2]:
                unvollstaendig.append((ls["name"], key, [c.revealed for c in gruppe]))
    assert unvollstaendig == []


# -- Vollständiger Durchlauf --------------------------------------------------

def test_jedes_lernset_ist_vollstaendig_lernbar(alle_lernsets):
    """Kernaussage von Phase 1: kein Lernset enthält eine unlösbare Karte.

    Vorher blockierte '___ had to ___' das englische Verbenset dauerhaft.
    """
    blockiert = []
    for _fname, ls in alle_lernsets:
        s = LearningSession(
            parse_items(ls["items"]),
            fortschritt=SetProgress(),
            rng=random.Random(1),
            richtung=VORWAERTS,
        )
        schritte = 0
        grenze = len(ls["items"]) * 4 + 50
        while (f := s.naechste_frage()) is not None and schritte < grenze:
            schritte += 1
            # Bei Alternativantworten ("a, b") zählt genau eine Variante,
            # nicht die ganze Zeichenkette - so verhält sich auch die App.
            antwort = (list(f.card.erwartet) if f.ist_triple
                       else f.card.akzeptierte_antworten(False)[0])
            ergebnis = s.antworte(antwort)
            if not ergebnis.richtig:
                blockiert.append((ls["name"], f.card.key, "richtige Antwort abgelehnt"))
                break
        else:
            if s.zustand != SessionZustand.FERTIG:
                blockiert.append((ls["name"], None, f"Endzustand {s.zustand}"))
            done, tot = s.fortschritt_zaehler()
            if done != tot:
                blockiert.append((ls["name"], None, f"nur {done}/{tot} gelernt"))
    assert blockiert == []


def test_englisches_verbenset_erreicht_hundert_prozent(alle_lernsets):
    """Explizit das Set mit den 351 Triple-Teilkarten."""
    kandidaten = [ls for fn, ls in alle_lernsets
                  if sum(1 for i in ls["items"] if "___" in i["q"]) > 100]
    if not kandidaten:
        pytest.skip("kein grosses Triple-Set vorhanden")
    ls = kandidaten[0]
    s = LearningSession(parse_items(ls["items"]), rng=random.Random(2), richtung=VORWAERTS)

    vorher = s.fortschritt_zaehler()
    assert vorher[1] == 117, "117 Verbpakete statt 351 Einzelkarten"

    while (f := s.naechste_frage()) is not None:
        assert s.antworte(list(f.card.erwartet)).richtig
    assert s.fortschritt_zaehler() == (117, 117)
    assert s.zustand == SessionZustand.FERTIG


# -- Bestehender Fortschritt ---------------------------------------------------

def test_bestehender_fortschritt_wird_ohne_verlust_migriert():
    roh = _lade(PROG, {})
    if not roh:
        pytest.skip("kein Fortschritt vorhanden")
    neu = migriere_progress(roh)
    for set_id, alt in roh.items():
        if set_id == "schema_version" or not isinstance(alt, dict):
            continue
        assert neu[set_id]["xp"] == alt.get("xp", 0)
        assert neu[set_id]["correct"] == alt.get("correct", 0)
        assert neu[set_id]["wrong"] == alt.get("wrong", 0)
        assert neu[set_id]["streaks"] == alt.get("streaks", {})
        # Die Datei kann bereits migriert sein (dann steht der Rekord in
        # best_combo) oder noch im Altformat (dann in combo).
        erwarteter_rekord = alt.get("best_combo", alt.get("combo", 0))
        assert neu[set_id]["best_combo"] == erwarteter_rekord, "Rekord bleibt erhalten"
        assert neu[set_id]["combo"] == 0, "laufende Combo startet nie geerbt"


def test_migration_der_echten_daten_ist_idempotent():
    roh = _lade(PROG, {})
    if not roh:
        pytest.skip("kein Fortschritt vorhanden")
    assert migriere_progress(roh) == migriere_progress(migriere_progress(roh))


def test_gespeicherter_fortschritt_laedt_in_die_session(alle_lernsets):
    roh = migriere_progress(_lade(PROG, {}))
    if not roh:
        pytest.skip("kein Fortschritt vorhanden")
    for _fname, ls in alle_lernsets:
        eintrag = roh.get(ls["id"])
        if not isinstance(eintrag, dict):
            continue
        s = LearningSession(
            parse_items(ls["items"]),
            fortschritt=SetProgress.from_legacy(eintrag),
            rng=random.Random(3),
        )
        done, tot = s.fortschritt_zaehler()
        assert 0 <= done <= tot
        assert s.fortschritt.current_combo == 0, "Multiplikator startet nie geerbt"
