"""Der GitHub-Device-Flow - ohne Netz.

Der Sender wird hereingereicht, das Warten auch. Kein Test schläft wirklich.
"""
from __future__ import annotations

import pytest

from lernapp.netz import github_anmeldung as g

KENNUNG = "Ov23liTESTTESTTEST"


def _sender(antworten: dict[str, list[dict]]):
    """Ein Sender, der je Adresse eine Antwortfolge abarbeitet."""
    verlauf = []

    def senden(url: str, felder: dict) -> dict:
        verlauf.append((url, felder))
        folge = antworten.get(url)
        if not folge:
            raise AssertionError(f"unerwarteter Aufruf: {url}")
        return folge.pop(0) if len(folge) > 1 else folge[0]

    senden.verlauf = verlauf
    return senden


CODE_ANTWORT = {
    "device_code": "abc-device",
    "user_code": "WDJB-MJHT",
    "verification_uri": "https://github.com/login/device",
    "expires_in": 900,
    "interval": 5,
}


# -- Code anfordern -----------------------------------------------------------

def test_geraetecode_wird_gelesen():
    sender = _sender({g.GERAETECODE_URL: [CODE_ANTWORT]})
    code = g.starte_anmeldung(sender, KENNUNG)
    assert code.nutzercode == "WDJB-MJHT"
    assert code.adresse == "https://github.com/login/device"
    assert code.intervall == 5
    assert not code.abgelaufen


def test_der_bereich_ist_public_repo_und_nicht_mehr():
    """`repo` schlösse alle privaten Repos ein - dafür gibt es keinen Grund."""
    sender = _sender({g.GERAETECODE_URL: [CODE_ANTWORT]})
    g.starte_anmeldung(sender, KENNUNG)
    assert sender.verlauf[0][1]["scope"] == "public_repo"


def test_ohne_eingebaute_kennung_gibt_es_eine_verstaendliche_meldung():
    sender = _sender({g.GERAETECODE_URL: [CODE_ANTWORT]})
    with pytest.raises(g.AnmeldungFehler, match="keine GitHub-Kennung"):
        g.starte_anmeldung(sender, "")


def test_abgeschalteter_device_flow_wird_benannt():
    """Der wahrscheinlichste Einrichtungsfehler - das Häkchen fehlt."""
    sender = _sender({g.GERAETECODE_URL: [{"error": "device_flow_disabled"}]})
    with pytest.raises(g.AnmeldungFehler, match="Enable Device Flow"):
        g.starte_anmeldung(sender, KENNUNG)


def test_unvollstaendige_antwort_wird_abgelehnt():
    sender = _sender({g.GERAETECODE_URL: [{"user_code": "X"}]})
    with pytest.raises(g.AnmeldungFehler):
        g.starte_anmeldung(sender, KENNUNG)


# -- Auf die Bestätigung warten ----------------------------------------------

def _code(intervall=5, gueltigkeit=900.0) -> g.Geraetecode:
    import time
    return g.Geraetecode("WDJB-MJHT", "https://github.com/login/device",
                         "abc-device", intervall,
                         time.monotonic() + gueltigkeit)


def test_token_kommt_nach_mehreren_versuchen():
    sender = _sender({g.TOKEN_URL: [
        {"error": "authorization_pending"},
        {"error": "authorization_pending"},
        {"access_token": "gho_geheim"},
    ]})
    geschlafen = []
    token = g.warte_auf_token(_code(), sender, geschlafen.append, KENNUNG)
    assert token == "gho_geheim"
    assert len(geschlafen) == 3


def test_slow_down_verlaengert_den_abstand():
    """Wer die Aufforderung überhört, wird von GitHub gesperrt."""
    sender = _sender({g.TOKEN_URL: [
        {"error": "slow_down"},
        {"access_token": "gho_geheim"},
    ]})
    geschlafen = []
    g.warte_auf_token(_code(intervall=5), sender, geschlafen.append, KENNUNG)
    assert geschlafen == [5, 10]


def test_abgelehnter_zugriff_beendet_das_warten():
    sender = _sender({g.TOKEN_URL: [{"error": "access_denied"}]})
    with pytest.raises(g.AnmeldungFehler, match="abgelehnt"):
        g.warte_auf_token(_code(), sender, lambda _s: None, KENNUNG)


def test_abgelaufener_code_wartet_nicht_ewig():
    sender = _sender({g.TOKEN_URL: [{"error": "authorization_pending"}]})
    with pytest.raises(g.AnmeldungFehler, match="abgelaufen"):
        g.warte_auf_token(_code(gueltigkeit=-1), sender, lambda _s: None, KENNUNG)


def test_abbruch_durch_die_oberflaeche():
    """Ein Abbruch-Knopf muss wirken, ohne dass dieses Modul Qt kennt."""
    sender = _sender({g.TOKEN_URL: [{"error": "authorization_pending"}]})
    with pytest.raises(g.AnmeldungFehler, match="abgebrochen"):
        g.warte_auf_token(_code(), sender, lambda _s: None, KENNUNG,
                          abbruch=lambda: True)


def test_leerer_token_gilt_nicht_als_erfolg():
    sender = _sender({g.TOKEN_URL: [{"access_token": ""}]})
    with pytest.raises(g.AnmeldungFehler):
        g.frage_token(_code(), sender, KENNUNG)


def test_noch_nicht_bestaetigt_ist_kein_fehler():
    sender = _sender({g.TOKEN_URL: [{"error": "authorization_pending"}]})
    with pytest.raises(g.NochNichtBestaetigt):
        g.frage_token(_code(), sender, KENNUNG)


def test_unbekannter_fehler_wird_trotzdem_lesbar():
    sender = _sender({g.TOKEN_URL: [
        {"error": "irgendwas", "error_description": "Etwas ist schiefgelaufen"},
    ]})
    with pytest.raises(g.AnmeldungFehler, match="Etwas ist schiefgelaufen"):
        g.frage_token(_code(), sender, KENNUNG)
