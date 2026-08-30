"""Anmeldung bei GitHub über den Device Flow.

Der übliche OAuth-Weg über den Browser braucht ein Client Secret, damit der
Code gegen einen Token getauscht werden kann. Ein Desktop-Programm kann kein
Geheimnis hüten - es steckt in jeder ausgelieferten .exe und ist mit einem
Texteditor zu finden. GitHub unterstützt kein PKCE, mit dem sich das umgehen
liesse.

Der Device Flow löst genau das: die App zeigt einen kurzen Code, der Nutzer
tippt ihn auf github.com/login/device ein, und die App fragt so lange nach,
bis er bestätigt hat. Nötig ist dafür nur die **Client ID**, und die darf
öffentlich sein.

Kennt weder Qt noch die Oberfläche. Wer sendet, wird hereingereicht - deshalb
laufen die Tests ohne Netz.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable

# Aus der OAuth-App unter https://github.com/settings/developers.
# Öffentlich und ungefährlich - im Gegensatz zum Client Secret, das es hier
# bewusst nicht gibt. Ohne Eintrag meldet sich die App verständlich, statt
# gegen GitHub zu laufen und einen kryptischen Fehler zu zeigen.
CLIENT_ID = "Ov23liZ18mucQn6mt8K4"

GERAETECODE_URL = "https://github.com/login/device/code"
TOKEN_URL = "https://github.com/login/oauth/access_token"

# `public_repo` reicht für Fork, Zweig, Datei und Pull Request in einem
# öffentlichen Repo. Bewusst nicht `repo`: das schlösse alle privaten Repos
# des Nutzers mit ein, und dafür gibt es keinen Grund.
BEREICH = "public_repo"

ZEITLIMIT = 20
# GitHub nennt selbst ein Intervall; das hier ist nur die Notbremse, falls die
# Antwort keines enthält.
STANDARDINTERVALL = 5

Sender = Callable[[str, dict], dict]


class AnmeldungFehler(Exception):
    """Fehler, dessen Text direkt dem Nutzer gezeigt werden kann."""


class NochNichtBestaetigt(Exception):
    """Der Nutzer hat den Code noch nicht eingegeben. Kein Fehler."""


@dataclass(frozen=True)
class Geraetecode:
    """Was dem Nutzer gezeigt wird, plus was die App zum Nachfragen braucht."""

    nutzercode: str
    adresse: str
    geraetecode: str
    intervall: int
    gueltig_bis: float

    @property
    def abgelaufen(self) -> bool:
        return time.monotonic() >= self.gueltig_bis


def sende_ueber_netz(url: str, felder: dict) -> dict:
    """Standardsender: POST als Formular, Antwort als JSON."""
    daten = urllib.parse.urlencode(felder).encode("ascii")
    anfrage = urllib.request.Request(
        url, data=daten,
        headers={"Accept": "application/json", "User-Agent": "LernApp"},
    )
    try:
        with urllib.request.urlopen(anfrage, timeout=ZEITLIMIT) as antwort:
            roh = antwort.read(64 * 1024)
    except urllib.error.HTTPError as grund:
        raise AnmeldungFehler(
            f"GitHub antwortet nicht wie erwartet (Fehler {grund.code})."
        ) from grund
    except (urllib.error.URLError, OSError) as grund:
        raise AnmeldungFehler(
            "Keine Verbindung zu GitHub. Internetverbindung prüfen."
        ) from grund
    try:
        antwort = json.loads(roh.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as grund:
        raise AnmeldungFehler("GitHub hat unverständlich geantwortet.") from grund
    if not isinstance(antwort, dict):
        raise AnmeldungFehler("GitHub hat unverständlich geantwortet.")
    return antwort


def _client_id(client_id: str | None) -> str:
    kennung = client_id if client_id is not None else CLIENT_ID
    if not kennung:
        raise AnmeldungFehler(
            "Diese Programmversion hat keine GitHub-Kennung eingebaut. "
            "Veröffentlichen ist damit nicht möglich."
        )
    return kennung


def starte_anmeldung(sender: Sender = sende_ueber_netz,
                     client_id: str | None = None) -> Geraetecode:
    """Code anfordern, den der Nutzer bei GitHub eingibt."""
    antwort = sender(GERAETECODE_URL, {
        "client_id": _client_id(client_id),
        "scope": BEREICH,
    })
    if "error" in antwort:
        raise AnmeldungFehler(_lesbar(antwort))

    for feld in ("device_code", "user_code", "verification_uri"):
        if not antwort.get(feld):
            raise AnmeldungFehler("GitHub hat unverständlich geantwortet.")

    gueltigkeit = int(antwort.get("expires_in", 900) or 900)
    return Geraetecode(
        nutzercode=str(antwort["user_code"]),
        adresse=str(antwort["verification_uri"]),
        geraetecode=str(antwort["device_code"]),
        intervall=max(1, int(antwort.get("interval", STANDARDINTERVALL) or STANDARDINTERVALL)),
        gueltig_bis=time.monotonic() + gueltigkeit,
    )


def frage_token(code: Geraetecode, sender: Sender = sende_ueber_netz,
                client_id: str | None = None) -> str:
    """Einmal nachfragen, ob der Nutzer bestätigt hat.

    Wirft `NochNichtBestaetigt`, solange er noch nicht so weit ist - das ist
    der Normalfall und kein Fehler.
    """
    antwort = sender(TOKEN_URL, {
        "client_id": _client_id(client_id),
        "device_code": code.geraetecode,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
    })

    fehler = antwort.get("error")
    if fehler in ("authorization_pending", "slow_down"):
        raise NochNichtBestaetigt(str(fehler))
    if fehler:
        raise AnmeldungFehler(_lesbar(antwort))

    token = str(antwort.get("access_token", ""))
    if not token:
        raise AnmeldungFehler("GitHub hat keinen Zugang zurückgegeben.")
    return token


def warte_auf_token(code: Geraetecode, sender: Sender = sende_ueber_netz,
                    schlafen: Callable[[float], None] = time.sleep,
                    client_id: str | None = None,
                    abbruch: Callable[[], bool] = lambda: False) -> str:
    """So lange nachfragen, bis der Nutzer bestätigt hat.

    `abbruch` erlaubt es der Oberfläche, den Vorgang abzubrechen, ohne dass
    dieses Modul Qt kennen muss.
    """
    intervall = code.intervall
    while True:
        if abbruch():
            raise AnmeldungFehler("Anmeldung abgebrochen.")
        if code.abgelaufen:
            raise AnmeldungFehler(
                "Der Code ist abgelaufen. Bitte die Anmeldung neu starten."
            )
        schlafen(intervall)
        try:
            return frage_token(code, sender, client_id)
        except NochNichtBestaetigt as stand:
            # `slow_down` ist eine Aufforderung, seltener zu fragen. Wer sie
            # überhört, wird von GitHub gesperrt.
            if str(stand) == "slow_down":
                intervall += 5


def _lesbar(antwort: dict) -> str:
    """GitHubs Fehlerkürzel in einen Satz übersetzen, den man zeigen kann."""
    schluessel = str(antwort.get("error", ""))
    texte = {
        "expired_token": "Der Code ist abgelaufen. Bitte neu anmelden.",
        "access_denied": "Der Zugriff wurde abgelehnt.",
        "incorrect_device_code": "Der Code wurde von GitHub nicht erkannt.",
        "unsupported_grant_type": "GitHub lehnt dieses Anmeldeverfahren ab.",
        "device_flow_disabled":
            "In der GitHub-App ist „Enable Device Flow“ nicht eingeschaltet.",
        "incorrect_client_credentials":
            "Die eingebaute GitHub-Kennung ist ungültig.",
    }
    if schluessel in texte:
        return texte[schluessel]
    beschreibung = str(antwort.get("error_description", "")).strip()
    return beschreibung or f"GitHub meldet: {schluessel or 'unbekannter Fehler'}"
