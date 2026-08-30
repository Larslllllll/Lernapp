"""Der Marktplatz-Kern - ohne Netz, ohne Qt.

Geprüft wird vor allem, was passiert, wenn der Katalog nicht das enthält,
was er soll. Die Datei kommt aus dem Netz; nichts darin ist vertrauenswürdig,
bevor es geprüft wurde.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from lernapp.netz import marktplatz as m

BASIS = "https://raw.githubusercontent.com/Larslllllll/Lernapp-lernsets/main/"


def _lernset_bytes(name="Beispiel", items=None) -> bytes:
    daten = {
        "schema_version": 1,
        "typ": "lernset",
        "name": name,
        "items": items or [{"q": "the house", "a": "das haus"}],
    }
    return json.dumps(daten, ensure_ascii=False).encode("utf-8")


def _katalog_bytes(eintraege) -> bytes:
    return json.dumps({
        "schema_version": 1,
        "aktualisiert_am": "2026-08-30",
        "basis_url": BASIS,
        "lernsets": eintraege,
    }).encode("utf-8")


def _eintrag(datei="lernsets/Englisch/Beispiel.lernset.json", **rest) -> dict:
    inhalt = rest.pop("inhalt", _lernset_bytes())
    satz = {
        "id": "englisch/beispiel",
        "name": "Beispiel",
        "ordner": "Englisch",
        "datei": datei,
        "karten": 1,
        "groesse": len(inhalt),
        "sha256": hashlib.sha256(inhalt).hexdigest(),
    }
    satz.update(rest)
    return satz


def _lader(seiten: dict[str, bytes]):
    """Ein Lader, der nur die hinterlegten Adressen kennt."""
    def laden(url: str) -> bytes:
        if url not in seiten:
            raise m.MarktplatzFehler(f"unerwartete Adresse: {url}")
        return seiten[url]
    return laden


# -- Katalog ------------------------------------------------------------------

def test_katalog_wird_gelesen():
    lader = _lader({m.STANDARD_KATALOG: _katalog_bytes([_eintrag()])})
    katalog = m.lade_katalog(lader)
    assert katalog.aktualisiert_am == "2026-08-30"
    assert len(katalog.eintraege) == 1
    assert katalog.eintraege[0].name == "Beispiel"
    assert katalog.eintraege[0].url == BASIS + "lernsets/Englisch/Beispiel.lernset.json"


def test_faecher_behalten_die_reihenfolge_des_katalogs():
    eintraege = [
        _eintrag(ordner="Französisch", name="A"),
        _eintrag(ordner="Englisch", name="B"),
        _eintrag(ordner="Französisch", name="C"),
    ]
    lader = _lader({m.STANDARD_KATALOG: _katalog_bytes(eintraege)})
    assert m.lade_katalog(lader).faecher() == ("Französisch", "Englisch")


def test_neueres_schema_verlangt_eine_neuere_app():
    roh = json.loads(_katalog_bytes([_eintrag()]))
    roh["schema_version"] = 2
    lader = _lader({m.STANDARD_KATALOG: json.dumps(roh).encode("utf-8")})
    with pytest.raises(m.MarktplatzFehler, match="neuere Version"):
        m.lade_katalog(lader)


def test_kaputter_eintrag_macht_die_anderen_nicht_unerreichbar():
    """Ein fehlerhafter Satz wird übersprungen, nicht der ganze Katalog."""
    eintraege = [
        {"name": "Ohne Datei", "ordner": "X", "sha256": "a" * 64},
        _eintrag(name="Heil"),
    ]
    lader = _lader({m.STANDARD_KATALOG: _katalog_bytes(eintraege)})
    katalog = m.lade_katalog(lader)
    assert [e.name for e in katalog.eintraege] == ["Heil"]


def test_leerer_katalog_meldet_sich_verstaendlich():
    lader = _lader({m.STANDARD_KATALOG: _katalog_bytes([])})
    with pytest.raises(m.MarktplatzFehler, match="keine Lernsets"):
        m.lade_katalog(lader)


def test_beschaedigtes_json_wird_nicht_als_absturz_weitergereicht():
    lader = _lader({m.STANDARD_KATALOG: b"{kein json"})
    with pytest.raises(m.MarktplatzFehler, match="beschädigt"):
        m.lade_katalog(lader)


# -- Adressen: alles aus dem Netz ist erst einmal verdächtig -----------------

@pytest.mark.parametrize("datei", [
    "../../../etc/passwd",
    "/absolut/pfad.json",
    "https://beispiel.invalid/boese.json",
    "",
])
def test_unzulaessige_pfade_werden_abgelehnt(datei):
    """Über einen manipulierten Katalog darf keine fremde Adresse kommen."""
    lader = _lader({m.STANDARD_KATALOG: _katalog_bytes([_eintrag(datei=datei)])})
    with pytest.raises(m.MarktplatzFehler):
        m.lade_katalog(lader)


def test_katalog_ohne_https_wird_abgelehnt():
    roh = json.loads(_katalog_bytes([_eintrag()]))
    roh["basis_url"] = "http://raw.githubusercontent.com/x/y/main/"
    lader = _lader({m.STANDARD_KATALOG: json.dumps(roh).encode("utf-8")})
    with pytest.raises(m.MarktplatzFehler, match="HTTPS"):
        m.lade_katalog(lader)


def test_standardlader_verweigert_klartext():
    with pytest.raises(m.MarktplatzFehler, match="HTTPS"):
        m.lade_ueber_netz("http://beispiel.invalid/index.json")


# -- Lernset laden ------------------------------------------------------------

def test_lernset_wird_geladen_und_geprueft():
    inhalt = _lernset_bytes("Headway Unit 4", [{"q": "the house", "a": "das haus"}])
    satz = _eintrag(inhalt=inhalt, name="Headway Unit 4")
    lader = _lader({
        m.STANDARD_KATALOG: _katalog_bytes([satz]),
        BASIS + satz["datei"]: inhalt,
    })
    eintrag = m.lade_katalog(lader).eintraege[0]
    name, items = m.lade_lernset(eintrag, lader)
    assert name == "Headway Unit 4"
    assert items == [{"q": "the house", "a": "das haus"}]


def test_falsche_pruefsumme_verwirft_das_lernset():
    """Der wichtigste Test hier: übernommen wird nur, was angekündigt war."""
    satz = _eintrag()
    lader = _lader({
        m.STANDARD_KATALOG: _katalog_bytes([satz]),
        BASIS + satz["datei"]: _lernset_bytes("Etwas ganz anderes"),
    })
    eintrag = m.lade_katalog(lader).eintraege[0]
    with pytest.raises(m.MarktplatzFehler, match="stimmt nicht"):
        m.lade_lernset(eintrag, lader)


def test_name_kommt_aus_der_datei_nicht_aus_dem_katalog():
    """Massgeblich ist, was im Lernset steht - nicht, was der Katalog behauptet."""
    inhalt = _lernset_bytes("Wahrer Name")
    satz = _eintrag(inhalt=inhalt, name="Katalogname")
    lader = _lader({
        m.STANDARD_KATALOG: _katalog_bytes([satz]),
        BASIS + satz["datei"]: inhalt,
    })
    eintrag = m.lade_katalog(lader).eintraege[0]
    assert eintrag.name == "Katalogname"
    assert m.lade_lernset(eintrag, lader)[0] == "Wahrer Name"


def test_leeres_lernset_wird_abgelehnt():
    inhalt = json.dumps({"schema_version": 1, "typ": "lernset",
                         "name": "Leer", "items": []}).encode("utf-8")
    satz = _eintrag(inhalt=inhalt)
    lader = _lader({
        m.STANDARD_KATALOG: _katalog_bytes([satz]),
        BASIS + satz["datei"]: inhalt,
    })
    eintrag = m.lade_katalog(lader).eintraege[0]
    with pytest.raises(m.MarktplatzFehler):
        m.lade_lernset(eintrag, lader)
