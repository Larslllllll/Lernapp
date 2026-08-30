"""Zugang zu einem Sprachmodell - anbieterneutral.

Alles läuft über die OpenAI-kompatible Schnittstelle, die praktisch jeder
Anbieter spricht (Nous, Gemini, Groq, Cerebras, Mistral, OpenRouter). Der
Wechsel ist damit eine Umgebungsvariable, kein Umbau.

**Dieses Modul wird nie in der ausgelieferten App benutzt.** Es dient dem
Anreichern der Lernsets auf Lars' Rechner, einmalig, vor dem Veröffentlichen.
Deshalb steht auch kein Schlüssel im Programm: er kommt aus der Umgebung, und
er gehört weder ins Repo noch in ein Bundle.

    setx LERNAPP_KI_SCHLUESSEL "..."
    setx LERNAPP_KI_BASIS      "https://inference-api.nousresearch.com/v1"
    setx LERNAPP_KI_MODELL     "Hermes-4-70B"
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ZEITLIMIT = 120

# Bekannte Anbieter als Abkürzung. Alles andere geht über LERNAPP_KI_BASIS.
ANBIETER = {
    # Gratis nutzbar und im Vergleich an echten Vokabeln als bestes der
    # freien Modelle hervorgegangen (6/6 gegen 5/6). Die bezahlten
    # Modelle des Portals verlangen Guthaben.
    "nous": ("https://inference-api.nousresearch.com/v1",
             "inclusionai/ling-3.0-flash-fin:free"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai",
               "gemini-2.5-flash"),
    "groq": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    "cerebras": ("https://api.cerebras.ai/v1", "llama-3.3-70b"),
    "mistral": ("https://api.mistral.ai/v1", "mistral-small-latest"),
}


class KIFehler(Exception):
    """Fehler, dessen Text man zeigen kann."""


@dataclass(frozen=True)
class Zugang:
    basis: str
    modell: str
    schluessel: str
    name: str = ""

    @property
    def bereit(self) -> bool:
        return bool(self.basis and self.modell and self.schluessel)


# Lokale Schluesseldateien, die NICHT im Repo liegen duerfen. Sie werden
# gelesen, aber nie geschrieben - und echte Umgebungsvariablen haben Vorrang.
SCHLUESSELDATEIEN = (".NOUS.ENV", ".ki.env")

# Feldnamen, die in solchen Dateien ueblich sind, je Zweck.
FELDER = {
    "schluessel": ("LERNAPP_KI_SCHLUESSEL", "NOUS_API_KEY", "OPENAI_API_KEY",
                   "API_KEY"),
    "modell": ("LERNAPP_KI_MODELL", "NOUS_MODEL_ID", "MODEL_ID", "MODEL"),
    "basis": ("LERNAPP_KI_BASIS", "NOUS_BASE_URL", "BASE_URL"),
}


def _aus_datei(wurzel: Path | None = None) -> dict[str, str]:
    """KEY=VALUE aus einer lokalen Schluesseldatei lesen.

    Bequemlichkeit, damit niemand Schluessel durch die Gegend kopiert. Die
    Datei gehoert in .gitignore - eine namens .NOUS.ENV war von ".env" und
    ".env.*" nicht erfasst und lag ungeschuetzt neben dem Quelltext.
    """
    # Als Parameter, damit ein Test nicht am Projektverzeichnis hängt.
    wurzel = wurzel or Path(__file__).resolve().parent.parent.parent
    gefunden: dict[str, str] = {}
    for name in SCHLUESSELDATEIEN:
        datei = wurzel / name
        if not datei.exists():
            continue
        for zeile in datei.read_text(encoding="utf-8", errors="replace").splitlines():
            zeile = zeile.strip()
            if not zeile or zeile.startswith("#") or "=" not in zeile:
                continue
            schluessel, _, wert = zeile.partition("=")
            gefunden.setdefault(schluessel.strip().upper(),
                                wert.strip().strip("\"'"))
    return gefunden


def _wert(zweck: str, datei: dict[str, str], anbieter: str = "") -> str:
    """Erst die Umgebung, dann die Datei. Anbieterspezifisch geht vor."""
    namen = FELDER[zweck]
    if anbieter:
        namen = (f"{namen[0]}_{anbieter.upper()}", *namen)
    for name in namen:
        wert = os.environ.get(name) or datei.get(name)
        if wert:
            return wert
    return ""


def aus_umgebung(anbieter: str = "") -> Zugang:
    """Zugang aus den Umgebungsvariablen zusammensetzen.

    `anbieter` überschreibt Basis und Modell mit einer bekannten Vorgabe -
    praktisch, um zwei Anbieter nacheinander zu vergleichen.
    """
    datei = _aus_datei()

    # Ohne ausdrücklichen Anbieter aus dem Schlüsselnamen schliessen: wer eine
    # Datei mit NOUS_API_KEY hinlegt, meint Nous und soll nicht zusätzlich
    # eine Basis-Adresse eintragen müssen.
    if not anbieter and not _wert("basis", datei):
        for name in ANBIETER:
            if os.environ.get(f"{name.upper()}_API_KEY") or datei.get(f"{name.upper()}_API_KEY"):
                anbieter = name
                break

    vorgabe_basis, vorgabe_modell = ANBIETER.get(anbieter, ("", ""))

    # Reihenfolge: was ausdrücklich gesetzt ist, schlägt die Vorgabe.
    basis = _wert("basis", datei, anbieter) or vorgabe_basis
    modell = _wert("modell", datei, anbieter) or vorgabe_modell
    schluessel = _wert("schluessel", datei, anbieter)

    # Wer das Modell aus der Weboberfläche kopiert, erwischt den Anzeigenamen
    # ("Upstage: Solar Pro 4") statt der Kennung ("upstage/solar-pro4"). Die
    # API antwortet darauf mit einem nichtssagenden 404. Ein Name mit
    # Leerzeichen ist nie eine Kennung - dann lieber die Vorgabe nehmen.
    if " " in modell and vorgabe_modell:
        modell = vorgabe_modell

    return Zugang(basis.rstrip("/"), modell, schluessel, anbieter or "eigen")


def frage(zugang: Zugang, system: str, auftrag: str,
          temperatur: float = 0.4, versuche: int = 3) -> str:
    """Eine Anfrage stellen und den Text zurückgeben.

    Wiederholt bei 429 und 5xx mit wachsendem Abstand - Gratis-Stufen
    begrenzen die Anfragen pro Minute, und ein Lauf über 1500 Karten läuft
    sonst nach zwei Minuten gegen die Wand.
    """
    if not zugang.bereit:
        raise KIFehler(
            "Kein Zugang eingerichtet. Nötig sind LERNAPP_KI_BASIS, "
            "LERNAPP_KI_MODELL und LERNAPP_KI_SCHLUESSEL."
        )

    nutzlast = json.dumps({
        "model": zugang.modell,
        "temperature": temperatur,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": auftrag},
        ],
    }).encode("utf-8")

    anfrage = urllib.request.Request(
        f"{zugang.basis}/chat/completions", data=nutzlast, method="POST",
        headers={
            "Authorization": f"Bearer {zugang.schluessel}",
            "Content-Type": "application/json",
            "User-Agent": "LernApp",
        },
    )

    letzter = ""
    for versuch in range(versuche):
        try:
            with urllib.request.urlopen(anfrage, timeout=ZEITLIMIT) as antwort:
                roh = json.loads(antwort.read().decode("utf-8"))
            return str(roh["choices"][0]["message"]["content"]).strip()
        except urllib.error.HTTPError as grund:
            letzter = f"Fehler {grund.code}"
            if grund.code == 401:
                raise KIFehler("Der Schlüssel wird abgelehnt.") from grund
            if grund.code not in (429, 500, 502, 503, 529):
                raise KIFehler(f"Der Anbieter antwortet mit {grund.code}.") from grund
        except (urllib.error.URLError, OSError) as grund:
            letzter = str(grund)
        except (KeyError, IndexError, json.JSONDecodeError) as grund:
            raise KIFehler("Die Antwort hat ein unerwartetes Format.") from grund
        time.sleep(2 ** versuch * 3)

    raise KIFehler(f"Auch nach {versuche} Versuchen keine Antwort ({letzter}).")
