"""Tests für SetProgress - Fehlerzähler, Combo und Legacy-Kompatibilität."""
from lernapp.core.progress import SCHEMA_VERSION, SetProgress


# -- round_errors vs total_errors ---------------------------------------------

def test_neue_runde_leert_nur_rundenfehler():
    p = SetProgress()
    p.falsch(["a"])
    p.falsch(["b"])
    assert p.round_errors == {"a": 1, "b": 1}
    assert p.total_errors == {"a": 1, "b": 1}

    p.neue_runde()
    assert p.round_errors == {}
    assert p.total_errors == {"a": 1, "b": 1}, "Historie darf nicht verloren gehen"


def test_total_errors_summiert_ueber_runden():
    p = SetProgress()
    p.falsch(["a"])
    p.neue_runde()
    p.falsch(["a"])
    assert p.round_errors == {"a": 1}
    assert p.total_errors == {"a": 2}


def test_gewichtung_nutzt_nur_rundenfehler():
    p = SetProgress()
    assert p.gewicht("a") == 1
    p.falsch(["a"])
    assert p.gewicht("a") == 4
    p.neue_runde()
    assert p.gewicht("a") == 1, "nach Rundenwechsel wieder normal gewichtet"


# -- current_combo vs best_combo ----------------------------------------------

def test_best_combo_ueberlebt_einen_fehler():
    p = SetProgress()
    for _ in range(5):
        p.richtig(["a"])
    assert p.current_combo == 5
    assert p.best_combo == 5

    p.falsch(["a"])
    assert p.current_combo == 0
    assert p.best_combo == 5, "Rekord darf nicht verloren gehen"


def test_best_combo_waechst_nur_nach_oben():
    p = SetProgress()
    for _ in range(3):
        p.richtig(["a"])
    p.falsch(["a"])
    p.richtig(["a"])
    assert p.current_combo == 1
    assert p.best_combo == 3


def test_neustart_behaelt_best_combo_als_rekord():
    p = SetProgress()
    for _ in range(4):
        p.richtig(["a"])
    p.zuruecksetzen()
    assert p.xp == 0
    assert p.total_correct == 0
    assert p.streaks["a"] == 0
    assert p.best_combo == 4


# -- XP -----------------------------------------------------------------------

def test_richtig_vergibt_xp_und_meldet_level_up():
    p = SetProgress()
    gewinn, level_up = p.richtig(["a"])
    assert gewinn == 10
    assert not level_up
    assert p.xp == 10


def test_level_up_wird_gemeldet():
    p = SetProgress(xp=45)
    _, level_up = p.richtig(["a"])
    assert level_up, "45 + 10 XP ueberschreitet die Schwelle 50"
    assert p.level == 2


def test_falsche_antwort_setzt_ganzes_paket_zurueck():
    p = SetProgress()
    p.richtig(["k1"])
    p.richtig(["k2"])
    p.falsch(["k1", "k2", "k3"])
    assert p.streaks["k1"] == 0
    assert p.streaks["k2"] == 0
    assert p.streaks["k3"] == 0


def test_fehler_wird_nur_der_hauptkarte_zugeschrieben():
    p = SetProgress()
    p.falsch(["k1", "k2", "k3"])
    assert p.total_errors == {"k1": 1}


# -- Legacy-Kompatibilität ---------------------------------------------------

def test_liest_altes_format():
    alt = {
        "xp": 460, "correct": 23, "wrong": 7,
        "errors": {"go ___ ___": 2}, "combo": 12,
        "streaks": {"go ___ ___": 1},
    }
    p = SetProgress.from_legacy(alt)
    assert p.xp == 460
    assert p.total_correct == 23
    assert p.total_wrong == 7
    assert p.streaks == {"go ___ ___": 1}


def test_gespeicherte_combo_startet_nicht_wieder_als_multiplikator():
    """Früher wurde combo=12 geladen und man startete sofort mit x3."""
    p = SetProgress.from_legacy({"combo": 12})
    assert p.current_combo == 0
    assert p.best_combo == 12, "Wert geht nicht verloren, wird aber zum Rekord"


def test_alte_errors_gehen_in_die_historie_ueber():
    p = SetProgress.from_legacy({"errors": {"a": 3}})
    assert p.round_errors == {"a": 3}
    assert p.total_errors == {"a": 3}


def test_to_legacy_bleibt_abwaertskompatibel():
    p = SetProgress(xp=100, total_correct=5, total_wrong=2, best_combo=9)
    p.streaks["a"] = 1
    roh = p.to_legacy()
    for schluessel in ("xp", "correct", "wrong", "combo", "errors", "streaks"):
        assert schluessel in roh, f"alter Schluessel {schluessel} fehlt"
    assert roh["schema_version"] == SCHEMA_VERSION
    assert roh["best_combo"] == 9


def test_speichern_und_laden_ist_verlustfrei():
    p = SetProgress(xp=250, total_correct=10, total_wrong=4, best_combo=7)
    p.streaks["a"] = 2
    p.total_errors["a"] = 3
    p.round_errors["a"] = 1
    zurueck = SetProgress.from_legacy(p.to_legacy())
    assert zurueck.xp == p.xp
    assert zurueck.total_correct == p.total_correct
    assert zurueck.best_combo == p.best_combo
    assert zurueck.total_errors == p.total_errors
    assert zurueck.streaks == p.streaks
