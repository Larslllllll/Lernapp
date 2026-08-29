"""Tests fuer die LearningSession.

Der Zufall wird ueber ein injiziertes random.Random(seed) kontrolliert, damit
die Kartenauswahl reproduzierbar ist.
"""
import random

import pytest

from lernapp.core.cards import parse_items
from lernapp.core.learning_engine import (
    GEMISCHT,
    RUECKWAERTS,
    VORWAERTS,
    LearningSession,
    SessionZustand,
)
from lernapp.core.progress import SetProgress

VOKABELN = [
    {"q": "la maison", "a": "das haus"},
    {"q": "le chien", "a": "der hund"},
    {"q": "la voiture", "a": "das auto"},
]

TRIPLE = [
    {"q": "go ___ ___", "a": "went, gone"},
    {"q": "___ went ___", "a": "go, gone"},
    {"q": "___ ___ gone", "a": "go, went"},
]


def session(items, seed=1, **kw):
    return LearningSession(parse_items(items), rng=random.Random(seed), **kw)


def viele_vokabeln(n):
    """n verschiedene Karten - Duplikate wuerden deduspliziert."""
    return [{"q": f"frage{i}", "a": f"antwort{i}"} for i in range(n)]


# -- Reproduzierbarkeit -------------------------------------------------------

def test_gleicher_seed_erzeugt_gleiche_kartenfolge():
    a = [session(VOKABELN, seed=42).naechste_frage().card.key for _ in range(1)]
    b = [session(VOKABELN, seed=42).naechste_frage().card.key for _ in range(1)]
    assert a == b


def test_gleicher_seed_erzeugt_gleiche_ganze_runde():
    def durchlauf():
        s = session(VOKABELN, seed=7)
        folge = []
        while (f := s.naechste_frage()) is not None:
            folge.append(f.card.key)
            s.antworte(f.card.erwartet(f.rueckwaerts))
        return folge

    assert durchlauf() == durchlauf()


def test_verschiedene_seeds_erzeugen_verschiedene_folgen():
    def folge(seed):
        s = session(VOKABELN * 4, seed=seed)
        out = []
        while (f := s.naechste_frage()) is not None:
            out.append(f.card.key)
            s.antworte(f.card.erwartet(f.rueckwaerts))
        return out

    assert folge(1) != folge(99999)


# -- Richtungen ---------------------------------------------------------------

def test_vorwaerts_fragt_immer_die_antwort():
    s = session(VOKABELN, richtung=VORWAERTS)
    for _ in range(3):
        f = s.naechste_frage()
        assert not f.rueckwaerts
        s.antworte(f.card.answer)


def test_rueckwaerts_fragt_immer_die_frage():
    s = session(VOKABELN, richtung=RUECKWAERTS)
    f = s.naechste_frage()
    assert f.rueckwaerts
    assert f.anzeige == f.card.answer


def test_gemischt_erzeugt_beide_richtungen():
    s = session(viele_vokabeln(60), seed=3, richtung=GEMISCHT)
    richtungen = set()
    while (f := s.naechste_frage()) is not None:
        richtungen.add(f.rueckwaerts)
        s.antworte(f.card.erwartet(f.rueckwaerts))
    assert richtungen == {True, False}


def test_triple_wird_nie_rueckwaerts_gefragt():
    s = session(TRIPLE, richtung=RUECKWAERTS)
    f = s.naechste_frage()
    assert not f.rueckwaerts


# -- Antworten ----------------------------------------------------------------

def test_richtige_antwort_gibt_xp_und_erhoeht_combo():
    s = session(VOKABELN)
    f = s.naechste_frage()
    e = s.antworte(f.card.erwartet(f.rueckwaerts))
    assert e.richtig
    assert e.xp == 10
    assert e.combo == 1


def test_falsche_antwort_setzt_combo_zurueck():
    s = session(VOKABELN)
    f = s.naechste_frage()
    s.antworte(f.card.erwartet(f.rueckwaerts))
    f = s.naechste_frage()
    e = s.antworte("voellig falsch")
    assert not e.richtig
    assert e.combo == 0
    assert s.fortschritt.best_combo == 1


def test_combo_multiplikator_greift():
    s = session(viele_vokabeln(10), seed=2, richtung=VORWAERTS)
    letzte = None
    for _ in range(7):
        f = s.naechste_frage()
        letzte = s.antworte(f.card.answer)
    assert letzte.combo == 7
    assert letzte.multiplikator == 3.0


def test_antwort_ohne_frage_ist_ein_fehler():
    s = session(VOKABELN)
    with pytest.raises(RuntimeError):
        s.antworte("irgendwas")


# -- Triple-Verhalten ---------------------------------------------------------

def test_richtige_triple_antwort_zaehlt_nur_fuer_diese_karte():
    s = session(TRIPLE)
    f = s.naechste_frage()
    s.antworte(list(f.card.erwartet))
    gesetzt = [k for k, v in s.fortschritt.streaks.items() if v >= 1]
    assert gesetzt == [f.card.key], "nur die beantwortete Form zaehlt"


def test_falsche_triple_antwort_setzt_das_ganze_paket_zurueck():
    s = session(TRIPLE, richtung=VORWAERTS)
    # zwei Formen richtig
    for _ in range(2):
        f = s.naechste_frage()
        s.antworte(list(f.card.erwartet))
    assert sum(1 for v in s.fortschritt.streaks.values() if v >= 1) == 2
    # dritte falsch
    f = s.naechste_frage()
    s.antworte(["quatsch", "unsinn"])
    assert all(v == 0 for v in s.fortschritt.streaks.values()), "ganzes Paket faellt"


def test_regression_had_to_karte_ist_loesbar():
    """Diese Karte aus den echten Daten war nie beantwortbar."""
    s = session([{"q": "___ had to ___", "a": "must, had to"}], richtung=VORWAERTS)
    f = s.naechste_frage()
    e = s.antworte(["must", "had to"])
    assert e.richtig


def test_regression_kaputtes_paket_erreicht_100_prozent():
    """must/had to/had to war frueher in zwei Pakete zerfallen und blockierte
    den Abschluss der Runde."""
    kaputt = [
        {"q": "must ___ ___", "a": "had to, had to"},
        {"q": "___ had to ___", "a": "must, had to"},
        {"q": "___ ___ had to", "a": "must, had to"},
    ]
    s = session(kaputt, richtung=VORWAERTS)
    while (f := s.naechste_frage()) is not None:
        e = s.antworte(list(f.card.erwartet))
        assert e.richtig
    assert s.zustand == SessionZustand.FERTIG
    assert s.fortschritt_zaehler() == (1, 1)


# -- Zaehlung -----------------------------------------------------------------

def test_fortschritt_zaehlt_paket_als_eine_einheit():
    s = session(TRIPLE + VOKABELN, richtung=VORWAERTS)
    assert s.fortschritt_zaehler() == (0, 4), "1 Paket + 3 Vokabeln"


def test_paket_gilt_erst_als_gelernt_wenn_alle_drei_sitzen():
    s = session(TRIPLE, richtung=VORWAERTS)
    assert s.fortschritt_zaehler() == (0, 1)
    for nach_antwort in (0, 0, 1):
        f = s.naechste_frage()
        assert f is not None
        s.antworte(list(f.card.erwartet))
        assert s.fortschritt_zaehler()[0] == nach_antwort
    assert s.fortschritt_zaehler() == (1, 1)


# -- Runden -------------------------------------------------------------------

def test_runde_endet_und_fehlerkarten_kommen_zurueck():
    s = session(VOKABELN, seed=5, richtung=VORWAERTS)
    falsch_key = None
    while (f := s.naechste_frage()) is not None:
        if falsch_key is None:
            falsch_key = f.card.key
            s.antworte("falsch")
            # gleiche Karte gleich nochmal richtig, damit die Runde endet
            f2 = s.naechste_frage()
            while f2.card.key != falsch_key:
                s.antworte(f2.card.answer)
                f2 = s.naechste_frage()
            s.antworte(f2.card.answer)
        else:
            s.antworte(f.card.answer)

    assert s.zustand == SessionZustand.RUNDE_FERTIG
    assert s.naechste_runde() is True
    assert s.runde == 2
    assert s.fortschritt.streaks[falsch_key] == 0, "Fehlerkarte muss zurueck"
    assert s.fortschritt.round_errors == {}, "Rundenfehler geleert"
    assert s.fortschritt.total_errors[falsch_key] == 1, "Historie bleibt"


def test_fehlerfreie_runde_beendet_die_sitzung():
    s = session(VOKABELN, richtung=VORWAERTS)
    while (f := s.naechste_frage()) is not None:
        s.antworte(f.card.answer)
    assert s.zustand == SessionZustand.FERTIG
    assert s.naechste_runde() is False


def test_neustart_setzt_alles_zurueck():
    s = session(VOKABELN, richtung=VORWAERTS)
    while (f := s.naechste_frage()) is not None:
        s.antworte(f.card.answer)
    s.neustart()
    assert s.fortschritt.xp == 0
    assert s.runde == 1
    assert s.fortschritt_zaehler()[0] == 0


# -- Fortschritt uebernehmen --------------------------------------------------

def test_bestehender_fortschritt_wird_uebernommen():
    p = SetProgress(xp=100, streaks={"la maison": 1})
    s = LearningSession(parse_items(VOKABELN), fortschritt=p, rng=random.Random(1))
    assert s.fortschritt.xp == 100
    assert "la maison" not in s.offene_keys


def test_unbekannte_karten_bekommen_streak_null():
    p = SetProgress(streaks={"veraltete karte": 5})
    s = LearningSession(parse_items(VOKABELN), fortschritt=p, rng=random.Random(1))
    assert set(s.offene_keys) == {i["q"] for i in VOKABELN}


# -- Statistik ----------------------------------------------------------------

def test_statistik_nutzt_gesamtfehler_nicht_rundenfehler():
    s = session(VOKABELN, richtung=VORWAERTS)
    f = s.naechste_frage()
    key = f.card.key
    s.antworte("falsch")
    s.fortschritt.neue_runde()
    st = s.statistik()
    assert st["falsch"] == 1
    assert st["schwerste_karten"] == [(key, 1)], "Historie ueberlebt den Rundenwechsel"
