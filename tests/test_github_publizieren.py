"""Einreichen im Marktplatz - ohne Netz und ohne GitHub-Konto.

Die API wird hereingereicht. Ein gefälschter GitHub merkt sich jeden Aufruf,
damit die Tests nicht nur das Ergebnis prüfen, sondern auch den Weg dorthin -
gerade beim wichtigsten Punkt: dass vor der Sperrliste kein einziges Byte
nach aussen geht.
"""
from __future__ import annotations

import base64
import json

import pytest

from lernapp.netz import github_publizieren as p

KONTO = "MitschuelerIn"
BASIS_SHA = "a" * 40
KARTEN = [{"q": "la maison", "a": "das haus"}]


class GefaelschterGitHub:
    """Antwortet auf die Aufrufe, die der Ablauf wirklich macht."""

    def __init__(self, fork_da=True, zweig_da=False, datei_da=False,
                 pr_offen=False, forks_nach=0):
        self.aufrufe: list[tuple[str, str, dict | None]] = []
        self.fork_da = fork_da
        self.zweig_da = zweig_da
        self.datei_da = datei_da
        self.pr_offen = pr_offen
        self.forks_nach = forks_nach     # so viele 404 nach dem Fork-Auftrag
        self.fork_beantragt = False

    def __call__(self, methode: str, pfad: str, daten: dict | None, token: str):
        self.aufrufe.append((methode, pfad, daten))

        if pfad == "/user":
            return {"login": KONTO}

        if pfad == f"/repos/{KONTO}/{p.ZIEL_REPO}":
            if self.fork_da:
                return {"full_name": f"{KONTO}/{p.ZIEL_REPO}"}
            if self.fork_beantragt:
                if self.forks_nach > 0:
                    self.forks_nach -= 1
                    raise p.NichtGefunden("noch nicht da")
                return {"full_name": f"{KONTO}/{p.ZIEL_REPO}"}
            raise p.NichtGefunden("kein Fork")

        if pfad.endswith("/forks"):
            self.fork_beantragt = True
            return {}

        if pfad.endswith(f"/git/ref/heads/{p.ZIEL_ZWEIG}"):
            return {"object": {"sha": BASIS_SHA}}

        if methode == "POST" and pfad.endswith("/git/refs"):
            if self.zweig_da:
                raise p.PublizierenFehler("Zweig existiert bereits")
            return {}

        if methode == "PATCH" and "/git/refs/heads/" in pfad:
            return {}

        if methode == "GET" and "/contents/" in pfad:
            if self.datei_da:
                return {"sha": "b" * 40}
            raise p.NichtGefunden("keine Datei")

        if methode == "PUT" and "/contents/" in pfad:
            return {"commit": {"sha": "c" * 40}}

        if methode == "POST" and pfad.endswith("/pulls"):
            if self.pr_offen:
                raise p.PublizierenFehler("A pull request already exists")
            return {"html_url": "https://github.com/Larslllllll/Lernapp-lernsets/pull/7"}

        if methode == "GET" and "/pulls?" in pfad:
            return ([{"html_url": "https://github.com/Larslllllll/Lernapp-lernsets/pull/3"}]
                    if self.pr_offen else [])

        raise AssertionError(f"unerwarteter Aufruf: {methode} {pfad}")

    def mit(self, methode: str, teil: str) -> list[dict | None]:
        return [d for m, pf, d in self.aufrufe if m == methode and teil in pf]


# Eigener Platzhalter statt None: `items or KARTEN` würde aus der leeren
# Liste die Standardkarten machen - und damit genau den Test entwerten, der
# prüft, dass ein leeres Lernset abgelehnt wird.
OHNE_ANGABE = object()


def _publiziere(gh, name="4. Québec", items=OHNE_ANGABE, fach="Französisch"):
    return p.veroeffentliche("gho_test", name,
                             KARTEN if items is OHNE_ANGABE else items, fach,
                             app_version="0.9.2", aufruf=gh,
                             schlafen=lambda _s: None)


# -- Die Sperrliste kommt vor allem anderen -----------------------------------

def test_gesperrtes_lernset_sendet_kein_einziges_byte():
    """Der wichtigste Test der Datei.

    Was einmal in einem öffentlichen Pull Request stand, steht in der
    Historie - auch wenn er abgelehnt wird.
    """
    gh = GefaelschterGitHub()
    with pytest.raises(p.Gesperrt):
        _publiziere(gh, items=[{"q": "nigger", "a": "test"}])
    assert gh.aufrufe == []


def test_gesperrter_name_sendet_ebenfalls_nichts():
    gh = GefaelschterGitHub()
    with pytest.raises(p.Gesperrt):
        _publiziere(gh, name="faggot Vokabeln")
    assert gh.aufrufe == []


def test_die_meldung_nennt_die_stelle():
    gh = GefaelschterGitHub()
    with pytest.raises(p.Gesperrt, match="Karte 1, Frage"):
        _publiziere(gh, items=[{"q": "nigger", "a": "test"}])


# -- Der übliche Weg ----------------------------------------------------------

def test_pull_request_wird_aufgemacht():
    gh = GefaelschterGitHub()
    ergebnis = _publiziere(gh)
    assert ergebnis.adresse.endswith("/pull/7")
    assert ergebnis.aktualisiert is False


def test_zweig_haengt_am_stand_des_echten_repos_nicht_am_fork():
    """Ein alter Fork wäre Tage hinterher, und der Pull Request enthielte
    plötzlich fremde Rücknahmen."""
    gh = GefaelschterGitHub()
    _publiziere(gh)
    gelesen = [pf for m, pf, _ in gh.aufrufe if "git/ref/heads" in pf and m == "GET"]
    assert gelesen == [f"/repos/{p.ZIEL_BESITZER}/{p.ZIEL_REPO}/git/ref/heads/main"]
    assert gh.mit("POST", "/git/refs")[0]["sha"] == BASIS_SHA


def test_pfad_und_zweig_kommen_ohne_umlaute_aus():
    gh = GefaelschterGitHub()
    _publiziere(gh)
    pfade = [pf for m, pf, _ in gh.aufrufe if m == "PUT"]
    assert pfade == [f"/repos/{KONTO}/{p.ZIEL_REPO}/contents/"
                     f"lernsets/Franzoesisch/4-Quebec.lernset.json"]
    assert gh.mit("POST", "/git/refs")[0]["ref"] == "refs/heads/lernset/franzoesisch-4-quebec"


def test_der_anzeigename_behaelt_seine_umlaute():
    """Nur der Pfad wird entschärft, nicht der Inhalt."""
    gh = GefaelschterGitHub()
    _publiziere(gh)
    roh = base64.b64decode(gh.mit("PUT", "/contents/")[0]["content"])
    assert json.loads(roh)["name"] == "4. Québec"


def test_inhalt_ist_ein_gueltiges_lernset_mit_lf():
    gh = GefaelschterGitHub()
    _publiziere(gh)
    roh = base64.b64decode(gh.mit("PUT", "/contents/")[0]["content"])
    assert b"\r\n" not in roh, "CRLF macht die Prüfsummen im Index wertlos"
    assert roh.endswith(b"\n")
    daten = json.loads(roh)
    assert daten["typ"] == "lernset"
    assert daten["schema_version"] == 1
    assert daten["items"] == KARTEN
    assert daten["app_version"] == "0.9.2"


def test_der_pull_request_beschreibt_was_drin_ist():
    gh = GefaelschterGitHub()
    _publiziere(gh)
    antrag = gh.mit("POST", "/pulls")[0]
    assert antrag["head"] == f"{KONTO}:lernset/franzoesisch-4-quebec"
    assert antrag["base"] == "main"
    assert "4. Québec" in antrag["title"]
    assert "Französisch" in antrag["body"]


# -- Fork ---------------------------------------------------------------------

def test_fehlender_fork_wird_angelegt():
    gh = GefaelschterGitHub(fork_da=False)
    _publiziere(gh)
    assert gh.mit("POST", "/forks")


def test_auf_den_frischen_fork_wird_gewartet():
    """GitHub antwortet, bevor der Fork benutzbar ist."""
    gh = GefaelschterGitHub(fork_da=False, forks_nach=3)
    _publiziere(gh)
    versuche = [pf for m, pf, _ in gh.aufrufe
                if m == "GET" and pf == f"/repos/{KONTO}/{p.ZIEL_REPO}"]
    assert len(versuche) == 5      # einmal vorher, dann 3 Fehlschläge, dann Erfolg


def test_ein_fork_der_nie_auftaucht_meldet_sich_verstaendlich():
    gh = GefaelschterGitHub(fork_da=False, forks_nach=99)
    with pytest.raises(p.PublizierenFehler, match="ungewöhnlich lange"):
        _publiziere(gh)


# -- Zweite Einreichung desselben Lernsets ------------------------------------

def test_vorhandener_zweig_wird_auf_den_aktuellen_stand_gesetzt():
    gh = GefaelschterGitHub(zweig_da=True)
    _publiziere(gh)
    patch = gh.mit("PATCH", "/git/refs/heads/")
    assert patch and patch[0] == {"sha": BASIS_SHA, "force": True}


def test_vorhandene_datei_wird_ersetzt_statt_zu_scheitern():
    gh = GefaelschterGitHub(datei_da=True)
    ergebnis = _publiziere(gh)
    assert gh.mit("PUT", "/contents/")[0]["sha"] == "b" * 40
    assert ergebnis.aktualisiert is True
    assert "Aktualisiert" in gh.mit("POST", "/pulls")[0]["title"]


def test_offener_pull_request_wird_zurueckgemeldet_statt_zu_scheitern():
    """Die neue Fassung hängt bereits am offenen Antrag."""
    gh = GefaelschterGitHub(pr_offen=True)
    ergebnis = _publiziere(gh)
    assert ergebnis.adresse.endswith("/pull/3")


# -- Vorbedingungen -----------------------------------------------------------

@pytest.mark.parametrize("name,items,fach", [
    ("", KARTEN, "Englisch"),
    ("Test", [], "Englisch"),
    ("Test", KARTEN, ""),
])
def test_unvollstaendige_angaben_werden_abgelehnt(name, items, fach):
    gh = GefaelschterGitHub()
    with pytest.raises(p.PublizierenFehler):
        _publiziere(gh, name=name, items=items, fach=fach)


def test_ohne_erkennbares_konto_geht_nichts():
    def kein_konto(methode, pfad, daten, token):
        return {}
    with pytest.raises(p.PublizierenFehler, match="wer angemeldet ist"):
        p.veroeffentliche("gho_test", "Test", KARTEN, "Englisch",
                          aufruf=kein_konto, schlafen=lambda _s: None)


def test_abgelaufene_anmeldung_wird_benannt():
    import urllib.error
    fehler = p._http_fehler(urllib.error.HTTPError("u", 401, "", {}, None))
    assert "neu anmelden" in str(fehler)
