"""Ein Lernset im Marktplatz einreichen.

Der Weg ist der, den Open Source überall benutzt: Das Repo wird in das Konto
des Nutzers geforkt, dort ein Zweig angelegt, die Datei geschrieben und ein
Pull Request aufgemacht. Freigeben muss Lars - der offizielle Marktplatz
bleibt kuratiert, und der Beitrag steht unter dem Namen des Beitragenden.

Kennt weder Qt noch die Oberfläche. Wer sendet, wird hereingereicht - deshalb
laufen die Tests ohne Netz und ohne GitHub-Konto.

Reihenfolge ist Absicht: **erst die Sperrliste, dann das erste Byte nach
aussen.** Was einmal in einem öffentlichen Pull Request stand, steht in der
Historie, auch wenn er abgelehnt wird.
"""
from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable

from lernapp.core import wortfilter
from lernapp.core.import_export import als_export

ZIEL_BESITZER = "Larslllllll"
ZIEL_REPO = "Lernapp-lernsets"
ZIEL_ZWEIG = "main"

API = "https://api.github.com"
ZEITLIMIT = 30

# Ein Fork entsteht bei GitHub nicht sofort - die Antwort kommt, bevor das
# Repo benutzbar ist. Ohne Warten scheitert der nächste Aufruf mit 404.
FORK_VERSUCHE = 10
FORK_ABSTAND = 3

UMLAUTE = {
    "ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss",
    "é": "e", "è": "e", "ê": "e", "ë": "e", "à": "a", "â": "a", "á": "a",
    "ç": "c", "î": "i", "ï": "i", "í": "i", "ô": "o", "ó": "o", "õ": "o",
    "û": "u", "ù": "u", "ú": "u", "ñ": "n",
}


class PublizierenFehler(Exception):
    """Fehler, dessen Text direkt dem Nutzer gezeigt werden kann."""


class Gesperrt(PublizierenFehler):
    """Die Sperrliste hat angeschlagen. Nichts wurde gesendet."""


@dataclass(frozen=True)
class Ergebnis:
    adresse: str
    zweig: str
    aktualisiert: bool


# Die API liefert je nach Endpunkt ein Objekt oder eine Liste.
Aufruf = Callable[[str, str, "dict | None", str], "dict | list"]


def rufe_api(methode: str, pfad: str, daten: dict | None,
             token: str) -> dict | list:
    """Standardaufruf gegen die GitHub-API."""
    roh = json.dumps(daten).encode("utf-8") if daten is not None else None
    anfrage = urllib.request.Request(
        pfad if pfad.startswith("https://") else API + pfad,
        data=roh, method=methode,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "LernApp",
        },
    )
    try:
        with urllib.request.urlopen(anfrage, timeout=ZEITLIMIT) as antwort:
            inhalt = antwort.read()
    except urllib.error.HTTPError as grund:
        raise _http_fehler(grund) from grund
    except (urllib.error.URLError, OSError) as grund:
        raise PublizierenFehler(
            "Keine Verbindung zu GitHub. Internetverbindung prüfen."
        ) from grund
    if not inhalt:
        return {}
    try:
        return json.loads(inhalt.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}


class NichtGefunden(PublizierenFehler):
    """404 - für den Ablauf oft eine normale Auskunft, kein Fehler."""


def _http_fehler(grund: urllib.error.HTTPError) -> PublizierenFehler:
    if grund.code == 404:
        return NichtGefunden("Nicht gefunden.")
    if grund.code == 401:
        return PublizierenFehler(
            "Die Anmeldung bei GitHub gilt nicht mehr. Bitte neu anmelden."
        )
    if grund.code == 403:
        return PublizierenFehler(
            "GitHub verweigert den Zugriff. Vielleicht wurde die Erlaubnis "
            "entzogen, oder es waren zu viele Anfragen in kurzer Zeit."
        )
    return PublizierenFehler(f"GitHub antwortet mit Fehler {grund.code}.")


def ascii_pfad(text: str) -> str:
    """Dateiname ohne Sonderzeichen.

    Roh-URLs mit Umlaut müssten prozentkodiert werden und überleben keinen
    Kopiervorgang durch einen Chat. Der Anzeigename im Lernset bleibt
    unverändert - nur der Pfad wird entschärft.
    """
    for zeichen, ersatz in UMLAUTE.items():
        text = text.replace(zeichen, ersatz)
    sauber = "".join(z if (z.isalnum() and z.isascii()) or z in "-_" else "-"
                     for z in text)
    while "--" in sauber:
        sauber = sauber.replace("--", "-")
    return sauber.strip("-") or "Unbenannt"


def _inhalt(name: str, items: list[dict], app_version: str) -> bytes:
    """Die Datei, wie sie im Repo liegen soll.

    Mit LF und abschliessendem Zeilenumbruch - das Lernset-Repo nagelt
    Zeilenenden auf LF fest, weil sonst die Prüfsummen im Index für eine
    Fassung gelten, die niemand herunterlädt.
    """
    text = json.dumps(als_export(name, items, app_version),
                      ensure_ascii=False, indent=2) + "\n"
    return text.replace("\r\n", "\n").encode("utf-8")


def veroeffentliche(token: str, name: str, items: list[dict], fach: str,
                    app_version: str = "", aufruf: Aufruf = rufe_api,
                    schlafen: Callable[[float], None] = time.sleep) -> Ergebnis:
    """Lernset einreichen. Gibt die Adresse des Pull Requests zurück."""
    # 1. Sperrliste. Vor allem anderen - danach ist es öffentlich.
    treffer = wortfilter.pruefe_lernset(name, items)
    if treffer:
        raise Gesperrt(wortfilter.meldung(treffer))

    name = (name or "").strip()
    fach = (fach or "").strip()
    if not name or not items:
        raise PublizierenFehler("Ein Lernset braucht einen Namen und Karten.")
    if not fach:
        raise PublizierenFehler("Ein Lernset braucht ein Fach.")

    nutzer = aufruf("GET", "/user", None, token)
    konto = str(nutzer.get("login", "")) if isinstance(nutzer, dict) else ""
    if not konto:
        raise PublizierenFehler("GitHub verrät nicht, wer angemeldet ist.")

    _stelle_fork_sicher(konto, token, aufruf, schlafen)

    # Der Zweig zeigt auf den aktuellen Stand des ECHTEN Repos, nicht auf den
    # des Forks: ein alter Fork wäre sonst Tage hinterher, und der Pull
    # Request enthielte auf einmal fremde Rücknahmen. Forks teilen sich den
    # Objektspeicher, deshalb kennt der Fork diesen Commit bereits.
    stand = aufruf("GET", f"/repos/{ZIEL_BESITZER}/{ZIEL_REPO}/git/ref/heads/{ZIEL_ZWEIG}",
                   None, token)
    basis = str(stand.get("object", {}).get("sha", "")) if isinstance(stand, dict) else ""
    if not basis:
        raise PublizierenFehler("Der Marktplatz gibt seinen Stand nicht preis.")

    zweig = f"lernset/{ascii_pfad(fach).lower()}-{ascii_pfad(name).lower()}"
    _lege_zweig_an(konto, zweig, basis, token, aufruf)

    pfad = f"lernsets/{ascii_pfad(fach)}/{ascii_pfad(name)}.lernset.json"
    aktualisiert = _schreibe_datei(konto, zweig, pfad, name, items,
                                   app_version, token, aufruf)

    return _oeffne_pull_request(konto, zweig, name, fach, len(items),
                                aktualisiert, token, aufruf)


def _stelle_fork_sicher(konto: str, token: str, aufruf: Aufruf,
                        schlafen: Callable[[float], None]) -> None:
    try:
        aufruf("GET", f"/repos/{konto}/{ZIEL_REPO}", None, token)
        return
    except NichtGefunden:
        pass

    aufruf("POST", f"/repos/{ZIEL_BESITZER}/{ZIEL_REPO}/forks", {}, token)
    for versuch in range(FORK_VERSUCHE):
        try:
            aufruf("GET", f"/repos/{konto}/{ZIEL_REPO}", None, token)
            return
        except NichtGefunden:
            schlafen(FORK_ABSTAND)
    raise PublizierenFehler(
        "GitHub braucht ungewöhnlich lange für die Kopie des Marktplatzes. "
        "Bitte in ein paar Minuten noch einmal versuchen."
    )


def _lege_zweig_an(konto: str, zweig: str, basis: str, token: str,
                   aufruf: Aufruf) -> None:
    try:
        aufruf("POST", f"/repos/{konto}/{ZIEL_REPO}/git/refs",
               {"ref": f"refs/heads/{zweig}", "sha": basis}, token)
    except PublizierenFehler:
        # Der Zweig gibt es schon, weil dasselbe Lernset schon einmal
        # eingereicht wurde. Dann wird er auf den aktuellen Stand gesetzt -
        # sonst enthielte der Pull Request Änderungen von vorletzter Woche.
        aufruf("PATCH", f"/repos/{konto}/{ZIEL_REPO}/git/refs/heads/{zweig}",
               {"sha": basis, "force": True}, token)


def _schreibe_datei(konto: str, zweig: str, pfad: str, name: str,
                    items: list[dict], app_version: str, token: str,
                    aufruf: Aufruf) -> bool:
    nutzlast = {
        "message": f"Lernset: {name}",
        "content": base64.b64encode(_inhalt(name, items, app_version)).decode("ascii"),
        "branch": zweig,
    }
    try:
        vorhanden = aufruf("GET", f"/repos/{konto}/{ZIEL_REPO}/contents/{pfad}?ref={zweig}",
                           None, token)
        if isinstance(vorhanden, dict) and vorhanden.get("sha"):
            nutzlast["sha"] = str(vorhanden["sha"])
    except NichtGefunden:
        pass

    aufruf("PUT", f"/repos/{konto}/{ZIEL_REPO}/contents/{pfad}", nutzlast, token)
    return "sha" in nutzlast


def _oeffne_pull_request(konto: str, zweig: str, name: str, fach: str,
                         karten: int, aktualisiert: bool, token: str,
                         aufruf: Aufruf) -> Ergebnis:
    titel = f"{'Aktualisiert' if aktualisiert else 'Neu'}: {name} ({fach})"
    text = (
        f"Eingereicht aus LernApp.\n\n"
        f"- **Lernset:** {name}\n"
        f"- **Fach:** {fach}\n"
        f"- **Karten:** {karten}\n\n"
        f"Die Sperrliste lief vor dem Absenden durch.\n"
    )
    try:
        antwort = aufruf("POST", f"/repos/{ZIEL_BESITZER}/{ZIEL_REPO}/pulls",
                         {"title": titel, "head": f"{konto}:{zweig}",
                          "base": ZIEL_ZWEIG, "body": text}, token)
        if not isinstance(antwort, dict):
            raise PublizierenFehler("GitHub hat unverständlich geantwortet.")
    except PublizierenFehler:
        # Meist: für diesen Zweig steht schon ein Pull Request offen. Die neue
        # Fassung hängt dann bereits daran - Bescheid geben statt scheitern.
        offen = aufruf("GET", f"/repos/{ZIEL_BESITZER}/{ZIEL_REPO}/pulls"
                              f"?head={konto}:{zweig}&state=open", None, token)
        if isinstance(offen, list) and offen:
            return Ergebnis(str(offen[0].get("html_url", "")), zweig, True)
        raise

    return Ergebnis(str(antwort.get("html_url", "")), zweig, aktualisiert)
