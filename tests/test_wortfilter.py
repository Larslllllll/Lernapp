"""Die Sperrliste für Veröffentlichungen.

Zwei Sorten Tests, und die zweite ist die wichtigere: dass der Filter das
Richtige fängt, und dass er das Falsche in Ruhe lässt. Ein Vokabeltrainer, der
„weniger" sperrt, ist unbrauchbar - und genau das war der erste Entwurf.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lernapp.core import wortfilter as w


# -- Was gefangen werden muss -------------------------------------------------

@pytest.mark.parametrize("text", [
    "nigger",
    "Nigger",
    "NIGGER",
    "nigg3r",
    "n1gg3r",
    "n!gg3r",
    "n i g g e r",
    "n-i-g-g-e-r",
    "n.i.g.g.e.r",
    "n_i_g_g_e_r",
    "niiigger",
    "niggggger",
    "nigger!!!",
    "das wort nigger steht hier mitten im satz",
    "niggers",
    "niggerish",
    "n*i*g*g*e*r",
    "ni66er",
    "n1993r",
])
def test_varianten_werden_gefangen(text):
    """Die Liste enthält nur die Grundform - der Rest ist Normalisierung."""
    assert not w.ist_sauber(text), f"durchgerutscht: {text!r}"


def test_homoglyphen_werden_gefangen():
    """Kyrillisches „е" sieht identisch aus und kommt durch jede naive Liste."""
    mit_kyrillisch = "niggеr"          # e -> U+0435
    assert mit_kyrillisch != "nigger"
    assert not w.ist_sauber(mit_kyrillisch)


def test_akzente_werden_gefangen():
    assert not w.ist_sauber("nïggér")


def test_mehrere_treffer_werden_einzeln_gemeldet():
    """Mehr Treffer als erwartet sind in Ordnung - `faggot` erfüllt auch das
    Muster von `fagot`. Entscheidend ist, dass beide Wörter auffallen."""
    treffer = {t.wort for t in w.pruefe("nigger und faggot")}
    assert {"nigger", "faggot"} <= treffer


# -- Was in Ruhe gelassen werden muss ----------------------------------------

@pytest.mark.parametrize("text", [
    # Der Fehler, an dem der erste Entwurf gescheitert ist: Doppelbuchstaben
    # zusammenziehen macht aus "nigger" ein "niger", und das steckt in:
    "weniger",
    "einiger",
    "wenigerer",
    "Niger",
    "Nigeria",
    "nigerianisch",
    # Klassiker der Fehlalarme
    "suspicion",
    "spicy",
    "spice",
    "Spickzettel",
    "spicken",
    "denigrate",
    "snigger",
    "raccoon",
    "cocoon",
    "tycoon",
    "Negroni",
    # ganz normale Vokabeln
    "la maison; das Haus",
    "être; sein",
    "to go; went; gone",
    "der Kanal",
    "die Gasse",
    "das Krankenhaus",
    "gaskets",
    "Untermiete",
    "Hitliste",
    "cooking",
    "school",
])
def test_harmlose_texte_bleiben_unbehelligt(text):
    treffer = w.pruefe(text)
    assert treffer == [], f"Fehlalarm bei {text!r}: {[t.wort for t in treffer]}"


def test_kurze_grundformen_muessen_das_ganze_wort_ausfuellen():
    """Sonst sperrt `spic` das englische Wort `suspicion`."""
    assert not w.ist_sauber("spic")
    assert w.ist_sauber("suspicion")
    assert w.ist_sauber("spicier")


def test_kurze_grundformen_werden_nicht_ueber_wortgrenzen_gesucht():
    """`negro` steckt in „eine grosse" - das darf nicht anschlagen."""
    assert w.ist_sauber("eine grosse Wohnung")


# -- Lernsets ----------------------------------------------------------------

def test_lernset_meldet_die_karte():
    treffer = w.pruefe_lernset("Englisch", [
        {"q": "the house", "a": "das haus"},
        {"q": "nigger", "a": "test"},
    ])
    assert len(treffer) == 1
    assert treffer[0].fundstelle == "Karte 2, Frage"


def test_lernset_meldet_den_namen():
    treffer = w.pruefe_lernset("faggot vokabeln", [{"q": "a", "a": "b"}])
    assert treffer[0].fundstelle == "im Namen des Lernsets"


def test_sauberes_lernset_hat_keine_treffer():
    assert w.pruefe_lernset("Unité 4", [
        {"q": "la maison", "a": "das haus"},
        {"q": "le chien", "a": "der hund"},
    ]) == []


def test_meldung_nennt_die_stelle_aber_nicht_das_wort():
    """Die Meldung landet sonst als Bildschirmfoto im Klassenchat."""
    treffer = w.pruefe_lernset("Test", [{"q": "nigger", "a": "x"}])
    text = w.meldung(treffer)
    assert "Karte 1, Frage" in text
    assert "nigger" not in text.lower()
    assert w.meldung([]) == ""


# -- Gegen die echten Daten ---------------------------------------------------

def test_keine_fehlalarme_in_den_veroeffentlichten_lernsets():
    """1516 echte Karten aus Französisch, Englisch und Latein.

    Der beste verfügbare Fehlalarm-Test: echter Unterrichtsstoff in drei
    Sprachen. Läuft nur, wenn das Lernset-Repo daneben liegt.
    """
    wurzel = Path(__file__).resolve().parent.parent.parent / "Lernapp-lernsets"
    if not wurzel.is_dir():
        pytest.skip("Lernset-Repo liegt nicht daneben")

    dateien = sorted(wurzel.rglob("*.lernset.json"))
    if not dateien:
        pytest.skip("keine Lernsets gefunden")

    fehlalarme = []
    for datei in dateien:
        roh = json.loads(datei.read_text(encoding="utf-8"))
        for treffer in w.pruefe_lernset(roh["name"], roh["items"]):
            fehlalarme.append(f"{datei.name}: {treffer.wort} ({treffer.fundstelle})")
    assert not fehlalarme, "Fehlalarme in echten Lernsets:\n" + "\n".join(fehlalarme)
