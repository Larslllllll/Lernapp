"""Charakterisierungstests: neuer Core gegen das eingefrorene Altverhalten.

Die Referenzfunktionen unten sind wörtliche Kopien aus LernApp.py vor dem
Refactor. Sie bleiben absichtlich hier stehen, damit jede künftige Änderung
an den Spielregeln sofort auffällt.
"""
import pytest

from lernapp.core import rules
from lernapp.core.cards import parse_card

# ---------------------------------------------------------------------------
# Eingefrorene Referenz - Stand vor Phase 1. NICHT anpassen.
# ---------------------------------------------------------------------------

LEGACY_LEVEL_XP = [0, 50, 150, 300, 500, 750, 1000, 1500, 2000, 3000]


def legacy_get_level(xp):
    lvl = 1
    for i, t in enumerate(LEGACY_LEVEL_XP):
        if xp >= t:
            lvl = i + 1
    return min(lvl, len(LEGACY_LEVEL_XP))


def legacy_combo_mul(combo):
    if combo >= 7:
        return 3.0
    if combo >= 4:
        return 2.0
    if combo >= 2:
        return 1.5
    return 1.0


def legacy_gain(streak, combo):
    return round((10 + (streak - 1) * 5) * legacy_combo_mul(combo))


def legacy_pkg_key(q, a):
    """Alte Triple-Erkennung. Zerbricht an mehrwortigen Formen - genau das
    zeigt test_neue_paketbildung_repariert_altbug unten."""
    if "___" not in q:
        return None
    known = next(t for t in q.split() if t != "___")
    others = [p.strip() for p in a.split(", ")]
    return frozenset([known] + others)


# ---------------------------------------------------------------------------
# Äquivalenz
# ---------------------------------------------------------------------------

def test_level_xp_tabelle_unveraendert():
    assert list(rules.LEVEL_XP) == LEGACY_LEVEL_XP


def test_get_level_stimmt_ueber_den_ganzen_bereich():
    abweichungen = [x for x in range(0, 5001) if rules.get_level(x) != legacy_get_level(x)]
    assert abweichungen == []


def test_combo_mul_stimmt_ueber_den_ganzen_bereich():
    abweichungen = [c for c in range(0, 200) if rules.combo_mul(c) != legacy_combo_mul(c)]
    assert abweichungen == []


def test_xp_formel_stimmt():
    abweichungen = [
        (s, c)
        for s in range(1, 20)
        for c in range(0, 20)
        if rules.xp_gain(s, c) != legacy_gain(s, c)
    ]
    assert abweichungen == []


# ---------------------------------------------------------------------------
# Historische Fixpunkte
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("xp,erwartet", [
    (0, 1), (49, 1), (50, 2), (149, 2), (150, 3), (300, 4), (500, 5),
    (750, 6), (1000, 7), (1500, 8), (2000, 9), (3000, 10), (99999, 10),
])
def test_level_fixpunkte(xp, erwartet):
    assert rules.get_level(xp) == erwartet


@pytest.mark.parametrize("combo,erwartet", [
    (0, 1.0), (1, 1.0), (2, 1.5), (3, 1.5),
    (4, 2.0), (6, 2.0), (7, 3.0), (100, 3.0),
])
def test_combo_fixpunkte(combo, erwartet):
    assert rules.combo_mul(combo) == erwartet


@pytest.mark.parametrize("streak,combo,erwartet", [
    (1, 1, 10), (2, 1, 15), (1, 2, 15), (1, 4, 20), (1, 7, 30), (3, 7, 60),
])
def test_xp_fixpunkte(streak, combo, erwartet):
    assert rules.xp_gain(streak, combo) == erwartet


# ---------------------------------------------------------------------------
# Bewusste Verhaltensänderung - dokumentiert, nicht versehentlich
# ---------------------------------------------------------------------------

def test_neue_paketbildung_repariert_altbug():
    """Bei mehrwortigen Formen wich die alte Paketbildung ab.

    'been able' wurde von q.split() zu 'been' verkürzt, wodurch die dritte
    Karte in einem eigenen Paket landete.
    """
    alt = legacy_pkg_key("___ ___ been able", "can, could")
    neu = parse_card({"q": "___ ___ been able", "a": "can, could"}).package_key

    assert alt == frozenset({"been", "can", "could"}), "alter Fehler"
    assert neu == ("can", "could", "been able"), "neu korrekt"

    geschwister = legacy_pkg_key("can ___ ___", "could, been able")
    assert alt != geschwister, "alt: zwei Pakete statt einem"
    neu_geschwister = parse_card({"q": "can ___ ___", "a": "could, been able"}).package_key
    assert neu == neu_geschwister, "neu: ein Paket"


def test_alte_und_neue_paketbildung_stimmen_bei_einwortformen_ueberein():
    """Wo die alte Logik funktionierte, gruppiert die neue identisch."""
    formen = [
        ("go ___ ___", "went, gone"),
        ("___ went ___", "go, gone"),
        ("___ ___ gone", "go, went"),
    ]
    alte = {legacy_pkg_key(q, a) for q, a in formen}
    neue = {parse_card({"q": q, "a": a}).package_key for q, a in formen}
    assert len(alte) == 1
    assert len(neue) == 1


# ---------------------------------------------------------------------------
# level_fortschritt - Grundlage der XP-Anzeige
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("xp,level,seit,spanne", [
    (0, 1, 0, 50),
    (25, 1, 25, 50),
    (50, 2, 0, 100),
    (149, 2, 99, 100),
    (2999, 9, 999, 1000),
])
def test_level_fortschritt(xp, level, seit, spanne):
    assert rules.level_fortschritt(xp) == (level, seit, spanne)


def test_level_fortschritt_bei_maximum():
    level, seit, spanne = rules.level_fortschritt(999999)
    assert level == rules.MAX_LEVEL
    assert seit is None and spanne is None, "keine Division durch None im UI"


def test_level_fortschritt_teilt_nie_durch_null():
    for xp in range(0, 3200, 7):
        _lvl, seit, spanne = rules.level_fortschritt(xp)
        if spanne is not None:
            assert spanne > 0
            assert 0 <= seit / spanne <= 1
