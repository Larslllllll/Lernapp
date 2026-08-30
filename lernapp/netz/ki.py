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

ZEITLIMIT = 120

# Bekannte Anbieter als Abkürzung. Alles andere geht über LERNAPP_KI_BASIS.
ANBIETER = {
    "nous": ("https://inference-api.nousresearch.com/v1", "Hermes-4-70B"),
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


def aus_umgebung(anbieter: str = "") -> Zugang:
    """Zugang aus den Umgebungsvariablen zusammensetzen.

    `anbieter` überschreibt Basis und Modell mit einer bekannten Vorgabe -
    praktisch, um zwei Anbieter nacheinander zu vergleichen.
    """
    basis, modell = ANBIETER.get(anbieter, ("", ""))
    basis = basis or os.environ.get("LERNAPP_KI_BASIS", "")
    modell = os.environ.get("LERNAPP_KI_MODELL", "") if not anbieter else modell
    modell = modell or os.environ.get("LERNAPP_KI_MODELL", "")

    # Je Anbieter ein eigener Schlüssel, sonst der allgemeine. So lassen sich
    # zwei Anbieter vergleichen, ohne dauernd umzusetzen.
    schluessel = (os.environ.get(f"LERNAPP_KI_SCHLUESSEL_{anbieter.upper()}", "")
                  if anbieter else "")
    schluessel = schluessel or os.environ.get("LERNAPP_KI_SCHLUESSEL", "")

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
