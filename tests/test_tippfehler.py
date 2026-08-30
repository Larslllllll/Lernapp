"""Tippfehler-Erkennung.

Zwei Sorten Tests, und die zweite ist die wichtigere: dass Vertipper erkannt
werden, und dass **andere Wörter nicht** als Vertipper durchgehen. `Haus` und
`Maus` unterscheidet ein Buchstabe - wer das durchwinkt, bringt Leuten
falsche Vokabeln bei.
"""
from __future__ import annotations

import pytest

from lernapp.core import tippfehler as t


# -- Abstand ------------------------------------------------------------------

@pytest.mark.parametrize("a,b,erwartet", [
    ("maison", "maison", 0),
    ("maisson", "maison", 1),     # ein Zeichen zu viel
    ("maion", "maison", 1),       # ein Zeichen fehlt
    ("maisen", "maison", 1),      # ein Zeichen falsch
    ("maisno", "maison", 1),      # vertauscht - deshalb Damerau
    ("", "maison", 6),
    ("maison", "", 6),
])
def test_abstand(a, b, erwartet):
    assert t.abstand(a, b) == erwartet


def test_vertauschen_zaehlt_als_ein_fehler():
    """Beim einfachen Levenshtein wären es zwei - ein Anschlag zu früh ist
    aber ein Fehler, nicht zwei."""
    assert t.abstand("hte", "the") == 1


# -- Was als Tippfehler durchgeht --------------------------------------------

@pytest.mark.parametrize("eingabe,erwartet", [
    ("maisson", "maison"),
    ("maisno", "maison"),
    ("haus", "haus"),
    ("krankenhaus", "krankenhous"),
    ("unregelmässig", "unregelmässig"),
])
def test_vertipper_werden_als_fast_erkannt(eingabe, erwartet):
    ergebnis = t.vergleiche(eingabe, [erwartet])
    assert ergebnis.richtig or ergebnis.fast


def test_fehlende_akzente_werden_eigens_benannt():
    """Der häufigste Fall im Französischen - und ein anderer Rat als ein
    verrutschter Finger."""
    ergebnis = t.vergleiche("eleve", ["élève"])
    assert ergebnis.fast is True
    assert ergebnis.nur_akzente is True
    assert "Akzente" in ergebnis.grund


def test_genau_richtig_bleibt_genau_richtig():
    ergebnis = t.vergleiche("  Das   Haus ", ["das haus"])
    assert ergebnis.richtig is True
    assert ergebnis.fast is False
    assert ergebnis.grund == ""


def test_mehrere_gueltige_antworten():
    assert t.vergleiche("das rad", ["das rad", "das fahrrad"]).richtig is True
    assert t.vergleiche("das farrad", ["das rad", "das fahrrad"]).fast is True


# -- Was NICHT durchgehen darf ------------------------------------------------

@pytest.mark.parametrize("eingabe,erwartet", [
    ("maus", "haus"),      # anderes Wort, ein Buchstabe
    ("mein", "sein"),
    ("die", "der"),
    ("hut", "hund"),
    ("gehen", "sehen"),
    ("bein", "wein"),
])
def test_kurze_woerter_werden_nicht_verziehen(eingabe, erwartet):
    """Bei kurzen Wörtern ist ein Buchstabe Unterschied meistens ein anderes
    Wort. Wer das durchwinkt, bringt falsche Vokabeln bei."""
    ergebnis = t.vergleiche(eingabe, [erwartet])
    assert ergebnis.richtig is False
    assert ergebnis.fast is False, f"{eingabe!r} wurde für {erwartet!r} durchgewunken"


def test_voellig_falsche_antwort_ist_falsch():
    ergebnis = t.vergleiche("der hund", ["la maison"])
    assert ergebnis.richtig is False
    assert ergebnis.fast is False
    assert ergebnis.grund == ""


def test_leere_eingabe_ist_nie_fast_richtig():
    ergebnis = t.vergleiche("", ["maison"])
    assert ergebnis.richtig is False
    assert ergebnis.fast is False


def test_zwei_fehler_erst_ab_zwoelf_zeichen():
    # elf Zeichen: nur ein Fehler erlaubt
    assert t.erlaubte_abweichung("aufraeumenX"[:11]) == 1
    # zwölf Zeichen: zwei
    assert t.erlaubte_abweichung("unregelmaess") == 2
    # drei Zeichen: gar nichts
    assert t.erlaubte_abweichung("der") == 0


# -- Die vierte Regel: Kontext -----------------------------------------------

def test_eine_andere_richtige_antwort_ist_nie_ein_vertipper():
    """`broke` und `broken` unterscheidet eine Einfügung - genau die Sorte
    Fehler, die sonst verziehen wird. Bei unregelmässigen Verben ist das aber
    der Kern der Sache."""
    ohne_kontext = t.vergleiche("broken", ["broke"])
    assert ohne_kontext.fast is True, "ohne Kontext sieht es wie ein Vertipper aus"

    mit_kontext = t.vergleiche("broken", ["broke"], {"broken", "break"})
    assert mit_kontext.fast is False
    assert mit_kontext.grund == ""


def test_ein_echter_vertipper_bleibt_einer_trotz_kontext():
    """`brokee` ist kein Wort - im Gegensatz zu `broken`, das im selben
    Lernset steht. Beides ist ein eingefügter Buchstabe; nur der Kontext
    unterscheidet sie."""
    assert t.vergleiche("brokee", ["broke"], {"broken", "break"}).fast is True
    assert t.vergleiche("broken", ["broke"], {"broken", "break"}).fast is False


def test_ersetzung_in_einem_kurzen_wort_bleibt_falsch():
    """`brokn` ist gleich lang wie `broke` - eine Ersetzung. Bei fünf Zeichen
    wird die nicht verziehen, sonst käme `Maus` für `Haus` durch."""
    assert t.vergleiche("brokn", ["broke"]).fast is False


def test_kontext_schlaegt_die_akzentregel():
    """`ou` und `où` sind zwei französische Wörter, keine Schreibvariante."""
    assert t.vergleiche("ou", ["où"]).fast is True
    assert t.vergleiche("ou", ["où"], {"ou"}).fast is False


def test_der_grund_ist_ein_satz_fuer_menschen():
    assert "ein Buchstabe" in t.vergleiche("maisson", ["maison"]).grund
    assert "zwei Buchstaben" in t.vergleiche("unregelmasig", ["unregelmässig"]).grund


# -- Gegen die echten Daten ---------------------------------------------------

def test_keine_echte_vokabel_gilt_als_vertipper_einer_anderen():
    """76 229 Antwortpaare aus 24 echten Lernsets.

    Der Lauf, der die vierte Regel überhaupt erst nötig gemacht hat: ohne
    sie gingen 68 Paare durch, darunter bit/bite, broke/broken und
    choose/chose.
    """
    import json
    from itertools import combinations
    from pathlib import Path as P

    from lernapp.core.cards import _antwort_varianten

    wurzel = P(__file__).resolve().parent.parent.parent / "Lernapp-lernsets" / "lernsets"
    if not wurzel.is_dir():
        pytest.skip("Lernset-Repo liegt nicht daneben")

    durchgewunken = []
    for datei in sorted(wurzel.rglob("*.lernset.json")):
        roh = json.loads(datei.read_text(encoding="utf-8"))
        menge = set()
        for karte in roh["items"]:
            menge.update(a for a in _antwort_varianten(karte["a"]) if a)
        for a, b in combinations(sorted(menge), 2):
            if t.vergleiche(a, [b], menge - {b}).fast:
                durchgewunken.append(f"{datei.name}: {a!r} statt {b!r}")
    assert not durchgewunken, ("Echte Vokabeln als Vertipper durchgewunken:\n"
                               + "\n".join(durchgewunken[:20]))
