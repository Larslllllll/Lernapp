"""Der Weg zum Modell - direkt oder über den Vermittler.

Ohne Netz. Geprüft wird vor allem die Weiche: mit eigenem Schlüssel direkt,
ohne über den Dienst, und ohne beides eine verständliche Meldung statt eines
Absturzes.
"""
from __future__ import annotations

import json
import urllib.error

import pytest

from lernapp.netz import ki, vokabel_dienst as vd
from lernapp.netz.ki import KIFehler, Zugang


@pytest.fixture(autouse=True)
def ohne_zugang(monkeypatch):
    """Standard: kein eigener Schlüssel, kein Dienst."""
    monkeypatch.setattr(ki, "_aus_datei", dict)
    monkeypatch.setattr(vd, "aus_umgebung", lambda: Zugang("", "", ""))
    monkeypatch.setattr(vd, "DIENST_URL", "")


# -- Gerätekennung ------------------------------------------------------------

def test_geraetekennung_wird_einmal_erzeugt_und_behalten(tmp_path):
    erste = vd.geraetekennung(tmp_path)
    assert len(erste) >= 8
    assert vd.geraetekennung(tmp_path) == erste


def test_geraetekennung_liegt_im_datenverzeichnis(tmp_path):
    kennung = vd.geraetekennung(tmp_path)
    assert (tmp_path / vd.GERAET_DATEI).read_text(encoding="utf-8").strip() == kennung


def test_ohne_schreibrecht_geht_es_trotzdem(tmp_path, monkeypatch):
    """Eine fehlende Datei darf den Import nicht scheitern lassen."""
    def kein_schreiben(*a, **k):
        raise OSError("kein Platz")

    monkeypatch.setattr(vd.Path, "write_text", kein_schreiben)
    assert len(vd.geraetekennung(tmp_path)) >= 8


# -- Die Weiche ---------------------------------------------------------------

def test_ohne_alles_gibt_es_eine_verstaendliche_meldung(tmp_path):
    assert vd.verfuegbar() is False
    with pytest.raises(KIFehler, match="von Hand"):
        vd.erkenne("irgendein Text", tmp_path)


def test_mit_eigenem_schluessel_wird_direkt_gefragt(tmp_path, monkeypatch):
    """Lars' Rechner: kein Umweg über den Vermittler, kein Deckel."""
    monkeypatch.setattr(vd, "aus_umgebung",
                        lambda: Zugang("https://x/v1", "modell", "geheim"))
    gerufen = {}

    def direkt(zugang, text):
        gerufen["text"] = text
        return vd.Vorschlag(["la maison;das Haus"])

    monkeypatch.setattr(vd, "direkt_erkennen", direkt)
    monkeypatch.setattr(vd, "DIENST_URL", "https://dienst.invalid")

    ergebnis = vd.erkenne("Seitentext", tmp_path)
    assert ergebnis.zeilen == ["la maison;das Haus"]
    assert gerufen["text"] == "Seitentext"


def test_ohne_schluessel_geht_es_ueber_den_dienst(tmp_path, monkeypatch):
    monkeypatch.setattr(vd, "DIENST_URL", "https://dienst.invalid")
    gesendet = {}

    class Antwort:
        def read(self):
            return json.dumps({"text": "la maison;das Haus", "verbleibend": 19}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def falsches_oeffnen(anfrage, timeout=0):
        gesendet["url"] = anfrage.full_url
        gesendet["koerper"] = json.loads(anfrage.data.decode())
        return Antwort()

    monkeypatch.setattr(vd.urllib.request, "urlopen", falsches_oeffnen)

    ergebnis = vd.erkenne("Seitentext", tmp_path)
    assert ergebnis.zeilen == ["la maison;das Haus"]
    assert gesendet["url"].endswith("/vokabeln")
    assert gesendet["koerper"]["text"] == "Seitentext"
    assert len(gesendet["koerper"]["geraet"]) >= 8


def test_der_dienst_schickt_seinen_eigenen_meldungstext(tmp_path, monkeypatch):
    """Bei einem Deckel soll der Nutzer den Satz des Dienstes sehen,
    nicht "Fehler 429"."""
    monkeypatch.setattr(vd, "DIENST_URL", "https://dienst.invalid")

    class Abgelehnt(urllib.error.HTTPError):
        def __init__(self):
            super().__init__("u", 429, "Too Many", {}, None)

        def read(self):
            return json.dumps({"fehler": "Du hast heute schon 20 Seiten eingelesen."}).encode()

    def wirft(*a, **k):
        raise Abgelehnt()

    monkeypatch.setattr(vd.urllib.request, "urlopen", wirft)
    with pytest.raises(KIFehler, match="20 Seiten"):
        vd.erkenne("Seitentext", tmp_path)


def test_dienst_nicht_erreichbar(tmp_path, monkeypatch):
    monkeypatch.setattr(vd, "DIENST_URL", "https://dienst.invalid")

    def wirft(*a, **k):
        raise urllib.error.URLError("kein Netz")

    monkeypatch.setattr(vd.urllib.request, "urlopen", wirft)
    with pytest.raises(KIFehler, match="nicht erreichbar"):
        vd.erkenne("Seitentext", tmp_path)


def test_antwort_des_dienstes_wird_ebenso_gesiebt(tmp_path, monkeypatch):
    """Auch über den Dienst plaudert das Modell - dieselbe Siebung greift."""
    monkeypatch.setattr(vd, "DIENST_URL", "https://dienst.invalid")

    class Antwort:
        def read(self):
            return json.dumps(
                {"text": "Hier sind die Vokabeln:\nla maison;das Haus"}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(vd.urllib.request, "urlopen", lambda *a, **k: Antwort())
    ergebnis = vd.erkenne("x", tmp_path)
    assert ergebnis.zeilen == ["la maison;das Haus"]


def test_leere_antwort_des_dienstes(tmp_path, monkeypatch):
    monkeypatch.setattr(vd, "DIENST_URL", "https://dienst.invalid")

    class Antwort:
        def read(self):
            return json.dumps({"text": "Nichts gefunden."}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(vd.urllib.request, "urlopen", lambda *a, **k: Antwort())
    with pytest.raises(KIFehler, match="keine Vokabelpaare"):
        vd.erkenne("x", tmp_path)


def test_verfuegbar_sobald_es_einen_dienst_gibt(monkeypatch):
    monkeypatch.setattr(vd, "DIENST_URL", "https://dienst.invalid")
    assert vd.verfuegbar() is True
