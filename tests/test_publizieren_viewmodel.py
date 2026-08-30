"""Das ViewModel zum Einreichen - ohne Netz, ohne Thread-Pool, ohne DPAPI."""
from __future__ import annotations

import json

import pytest

pytest.importorskip("PySide6", reason="PySide6 nicht installiert - venv nutzen")

from lernapp.gui.bridge.app_state import AppState                            # noqa: E402
from lernapp.gui.bridge.publizieren_viewmodel import PublizierenViewModel    # noqa: E402
from lernapp.netz import github_anmeldung as anmeldung                       # noqa: E402
from lernapp.netz import github_publizieren as publizieren                   # noqa: E402

DATEN = {"folders": {
    "Französisch": {"lernsets": [
        {"id": "gut", "name": "Unité 4", "items": [{"q": "la maison", "a": "das haus"}]},
        {"id": "boese", "name": "Test", "items": [{"q": "nigger", "a": "x"}]},
        {"id": "leer", "name": "Leer", "items": []},
    ]},
}}


class GefaelschtePlattform:
    """Merkt sich Geheimnisse im Speicher statt in DPAPI."""

    def __init__(self, vorhanden=None, kann_speichern=True):
        self.tresor = dict(vorhanden or {})
        self.kann_speichern = kann_speichern

    def lies_geheimnis(self, name):
        return self.tresor.get(name)

    def speichere_geheimnis(self, name, wert):
        if not self.kann_speichern:
            return False
        self.tresor[name] = wert
        return True

    def loesche_geheimnis(self, name):
        self.tresor.pop(name, None)


@pytest.fixture
def basis(tmp_path):
    (tmp_path / "data.json").write_text(json.dumps(DATEN), encoding="utf-8")
    return tmp_path


def _vm(basis, plattform=None):
    return PublizierenViewModel(AppState(basis),
                                plattform=plattform or GefaelschtePlattform(),
                                synchron=True)


# -- Schritt 1: prüfen --------------------------------------------------------

def test_sauberes_lernset_wird_durchgelassen(basis):
    antwort = _vm(basis).pruefe("gut")
    assert antwort["ok"] is True
    assert antwort["name"] == "Unité 4"
    assert antwort["fach"] == "Französisch"
    assert antwort["karten"] == 1


def test_gesperrtes_lernset_faellt_schon_hier_durch(basis):
    """Ohne Netz und vor dem Anmelden - sonst erfährt man erst nach der
    Anmeldung, dass es ohnehin nicht geht."""
    antwort = _vm(basis).pruefe("boese")
    assert antwort["ok"] is False
    assert "Karte 1, Frage" in antwort["grund"]
    assert "nigger" not in antwort["grund"].lower()


def test_leeres_lernset_wird_abgelehnt(basis):
    assert _vm(basis).pruefe("leer")["ok"] is False


def test_verschwundenes_lernset_wird_abgelehnt(basis):
    assert _vm(basis).pruefe("gibtsnicht")["ok"] is False


# -- Schritt 2: anmelden ------------------------------------------------------

def test_gespeicherter_zugang_gilt_als_angemeldet(basis):
    vm = _vm(basis, GefaelschtePlattform({"github": "gho_alt"}))
    assert vm.angemeldet is True


def test_ohne_zugang_ist_man_nicht_angemeldet(basis):
    assert _vm(basis).angemeldet is False


def test_anmeldung_zeigt_den_code_und_speichert_den_zugang(basis, monkeypatch):
    plattform = GefaelschtePlattform()
    vm = _vm(basis, plattform)
    gesehen = []
    vm.codeBereit.connect(lambda: gesehen.append(vm.nutzercode))

    monkeypatch.setattr(anmeldung, "starte_anmeldung", lambda: anmeldung.Geraetecode(
        "WDJB-MJHT", "https://github.com/login/device", "dev", 5, 1e12))
    monkeypatch.setattr(anmeldung, "warte_auf_token", lambda code: "gho_neu")

    vm.anmelden()

    assert gesehen == ["WDJB-MJHT"]
    assert vm.angemeldet is True
    assert plattform.tresor["github"] == "gho_neu"
    assert vm.nutzercode == ""      # nach dem Erfolg wieder weg
    assert vm.laeuft is False


def test_ohne_sichere_ablage_gilt_die_anmeldung_nur_fuer_die_sitzung(basis, monkeypatch):
    plattform = GefaelschtePlattform(kann_speichern=False)
    vm = _vm(basis, plattform)
    meldungen = []
    vm.hinweis.connect(meldungen.append)

    monkeypatch.setattr(anmeldung, "starte_anmeldung", lambda: anmeldung.Geraetecode(
        "WDJB-MJHT", "https://github.com/login/device", "dev", 5, 1e12))
    monkeypatch.setattr(anmeldung, "warte_auf_token", lambda code: "gho_neu")

    vm.anmelden()
    assert vm.angemeldet is True
    assert "nur für diese Sitzung" in meldungen[-1]


def test_abmelden_vergisst_den_zugang(basis):
    plattform = GefaelschtePlattform({"github": "gho_alt"})
    vm = _vm(basis, plattform)
    vm.abmelden()
    assert vm.angemeldet is False
    assert "github" not in plattform.tresor


# -- Schritt 3: einreichen ----------------------------------------------------

def test_einreichen_meldet_die_adresse_des_antrags(basis, monkeypatch):
    vm = _vm(basis, GefaelschtePlattform({"github": "gho_alt"}))
    gesehen = []
    vm.fertig.connect(gesehen.append)

    gerufen = {}

    def gefaelscht(token, name, items, fach, app_version="", **rest):
        gerufen.update(token=token, name=name, fach=fach, karten=len(items))
        return publizieren.Ergebnis("https://github.com/x/y/pull/9", "zweig", False)

    monkeypatch.setattr(publizieren, "veroeffentliche", gefaelscht)
    vm.reicheEin("gut")

    assert gerufen == {"token": "gho_alt", "name": "Unité 4",
                       "fach": "Französisch", "karten": 1}
    assert gesehen == ["https://github.com/x/y/pull/9"]
    assert vm.ergebnis.endswith("/pull/9")
    assert vm.laeuft is False


def test_ohne_anmeldung_wird_nichts_gesendet(basis, monkeypatch):
    vm = _vm(basis)
    meldungen = []
    vm.fehler.connect(meldungen.append)

    def darf_nicht(*args, **rest):
        raise AssertionError("es wurde trotzdem gesendet")

    monkeypatch.setattr(publizieren, "veroeffentliche", darf_nicht)
    vm.reicheEin("gut")
    assert "anmelden" in meldungen[0]


def test_abgelaufene_anmeldung_wird_weggeworfen(basis, monkeypatch):
    """Sonst scheitert jeder weitere Versuch sofort wieder."""
    plattform = GefaelschtePlattform({"github": "gho_alt"})
    vm = _vm(basis, plattform)

    def abgelaufen(*args, **rest):
        raise publizieren.PublizierenFehler(
            "Die Anmeldung bei GitHub gilt nicht mehr. Bitte neu anmelden.")

    monkeypatch.setattr(publizieren, "veroeffentliche", abgelaufen)
    vm.reicheEin("gut")

    assert vm.angemeldet is False
    assert "github" not in plattform.tresor


def test_ein_fehler_beim_einreichen_haelt_nichts_fest(basis, monkeypatch):
    vm = _vm(basis, GefaelschtePlattform({"github": "gho_alt"}))
    meldungen = []
    vm.fehler.connect(meldungen.append)

    def kaputt(*args, **rest):
        raise publizieren.PublizierenFehler("Keine Verbindung zu GitHub.")

    monkeypatch.setattr(publizieren, "veroeffentliche", kaputt)
    vm.reicheEin("gut")

    assert meldungen == ["Keine Verbindung zu GitHub."]
    assert vm.laeuft is False
    assert vm.angemeldet is True    # der Zugang bleibt, er war ja nicht schuld
