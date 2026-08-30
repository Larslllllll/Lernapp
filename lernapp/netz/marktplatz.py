"""Der Marktplatz: fertige Lernsets aus dem Netz holen.

Kennt weder Qt noch die Oberflaeche und schreibt keine Datei. Wer laedt, wird
hereingereicht (`lader`) - deshalb laufen die Tests ohne Internet.

Der Katalog liegt als index.json in einem oeffentlichen Repo. Jeder Eintrag
fuehrt eine SHA-256-Summe; heruntergeladen wird gegen diese Summe geprueft,
bevor irgendetwas in die Lernsets des Nutzers wandert. Dieselbe Regel wie beim
Installer: nichts uebernehmen, was nicht dem entspricht, was angekuendigt war.

Bewusst NICHT hier: die Zahl der Lerneinheiten. Ein Verbpaket liegt als drei
Karten in der Datei und zaehlt als eine Einheit - diese Regel steht in
lernapp.core und darf keine zweite Fassung bekommen.
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable

from lernapp.core.import_export import aus_export

SCHEMA = 1
STANDARD_KATALOG = (
    "https://raw.githubusercontent.com/Larslllllll/Lernapp-lernsets/main/index.json"
)

# Ein Katalog oder ein Lernset ist eine kleine Textdatei. Alles jenseits davon
# ist ein Versehen oder ein Angriff, und beides will man nicht in den Speicher
# laden.
MAX_BYTES = 5 * 1024 * 1024
ZEITLIMIT = 20

Lader = Callable[[str], bytes]


class MarktplatzFehler(Exception):
    """Fehler, dessen Text direkt dem Nutzer gezeigt werden kann."""


@dataclass(frozen=True)
class Eintrag:
    id: str
    name: str
    fach: str
    url: str
    karten: int
    groesse: int
    sha256: str


@dataclass(frozen=True)
class Katalog:
    aktualisiert_am: str
    eintraege: tuple[Eintrag, ...]

    def faecher(self) -> tuple[str, ...]:
        """Faecher in der Reihenfolge ihres ersten Auftretens im Katalog."""
        gesehen: list[str] = []
        for eintrag in self.eintraege:
            if eintrag.fach not in gesehen:
                gesehen.append(eintrag.fach)
        return tuple(gesehen)


def lade_ueber_netz(url: str) -> bytes:
    """Standardlader. Nur HTTPS, mit Zeitlimit und Groessengrenze."""
    if not url.startswith("https://"):
        raise MarktplatzFehler("Nur HTTPS-Adressen werden geladen.")
    anfrage = urllib.request.Request(url, headers={"User-Agent": "LernApp"})
    try:
        with urllib.request.urlopen(anfrage, timeout=ZEITLIMIT) as antwort:
            # Ein Byte mehr lesen als erlaubt, damit ein zu grosser Inhalt
            # auffaellt, statt still abgeschnitten zu werden.
            daten = antwort.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as grund:
        raise MarktplatzFehler(
            f"Der Marktplatz antwortet nicht wie erwartet (Fehler {grund.code})."
        ) from grund
    except (urllib.error.URLError, OSError) as grund:
        raise MarktplatzFehler(
            "Keine Verbindung zum Marktplatz. Internetverbindung prüfen."
        ) from grund
    if len(daten) > MAX_BYTES:
        raise MarktplatzFehler("Die Datei ist unerwartet groß und wurde verworfen.")
    return daten


def _als_json(daten: bytes, was: str) -> dict:
    try:
        roh = json.loads(daten.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as grund:
        raise MarktplatzFehler(f"{was} ist beschädigt.") from grund
    if not isinstance(roh, dict):
        raise MarktplatzFehler(f"{was} hat ein unerwartetes Format.")
    return roh


def _url_bauen(basis: str, datei: str) -> str:
    """basis_url und den Pfad aus dem Katalog zusammensetzen.

    `datei` kommt aus einer Datei im Netz. Ein Pfad, der aus dem Repo
    herausfuehrt oder auf einen anderen Server zeigt, wird abgelehnt - sonst
    liesse sich ueber einen manipulierten Katalog eine beliebige Adresse
    unterschieben.
    """
    if not basis.startswith("https://"):
        raise MarktplatzFehler("Der Katalog nennt keine HTTPS-Adresse.")
    if not datei or datei.startswith(("/", "\\")) or "://" in datei or ".." in datei:
        raise MarktplatzFehler(f"Der Katalog enthält einen unzulässigen Pfad: {datei}")
    return basis.rstrip("/") + "/" + datei.lstrip("/")


def lade_katalog(lader: Lader = lade_ueber_netz,
                 url: str = STANDARD_KATALOG) -> Katalog:
    """Das Verzeichnis aller angebotenen Lernsets holen."""
    roh = _als_json(lader(url), "Das Verzeichnis")

    version = roh.get("schema_version")
    if version != SCHEMA:
        # Groesser heisst: der Marktplatz ist weiter als diese App. Kleiner
        # sollte nie vorkommen; beides ist derselbe Rat an den Nutzer.
        raise MarktplatzFehler(
            "Der Marktplatz braucht eine neuere Version von LernApp."
            if isinstance(version, int) and version > SCHEMA
            else "Das Verzeichnis hat ein unbekanntes Format."
        )

    basis = str(roh.get("basis_url", ""))
    eintraege: list[Eintrag] = []
    for satz in roh.get("lernsets", []):
        if not isinstance(satz, dict):
            continue
        name = str(satz.get("name", "")).strip()
        datei = str(satz.get("datei", ""))
        summe = str(satz.get("sha256", ""))
        if not name or not datei or len(summe) != 64:
            # Einen unvollstaendigen Eintrag ueberspringen statt den ganzen
            # Katalog zu verwerfen: ein kaputtes Lernset soll nicht die
            # anderen 23 unerreichbar machen.
            continue
        eintraege.append(Eintrag(
            id=str(satz.get("id", "")) or name.lower(),
            name=name,
            fach=str(satz.get("ordner", "")).strip() or "Ohne Fach",
            url=_url_bauen(basis, datei),
            karten=int(satz.get("karten", 0) or 0),
            groesse=int(satz.get("groesse", 0) or 0),
            sha256=summe.lower(),
        ))

    if not eintraege:
        raise MarktplatzFehler("Der Marktplatz enthält derzeit keine Lernsets.")
    return Katalog(str(roh.get("aktualisiert_am", "")), tuple(eintraege))


def lade_lernset(eintrag: Eintrag,
                 lader: Lader = lade_ueber_netz) -> tuple[str, list[dict]]:
    """(Name, Karten) eines Lernsets - erst nach bestandener Pruefsumme.

    Der Name kommt aus der geladenen Datei, nicht aus dem Katalog: massgeblich
    ist, was tatsaechlich im Lernset steht.
    """
    daten = lader(eintrag.url)
    tatsaechlich = hashlib.sha256(daten).hexdigest()
    if tatsaechlich != eintrag.sha256:
        raise MarktplatzFehler(
            f"„{eintrag.name}“ stimmt nicht mit dem Verzeichnis überein und "
            "wurde verworfen. Bitte später noch einmal versuchen."
        )
    try:
        return aus_export(_als_json(daten, f"„{eintrag.name}“"))
    except ValueError as grund:
        raise MarktplatzFehler(str(grund)) from grund
