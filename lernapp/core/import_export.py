"""Import und Export von Lernsets.

GUI-frei und ohne Datei-I/O: hier wird nur zwischen Text/Dict und Karten
übersetzt. Wer Dateien schreibt, ist lernapp.storage.

Importformate (Trennzeichen wird automatisch erkannt):

    être;sein                 zwei Felder  -> eine normale Karte
    go;went;gone              drei Felder  -> ein Verbpaket (drei Karten)

Erkannt werden Tabulator, Semikolon und - nur wenn keins von beiden
vorkommt - Komma. Das Komma ist bewusst die letzte Wahl, weil Antworten
oft selbst Kommas enthalten ("das Fahrrad, das Rad").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .cards import NormalCard, TripleCard, parse_items

EXPORT_SCHEMA = 1
DATEIENDUNG = ".lernset.json"

TAB = "\t"
SEMIKOLON = ";"
KOMMA = ","


@dataclass
class Zeilenproblem:
    zeile: int
    text: str
    grund: str


@dataclass
class ImportErgebnis:
    """Vorschau eines Imports - wird angezeigt, bevor etwas gespeichert wird."""

    items: list[dict] = field(default_factory=list)
    trenner: str = ""
    normale: int = 0
    pakete: int = 0
    probleme: list[Zeilenproblem] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.items)

    @property
    def einheiten(self) -> int:
        """Zählbare Lerneinheiten - ein Paket zählt als eins."""
        return self.normale + self.pakete

    def zusammenfassung(self) -> str:
        if not self.items:
            return "Nichts erkannt"
        teile = []
        if self.normale:
            teile.append(f"{self.normale} Karte{'n' if self.normale != 1 else ''}")
        if self.pakete:
            teile.append(f"{self.pakete} Verbpaket{'e' if self.pakete != 1 else ''}")
        text = " und ".join(teile)
        if self.probleme:
            text += f", {len(self.probleme)} Zeile{'n' if len(self.probleme) != 1 else ''} übersprungen"
        return text


def erkenne_trenner(text: str) -> str:
    """Bestimmt das Trennzeichen für den gesamten Text.

    Tabulator und Semikolon gewinnen immer gegen das Komma, weil Antworten
    selbst Kommas enthalten können.
    """
    zeilen = [z for z in text.splitlines() if z.strip()]
    if not zeilen:
        return SEMIKOLON
    for kandidat in (TAB, SEMIKOLON):
        if any(kandidat in z for z in zeilen):
            return kandidat
    return KOMMA


def parse_text(text: str, trenner: str | None = None) -> ImportErgebnis:
    """Zerlegt eingefügten Text in Karten. Schreibt nichts."""
    ergebnis = ImportErgebnis(trenner=trenner or erkenne_trenner(text))

    for nummer, roh in enumerate(text.splitlines(), start=1):
        zeile = roh.strip()
        if not zeile:
            continue

        felder = [f.strip() for f in zeile.split(ergebnis.trenner)]
        felder = [f for f in felder if f]

        if len(felder) == 2:
            ergebnis.items.append({"q": felder[0], "a": felder[1].lower()})
            ergebnis.normale += 1
        elif len(felder) == 3:
            formen = (felder[0].lower(), felder[1].lower(), felder[2].lower())
            ergebnis.items.extend(
                TripleCard(forms=formen, revealed=i).legacy_item() for i in (0, 1, 2)
            )
            ergebnis.pakete += 1
        elif len(felder) < 2:
            ergebnis.probleme.append(
                Zeilenproblem(nummer, zeile, "kein Trennzeichen gefunden"))
        else:
            ergebnis.probleme.append(
                Zeilenproblem(nummer, zeile, f"{len(felder)} Felder statt 2 oder 3"))

    return ergebnis


# -- Export -------------------------------------------------------------------

def als_export(name: str, items: list[dict], app_version: str = "") -> dict:
    """Plattformneutrales Austauschformat.

    Bewusst nur Inhalt, kein Fortschritt: ein geteiltes Lernset soll nicht
    die XP des Absenders mitbringen.
    """
    return {
        "schema_version": EXPORT_SCHEMA,
        "typ": "lernset",
        "name": name,
        "erstellt_am": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "app_version": app_version,
        "items": [{"q": i["q"], "a": i["a"]} for i in items],
    }


def aus_export(roh: dict) -> tuple[str, list[dict]]:
    """(Name, Karten) aus einer Austauschdatei.

    Wirft ValueError bei allem, was nicht wie ein Lernset aussieht - lieber
    eine klare Meldung als ein halb importiertes Set.
    """
    if not isinstance(roh, dict):
        raise ValueError("Datei enthält kein Lernset")
    if roh.get("typ") not in (None, "lernset"):
        raise ValueError(f"Unbekannter Typ: {roh.get('typ')}")
    if roh.get("schema_version", EXPORT_SCHEMA) > EXPORT_SCHEMA:
        raise ValueError(
            "Die Datei stammt aus einer neueren Programmversion. Bitte LernApp aktualisieren.")

    items = roh.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("Die Datei enthält keine Karten")

    sauber: list[dict] = []
    for eintrag in items:
        if not isinstance(eintrag, dict):
            continue
        q = str(eintrag.get("q", "")).strip()
        a = str(eintrag.get("a", "")).strip()
        if q and a:
            sauber.append({"q": q, "a": a})
    if not sauber:
        raise ValueError("Die Datei enthält keine brauchbaren Karten")

    name = str(roh.get("name", "")).strip() or "Importiertes Lernset"
    return name, sauber


def dateiname_fuer(name: str) -> str:
    """Sicherer Dateiname aus einem Lernset-Namen.

    Muss auf Windows und macOS funktionieren, also ohne die unter Windows
    verbotenen Zeichen und ohne Leerzeichen am Rand.
    """
    verboten = '<>:"/\\|?*'
    sauber = "".join("-" if z in verboten else z for z in name).strip()
    sauber = "-".join(teil for teil in sauber.split() if teil)
    return (sauber or "Lernset") + DATEIENDUNG


def als_text(items: list[dict], trenner: str = SEMIKOLON) -> str:
    """Karten als einfacher Text - zum Kopieren in eine Nachricht.

    Verbpakete werden wieder zu einer Zeile mit drei Formen zusammengefasst,
    damit ein Export nicht dreimal so lang wird wie das Original.
    """
    karten = parse_items(items)
    zeilen: list[str] = []
    gesehen: set[tuple[str, str, str]] = set()

    for karte in karten:
        if isinstance(karte, TripleCard):
            if karte.package_key in gesehen:
                continue
            gesehen.add(karte.package_key)
            zeilen.append(trenner.join(karte.forms))
        elif isinstance(karte, NormalCard):
            zeilen.append(trenner.join((karte.question, karte.answer)))
    return "\n".join(zeilen)
