"""Gemeinsame Schnittstelle der plattformspezifischen Dienste.

Regel: ausserhalb dieses Pakets darf kein Modul `winsound`, `AppKit` oder
aehnliches importieren. Fehler in einem Dienst duerfen das Lernen niemals
verhindern - alle Implementierungen schlucken ihre eigenen Ausnahmen.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol


# Fachliche Aktionsnamen. Die Oberflaeche kennt nur diese Namen, nie eine
# konkrete Tastenkombination.
AKTIONEN = (
    "neuesLernset",
    "lernsetBearbeiten",
    "themeUmschalten",
    "tonUmschalten",
    "neustart",
)


class PlattformDienste(Protocol):
    name: str

    def spiele_ton(self, richtig: bool) -> None: ...

    def datenverzeichnis(self) -> Path: ...

    def unterstuetzt_ton(self) -> bool: ...

    def tastenkuerzel(self) -> dict[str, str]: ...


class BasisDienste:
    """Neutrale Grundimplementierung - tut nichts, schlaegt nie fehl."""

    name = "generisch"

    def spiele_ton(self, richtig: bool) -> None:
        return None

    def unterstuetzt_ton(self) -> bool:
        return False

    def datenverzeichnis(self) -> Path:
        from lernapp.storage import paths

        return paths.datenverzeichnis()

    def tastenkuerzel(self) -> dict[str, str]:
        """Aktionsname -> Qt-Tastenfolge.

        Qt bildet "Ctrl" in einer Tastenfolge auf macOS bereits selbst auf die
        Command-Taste ab. Diese Methode existiert trotzdem, damit echte
        Abweichungen (andere Taste, zusaetzliches Kuerzel) an genau einer
        Stelle liegen und die Oberflaeche nie eine Kombination fest verdrahtet.
        """
        return {
            "neuesLernset": "Ctrl+N",
            "lernsetBearbeiten": "Ctrl+E",
            "themeUmschalten": "Ctrl+D",
            "tonUmschalten": "Ctrl+M",
            "neustart": "Ctrl+R",
        }
