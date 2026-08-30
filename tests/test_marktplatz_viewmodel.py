"""Das Marktplatz-ViewModel - ohne Netz und ohne Thread-Pool.

Der Lader wird hereingereicht und `synchron=True` laesst die Arbeit im
aufrufenden Faden laufen. Sonst muesste jeder Test auf einen Thread warten,
und ein haengender Test waere schlimmer als gar keiner.
"""
import hashlib
import json

import pytest

pytest.importorskip("PySide6", reason="PySide6 nicht installiert - venv nutzen")

from lernapp.gui.bridge.app_state import AppState                          # noqa: E402
from lernapp.gui.bridge.marktplatz_viewmodel import MarktplatzViewModel    # noqa: E402
from lernapp.netz import marktplatz                                        # noqa: E402

BASIS = "https://raw.githubusercontent.com/Larslllllll/Lernapp-lernsets/main/"

DATEN = {"folders": {"Englisch": {"lernsets": [
    {"id": "vorhanden", "name": "Headway Unit 4", "items": [{"q": "a", "a": "b"}]},
]}}}


def _lernset(name, items):
    return json.dumps({"schema_version": 1, "typ": "lernset",
                       "name": name, "items": items}).encode("utf-8")


SETS = {
    "lernsets/Englisch/Headway-Unit-4.lernset.json":
        _lernset("Headway Unit 4", [{"q": "the house", "a": "das haus"}]),
    "lernsets/Latein/Vokabeln.lernset.json":
        _lernset("Vokabeln", [{"q": "domus", "a": "das haus"}]),
}


def _katalog():
    eintraege = []
    for datei, inhalt in SETS.items():
        fach, name = datei.split("/")[1], json.loads(inhalt)["name"]
        eintraege.append({
            "id": f"{fach.lower()}/{name.lower().replace(' ', '-')}",
            "name": name, "ordner": fach, "datei": datei,
            "karten": len(json.loads(inhalt)["items"]),
            "groesse": len(inhalt),
            "sha256": hashlib.sha256(inhalt).hexdigest(),
        })
    return json.dumps({"schema_version": 1, "aktualisiert_am": "2026-08-30",
                       "basis_url": BASIS, "lernsets": eintraege}).encode("utf-8")


@pytest.fixture
def seiten():
    inhalt = {marktplatz.STANDARD_KATALOG: _katalog()}
    inhalt.update({BASIS + pfad: roh for pfad, roh in SETS.items()})
    return inhalt


@pytest.fixture
def vm(tmp_path, seiten):
    (tmp_path / "data.json").write_text(json.dumps(DATEN), encoding="utf-8")

    def lader(url):
        if url not in seiten:
            raise marktplatz.MarktplatzFehler(f"unerwartete Adresse: {url}")
        return seiten[url]

    return MarktplatzViewModel(AppState(tmp_path), lader=lader, synchron=True)


def _id_von(vm, name):
    return next(e["id"] for e in vm.eintraege if e["name"] == name)


def test_vor_dem_laden_ist_die_liste_leer(vm):
    assert vm.eintraege == []
    assert vm.laedt is False


def test_katalog_laden_fuellt_die_liste(vm):
    vm.aktualisieren()
    assert [e["name"] for e in vm.eintraege] == ["Headway Unit 4", "Vokabeln"]
    assert vm.faecher == ["Englisch", "Latein"]
    assert vm.aktualisiertAm == "2026-08-30"
    assert vm.laedt is False


def test_bereits_vorhandene_lernsets_sind_markiert(vm):
    """Sonst laedt jemand dreimal dasselbe herunter."""
    vm.aktualisieren()
    nach_namen = {e["name"]: e["vorhanden"] for e in vm.eintraege}
    assert nach_namen == {"Headway Unit 4": True, "Vokabeln": False}


def test_uebernehmen_legt_das_lernset_an(vm):
    vm.aktualisieren()
    gemeldet = []
    vm.uebernommen.connect(gemeldet.append)

    vm.uebernehmen(_id_von(vm, "Vokabeln"))

    ordner, ls = vm._state.finde_lernset(gemeldet[0])
    assert ordner == "Latein"
    assert ls["name"] == "Vokabeln"
    assert ls["items"] == [{"q": "domus", "a": "das haus"}]


def test_fehlendes_fach_wird_als_ordner_angelegt(vm):
    """Latein gibt es in den Testdaten nicht - der Marktplatz legt ihn an."""
    assert "Latein" not in vm._state.folders
    vm.aktualisieren()
    vm.uebernehmen(_id_von(vm, "Vokabeln"))
    assert "Latein" in vm._state.folders


def test_ordner_wird_nicht_wegen_gross_kleinschreibung_verdoppelt(tmp_path, seiten):
    daten = {"folders": {"latein": {"lernsets": []}}}
    (tmp_path / "data.json").write_text(json.dumps(daten), encoding="utf-8")
    vm = MarktplatzViewModel(AppState(tmp_path),
                             lader=lambda url: seiten[url], synchron=True)
    vm.aktualisieren()
    vm.uebernehmen(_id_von(vm, "Vokabeln"))
    assert list(vm._state.folders) == ["latein"]


def test_uebernommenes_lernset_ueberlebt_den_neustart(vm, tmp_path):
    vm.aktualisieren()
    vm.uebernehmen(_id_von(vm, "Vokabeln"))
    frisch = AppState(tmp_path)
    assert [ls["name"] for _, ls in frisch.alle_lernsets()] == ["Headway Unit 4", "Vokabeln"]


def test_falsche_pruefsumme_legt_nichts_an(tmp_path, seiten):
    """Der Katalog verspricht etwas anderes, als der Server liefert."""
    (tmp_path / "data.json").write_text(json.dumps(DATEN), encoding="utf-8")
    seiten[BASIS + "lernsets/Latein/Vokabeln.lernset.json"] = _lernset(
        "Untergeschoben", [{"q": "x", "a": "y"}])
    vm = MarktplatzViewModel(AppState(tmp_path),
                             lader=lambda url: seiten[url], synchron=True)
    vm.aktualisieren()
    meldungen = []
    vm.fehler.connect(meldungen.append)

    vm.uebernehmen(_id_von(vm, "Vokabeln"))

    assert "stimmt nicht" in meldungen[0]
    assert [ls["name"] for _, ls in vm._state.alle_lernsets()] == ["Headway Unit 4"]
    assert vm.laedt is False


def test_kein_netz_meldet_sich_und_blockiert_nichts(tmp_path):
    """Ein toter Marktplatz darf das Lernen nicht behindern."""
    (tmp_path / "data.json").write_text(json.dumps(DATEN), encoding="utf-8")

    def kaputt(url):
        raise marktplatz.MarktplatzFehler("Keine Verbindung zum Marktplatz.")

    vm = MarktplatzViewModel(AppState(tmp_path), lader=kaputt, synchron=True)
    meldungen = []
    vm.fehler.connect(meldungen.append)

    vm.aktualisieren()

    assert meldungen == ["Keine Verbindung zum Marktplatz."]
    assert vm.eintraege == []
    assert vm.laedt is False
    # Die eigenen Lernsets sind unberuehrt.
    assert [ls["name"] for _, ls in vm._state.alle_lernsets()] == ["Headway Unit 4"]


def test_unbekannte_kennung_meldet_sich(vm):
    vm.aktualisieren()
    meldungen = []
    vm.fehler.connect(meldungen.append)
    vm.uebernehmen("gibt-es-nicht")
    assert "nicht mehr im Verzeichnis" in meldungen[0]


def test_einmalLaden_laedt_nur_beim_ersten_mal(vm):
    aufrufe = []
    echter_lader = vm._lader
    vm._lader = lambda url: (aufrufe.append(url), echter_lader(url))[1]

    vm.einmalLaden()
    vm.einmalLaden()

    assert aufrufe.count(marktplatz.STANDARD_KATALOG) == 1
