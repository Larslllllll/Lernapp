"""Tests fuer das Kartenmodell und das Parsen des Legacy-Formats."""
import pytest

from lernapp.core.cards import (
    NormalCard,
    TripleCard,
    gruppiere_pakete,
    lerneinheiten,
    parse_card,
    parse_items,
)


# -- Normale Karten -----------------------------------------------------------

def test_normale_karte_wird_nicht_als_triple_erkannt():
    c = parse_card({"q": "la maison", "a": "das Haus"})
    assert isinstance(c, NormalCard)
    assert not c.is_triple
    assert c.key == "la maison"


def test_normale_karte_prueft_unabhaengig_von_gross_klein_und_leerzeichen():
    c = NormalCard("la maison", "das Haus")
    assert c.pruefe("das haus")
    assert c.pruefe("  DAS HAUS  ")
    assert not c.pruefe("das Auto")


def test_normale_karte_akzeptiert_alternativen_mit_komma_und_semikolon():
    c = NormalCard("le velo", "das Fahrrad, das Rad")
    assert c.pruefe("das Fahrrad")
    assert c.pruefe("das Rad")
    d = NormalCard("le velo", "das Fahrrad; das Rad")
    assert d.pruefe("das Rad")


def test_normale_karte_nennt_weitere_loesungen():
    c = NormalCard("le velo", "das Fahrrad, das Rad")
    assert c.weitere_loesungen("das Rad") == ["das fahrrad"]


def test_rueckwaerts_fragt_die_antwort_ab():
    c = NormalCard("la maison", "das Haus")
    assert c.zeigt(rueckwaerts=True) == "das Haus"
    assert c.pruefe("la maison", rueckwaerts=True)
    assert not c.pruefe("das Haus", rueckwaerts=True)


# -- Triple-Karten ------------------------------------------------------------

def test_triple_wird_erkannt_und_forms_rekonstruiert():
    c = parse_card({"q": "go ___ ___", "a": "went, gone"})
    assert isinstance(c, TripleCard)
    assert c.forms == ("go", "went", "gone")
    assert c.revealed == 0
    assert c.erwartet == ("went", "gone")


@pytest.mark.parametrize("q,a,revealed", [
    ("go ___ ___", "went, gone", 0),
    ("___ went ___", "go, gone", 1),
    ("___ ___ gone", "go, went", 2),
])
def test_alle_drei_karten_eines_pakets_ergeben_dieselben_forms(q, a, revealed):
    c = parse_card({"q": q, "a": a})
    assert c.forms == ("go", "went", "gone")
    assert c.revealed == revealed


def test_triple_prueft_reihenfolge():
    c = parse_card({"q": "___ went ___", "a": "go, gone"})
    assert c.pruefe(["go", "gone"])
    assert not c.pruefe(["gone", "go"])
    assert not c.pruefe(["go"])


def test_slots_liefern_anzeigeplan():
    c = parse_card({"q": "___ went ___", "a": "go, gone"})
    assert c.slots() == [(0, None), (1, "went"), (2, None)]


# -- Regressionstests: die drei kaputten Karten aus den echten Daten ----------
# Diese Karten stehen so in data.json. Die alte Whitespace-Tokenisierung ist an
# ihnen zerbrochen.

def test_regression_mehrwortige_form_am_ende():
    """'been able' wurde von q.split() zu 'been' verstuemmelt."""
    c = parse_card({"q": "___ ___ been able", "a": "can, could"})
    assert c.forms == ("can", "could", "been able")
    assert c.revealed == 2
    assert c.erwartet == ("can", "could")


def test_regression_mehrwortige_form_in_der_mitte_ist_loesbar():
    """'___ had to ___' erzeugte nur EIN Eingabefeld und war nie loesbar."""
    c = parse_card({"q": "___ had to ___", "a": "must, had to"})
    assert c.forms == ("must", "had to", "had to")
    assert c.revealed == 1
    assert len(c.hidden_indices) == 2
    assert c.pruefe(["must", "had to"])


def test_regression_paket_mit_doppelter_form_kollabiert_nicht():
    """frozenset({'must','had to','had to'}) hatte nur 2 Elemente."""
    karten = parse_items([
        {"q": "must ___ ___", "a": "had to, had to"},
        {"q": "___ had to ___", "a": "must, had to"},
        {"q": "___ ___ had to", "a": "must, had to"},
    ])
    pakete = gruppiere_pakete(karten)
    assert len(pakete) == 1
    (gruppe,) = pakete.values()
    assert len(gruppe) == 3
    assert sorted(c.revealed for c in gruppe) == [0, 1, 2]


def test_regression_can_could_been_able_ist_ein_paket():
    karten = parse_items([
        {"q": "can ___ ___", "a": "could, been able"},
        {"q": "___ could ___", "a": "can, been able"},
        {"q": "___ ___ been able", "a": "can, could"},
    ])
    assert len(gruppiere_pakete(karten)) == 1


# -- Verlustfreiheit ----------------------------------------------------------

@pytest.mark.parametrize("item", [
    {"q": "la maison", "a": "das Haus"},
    {"q": "go ___ ___", "a": "went, gone"},
    {"q": "___ was/were ___", "a": "be, been"},
    {"q": "___ ___ been able", "a": "can, could"},
    {"q": "___ had to ___", "a": "must, had to"},
])
def test_roundtrip_ist_verlustfrei(item):
    """Der Legacy-Schluessel muss exakt erhalten bleiben - progress.json
    indiziert historisch nach der Frage-Zeichenkette."""
    assert parse_card(item).legacy_item() == item


# -- Zaehlung -----------------------------------------------------------------

def test_triple_paket_zaehlt_als_eine_lerneinheit():
    karten = parse_items([
        {"q": "go ___ ___", "a": "went, gone"},
        {"q": "___ went ___", "a": "go, gone"},
        {"q": "___ ___ gone", "a": "go, went"},
        {"q": "la maison", "a": "das Haus"},
    ])
    assert len(karten) == 4
    assert lerneinheiten(karten) == 2


# -- Robustheit gegen von Hand bearbeitete Daten ------------------------------

@pytest.mark.parametrize("item", [
    {"q": "___ ___ ___", "a": "a, b"},        # keine sichtbare Form
    {"q": "go ___", "a": "went"},             # nur eine Luecke
    {"q": "go ___ ___ ___", "a": "a, b"},     # drei Luecken
    {"q": "go ___ ___", "a": "nur eine"},     # nur eine Antwort
    {"q": "go ___ ___", "a": "a, "},          # leere zweite Antwort
])
def test_unsauberes_triple_faellt_auf_normale_karte_zurueck(item):
    """Lieber als normale Karte behandeln als abstuerzen."""
    c = parse_card(item)
    assert not c.is_triple
    assert c.legacy_item() == item


def test_triplecard_lehnt_ungueltige_werte_ab():
    with pytest.raises(ValueError):
        TripleCard(forms=("a", "b"), revealed=0)
    with pytest.raises(ValueError):
        TripleCard(forms=("a", "b", "c"), revealed=3)


def test_akzeptierte_antworten_listet_alle_varianten():
    c = NormalCard("le velo", "das Fahrrad; das Rad")
    assert c.akzeptierte_antworten() == ["das fahrrad", "das rad"]
