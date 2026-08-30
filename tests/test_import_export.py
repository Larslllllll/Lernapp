"""Tests für Import und Export von Lernsets."""
import pytest

from lernapp.core.cards import gruppiere_pakete, lerneinheiten, parse_items
from lernapp.core.import_export import (
    DATEIENDUNG,
    KOMMA,
    SEMIKOLON,
    TAB,
    als_export,
    als_text,
    aus_export,
    dateiname_fuer,
    erkenne_trenner,
    parse_text,
)


# -- Trennererkennung ---------------------------------------------------------

@pytest.mark.parametrize("text,erwartet", [
    ("être;sein", SEMIKOLON),
    ("être\tsein", TAB),
    ("être,sein", KOMMA),
    ("", SEMIKOLON),
])
def test_trenner_wird_erkannt(text, erwartet):
    assert erkenne_trenner(text) == erwartet


def test_semikolon_gewinnt_gegen_komma():
    """Antworten enthalten oft selbst Kommas - das Komma ist die letzte Wahl."""
    text = "le velo;das Fahrrad, das Rad\nla maison;das Haus"
    assert erkenne_trenner(text) == SEMIKOLON
    ergebnis = parse_text(text)
    assert ergebnis.normale == 2
    assert ergebnis.items[0] == {"q": "le velo", "a": "das fahrrad, das rad"}


def test_tabulator_gewinnt_gegen_semikolon():
    assert erkenne_trenner("a\tb;c") == TAB


# -- Normale Karten -----------------------------------------------------------

def test_zwei_felder_ergeben_eine_karte():
    ergebnis = parse_text("être;sein\navoir;haben")
    assert ergebnis.normale == 2
    assert ergebnis.pakete == 0
    assert ergebnis.items == [
        {"q": "être", "a": "sein"},
        {"q": "avoir", "a": "haben"},
    ]


def test_leerzeilen_und_leerraum_werden_ignoriert():
    ergebnis = parse_text("\n  être ;  sein  \n\n\navoir;haben\n\n")
    assert ergebnis.normale == 2
    assert ergebnis.items[0] == {"q": "être", "a": "sein"}
    assert ergebnis.probleme == []


# -- Verbpakete ---------------------------------------------------------------

def test_drei_felder_ergeben_ein_paket():
    ergebnis = parse_text("go;went;gone")
    assert ergebnis.pakete == 1
    assert ergebnis.normale == 0
    assert len(ergebnis.items) == 3
    pakete = gruppiere_pakete(parse_items(ergebnis.items))
    assert len(pakete) == 1
    assert lerneinheiten(parse_items(ergebnis.items)) == 1


def test_mehrwortige_formen_im_import():
    """Genau der Fall, an dem die Vorgängerversion zerbrochen ist."""
    ergebnis = parse_text("can;could;been able\nmust;had to;had to")
    assert ergebnis.pakete == 2
    karten = parse_items(ergebnis.items)
    pakete = gruppiere_pakete(karten)
    assert len(pakete) == 2
    for gruppe in pakete.values():
        assert sorted(c.revealed for c in gruppe) == [0, 1, 2]


def test_gemischter_import():
    ergebnis = parse_text("go;went;gone\nla maison;das haus")
    assert (ergebnis.pakete, ergebnis.normale) == (1, 1)
    assert ergebnis.einheiten == 2
    assert len(ergebnis.items) == 4


# -- Fehlerhafte Zeilen -------------------------------------------------------

def test_zeile_ohne_trenner_wird_gemeldet_nicht_verschluckt():
    ergebnis = parse_text("être;sein\nkaputte zeile\navoir;haben")
    assert ergebnis.normale == 2
    assert len(ergebnis.probleme) == 1
    assert ergebnis.probleme[0].zeile == 2
    assert ergebnis.probleme[0].text == "kaputte zeile"


def test_zu_viele_felder_werden_gemeldet():
    ergebnis = parse_text("a;b;c;d")
    assert ergebnis.items == []
    assert "4 Felder" in ergebnis.probleme[0].grund


def test_leerer_text_ist_kein_absturz():
    ergebnis = parse_text("")
    assert ergebnis.ok is False
    assert ergebnis.zusammenfassung() == "Nichts erkannt"


def test_zusammenfassung_ist_lesbar():
    ergebnis = parse_text("go;went;gone\nla maison;das haus\nkaputt")
    assert ergebnis.zusammenfassung() == "1 Karte und 1 Verbpaket, 1 Zeile übersprungen"


# -- Export -------------------------------------------------------------------

def test_export_enthaelt_nur_inhalt_keinen_fortschritt():
    daten = als_export("Unite 4", [{"q": "a", "a": "b"}], app_version="0.9.0")
    assert daten["typ"] == "lernset"
    assert daten["name"] == "Unite 4"
    assert daten["items"] == [{"q": "a", "a": "b"}]
    assert "xp" not in str(daten)
    assert "streaks" not in str(daten)


def test_export_import_roundtrip():
    items = parse_text("go;went;gone\nla maison;das haus").items
    name, zurueck = aus_export(als_export("Verben", items))
    assert name == "Verben"
    assert zurueck == items


def test_import_lehnt_unsinn_ab():
    for roh in ({}, {"items": []}, {"items": "keine liste"}, []):
        with pytest.raises(ValueError):
            aus_export(roh)


def test_import_lehnt_neuere_schemaversion_ab():
    with pytest.raises(ValueError, match="neueren Programmversion"):
        aus_export({"schema_version": 99, "items": [{"q": "a", "a": "b"}]})


def test_import_verwirft_kaputte_eintraege_behaelt_den_rest():
    name, items = aus_export({"items": [
        {"q": "gut", "a": "bon"},
        {"q": "", "a": "leer"},
        "kein dict",
        {"q": "auch gut", "a": "aussi bon"},
    ]})
    assert items == [{"q": "gut", "a": "bon"}, {"q": "auch gut", "a": "aussi bon"}]


def test_import_ohne_namen_bekommt_einen():
    name, _ = aus_export({"items": [{"q": "a", "a": "b"}]})
    assert name == "Importiertes Lernset"


# -- Dateinamen ---------------------------------------------------------------

@pytest.mark.parametrize("name,erwartet", [
    ("Unite 4", "Unite-4" + DATEIENDUNG),
    ("Unregelmäßige Verben", "Unregelmäßige-Verben" + DATEIENDUNG),
    ('bad<>:"/\\|?*name', "bad---------name" + DATEIENDUNG),
    ("   ", "Lernset" + DATEIENDUNG),
])
def test_dateiname_ist_plattformsicher(name, erwartet):
    ergebnis = dateiname_fuer(name)
    assert ergebnis == erwartet
    assert not any(z in ergebnis for z in '<>:"/\\|?*')


# -- Textexport ---------------------------------------------------------------

def test_textexport_fasst_pakete_wieder_zusammen():
    items = parse_text("go;went;gone\nla maison;das haus").items
    assert len(items) == 4
    text = als_text(items)
    assert text.splitlines() == ["go;went;gone", "la maison;das haus"]


def test_textexport_und_reimport_sind_stabil():
    original = "can;could;been able\nmust;had to;had to\nla maison;das haus"
    einmal = parse_text(original).items
    zweimal = parse_text(als_text(einmal)).items
    assert einmal == zweimal
