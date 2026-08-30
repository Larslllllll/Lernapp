"""Zugang zum Sprachmodell zusammensetzen.

Kein Netz. Die lokale Schlüsseldatei wird ausgeblendet - sonst hinge das
Ergebnis davon ab, ob auf diesem Rechner gerade eine liegt.
"""
from __future__ import annotations

import pytest

from lernapp.netz import ki

# Vor dem Ausblenden festhalten: die Fixture unten ersetzt _aus_datei durch
# dict(), und ein Test braucht die echte Fassung.
ECHTES_AUS_DATEI = ki._aus_datei


@pytest.fixture(autouse=True)
def ohne_datei_und_umgebung(monkeypatch):
    monkeypatch.setattr(ki, "_aus_datei", dict)
    for name in ("LERNAPP_KI_BASIS", "LERNAPP_KI_MODELL", "LERNAPP_KI_SCHLUESSEL",
                 "NOUS_API_KEY", "NOUS_MODEL_ID", "NOUS_BASE_URL",
                 "OPENAI_API_KEY", "API_KEY", "MODEL_ID", "MODEL", "BASE_URL",
                 "GEMINI_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def _datei(monkeypatch, **felder):
    monkeypatch.setattr(ki, "_aus_datei", lambda: dict(felder))


def test_ohne_alles_ist_nichts_bereit():
    assert ki.aus_umgebung().bereit is False


def test_anbieter_wird_aus_dem_schluesselnamen_erschlossen(monkeypatch):
    """Wer eine Datei mit NOUS_API_KEY hinlegt, meint Nous - und soll nicht
    zusätzlich eine Basis-Adresse eintragen müssen."""
    _datei(monkeypatch, NOUS_API_KEY="sk-nous-test")
    zugang = ki.aus_umgebung()
    assert zugang.name == "nous"
    assert "nousresearch" in zugang.basis
    assert zugang.modell.endswith(":free")
    assert zugang.bereit is True


def test_anzeigename_statt_kennung_wird_abgefangen(monkeypatch):
    """Aus der Weboberfläche kopiert man "Upstage: Solar Pro 4" - die API
    antwortet darauf mit einem nichtssagenden 404."""
    _datei(monkeypatch, NOUS_API_KEY="sk-nous-test",
           NOUS_MODEL_ID="Upstage: Solar Pro 4")
    zugang = ki.aus_umgebung()
    assert " " not in zugang.modell
    assert zugang.modell == ki.ANBIETER["nous"][1]


def test_eine_echte_kennung_bleibt_stehen(monkeypatch):
    _datei(monkeypatch, NOUS_API_KEY="sk-nous-test",
           NOUS_MODEL_ID="upstage/solar-pro4")
    assert ki.aus_umgebung().modell == "upstage/solar-pro4"


def test_umgebung_schlaegt_datei(monkeypatch):
    _datei(monkeypatch, NOUS_API_KEY="aus-datei")
    monkeypatch.setenv("LERNAPP_KI_SCHLUESSEL", "aus-umgebung")
    assert ki.aus_umgebung().schluessel == "aus-umgebung"


def test_ausdruecklicher_anbieter_setzt_basis_und_modell(monkeypatch):
    _datei(monkeypatch, LERNAPP_KI_SCHLUESSEL="egal")
    zugang = ki.aus_umgebung("gemini")
    assert "googleapis" in zugang.basis
    assert zugang.modell.startswith("gemini")


def test_je_anbieter_ein_eigener_schluessel(monkeypatch):
    """Damit sich zwei Anbieter vergleichen lassen, ohne umzusetzen."""
    monkeypatch.setenv("LERNAPP_KI_SCHLUESSEL_GEMINI", "gemini-schluessel")
    monkeypatch.setenv("LERNAPP_KI_SCHLUESSEL", "allgemein")
    assert ki.aus_umgebung("gemini").schluessel == "gemini-schluessel"
    assert ki.aus_umgebung("groq").schluessel == "allgemein"


def test_ohne_zugang_wird_gar_nicht_erst_gefragt():
    with pytest.raises(ki.KIFehler, match="Kein Zugang"):
        ki.frage(ki.Zugang("", "", ""), "system", "auftrag")


def test_kommentare_und_anfuehrungszeichen_in_der_datei(monkeypatch, tmp_path):
    datei = tmp_path / ".NOUS.ENV"
    datei.write_text('# Kommentar\nNOUS_API_KEY="sk-nous-x"\n\nNOUS_MODEL_ID=a/b\n',
                     encoding="utf-8")
    gefunden = ECHTES_AUS_DATEI(tmp_path)
    assert gefunden["NOUS_API_KEY"] == "sk-nous-x"
    assert gefunden["NOUS_MODEL_ID"] == "a/b"
