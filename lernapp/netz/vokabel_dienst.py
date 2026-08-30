"""Vokabeln erkennen - entweder direkt oder über den Vermittler.

Zwei Wege, und der Nutzer merkt den Unterschied nicht:

- **Mit eigenem Schlüssel** (nur auf Lars' Rechner): direkt zum Anbieter.
  Kein Deckel, keine fremde Zwischenstation.
- **Ohne Schlüssel** (jeder Mitschüler): über den kleinen Dienst auf
  Cloudflare. Der Schlüssel liegt dort, nicht in der App - sie ist
  quelloffen und wird als .exe verteilt, ein Schlüssel darin wäre in Minuten
  ausgelesen.

Die Gerätekennung ist eine Zufallszahl ohne jeden Bezug zur Person. Sie
existiert nur, damit der Dienst „20 Seiten pro Tag" zählen kann, und liegt im
Datenverzeichnis neben den Vokabeln.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from .ki import KIFehler, aus_umgebung
from .lernset_ki import Vorschlag, _saeubere
from .lernset_ki import erkenne_vokabeln as direkt_erkennen

# Adresse des Vermittlers. Öffentlich und ungefährlich - er kann nur
# Vokabeln erkennen, siehe server/worker.js.
DIENST_URL = "https://lernapp-vokabeln.ytschau80.workers.dev"

ZEITLIMIT = 120
GERAET_DATEI = "geraet.txt"


def geraetekennung(datenverzeichnis: Path) -> str:
    """Zufällige Kennung dieses Rechners, einmal erzeugt und behalten.

    Kein Personenbezug: eine Zufallszahl, mehr nicht. Sie existiert, damit
    der Dienst pro Gerät zählen kann statt gar nicht.
    """
    datei = datenverzeichnis / GERAET_DATEI
    try:
        vorhanden = datei.read_text(encoding="utf-8").strip()
        if len(vorhanden) >= 8:
            return vorhanden
    except OSError:
        pass

    neu = uuid.uuid4().hex
    try:
        datenverzeichnis.mkdir(parents=True, exist_ok=True)
        datei.write_text(neu, encoding="utf-8")
    except OSError:
        # Ohne Datei geht es auch - dann zählt der Dienst diese Sitzung
        # eben für sich. Kein Grund, den Import scheitern zu lassen.
        pass
    return neu


def verfuegbar() -> bool:
    """Kann überhaupt jemand Vokabeln erkennen lassen?"""
    return bool(DIENST_URL) or aus_umgebung().bereit


def erkenne(text: str, datenverzeichnis: Path) -> Vorschlag:
    """Vokabeln erkennen - auf dem Weg, der gerade möglich ist."""
    zugang = aus_umgebung()
    if zugang.bereit:
        return direkt_erkennen(zugang, text)
    if not DIENST_URL:
        raise KIFehler(
            "Für das Einlesen ist kein Dienst eingerichtet. Vokabeln von Hand "
            "einfügen geht weiterhin."
        )
    return _ueber_dienst(text, geraetekennung(datenverzeichnis))


def _ueber_dienst(text: str, geraet: str) -> Vorschlag:
    nutzlast = json.dumps({"text": text, "geraet": geraet}).encode("utf-8")
    anfrage = urllib.request.Request(
        DIENST_URL.rstrip("/") + "/vokabeln", data=nutzlast, method="POST",
        # Der User-Agent ist NICHT schmückendes Beiwerk: Cloudflare lehnt den
        # Standardwert von urllib ("Python-urllib/3.11") mit 403 und
        # "error code: 1010" ab, bevor der Worker ihn je sieht. Ohne diese
        # Zeile ist der PDF-Import tot, und die Meldung sagt nicht warum.
        headers={"Content-Type": "application/json", "User-Agent": "LernApp"},
    )
    try:
        with urllib.request.urlopen(anfrage, timeout=ZEITLIMIT) as antwort:
            roh = json.loads(antwort.read().decode("utf-8"))
    except urllib.error.HTTPError as grund:
        # Der Dienst schickt bei Deckeln und Fehlern einen Text mit, der für
        # den Nutzer gedacht ist. Den zeigen, statt "Fehler 429".
        try:
            meldung = json.loads(grund.read().decode("utf-8")).get("fehler", "")
        except Exception:
            meldung = ""
        raise KIFehler(meldung or "Das Einlesen hat nicht geklappt.") from grund
    except (urllib.error.URLError, OSError) as grund:
        raise KIFehler(
            "Der Dienst zum Einlesen ist nicht erreichbar. "
            "Internetverbindung prüfen."
        ) from grund

    vorschlag = _saeubere(str(roh.get("text", "")))
    if not vorschlag.zeilen:
        raise KIFehler(
            "In diesem Text konnte ich keine Vokabelpaare erkennen. "
            "Vielleicht ist es eine Textseite ohne Vokabelliste."
        )
    return vorschlag
