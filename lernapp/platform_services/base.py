"""Gemeinsame Schnittstelle der plattformspezifischen Dienste.

Regel: ausserhalb dieses Pakets darf kein Modul `winsound`, `AppKit` oder
ähnliches importieren. Fehler in einem Dienst dürfen das Lernen niemals
verhindern - alle Implementierungen schlucken ihre eigenen Ausnahmen.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol


# Fachliche Aktionsnamen. Die Oberfläche kennt nur diese Namen, nie eine
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

    def beim_start(self) -> None: ...

    def zeige_meldung(self, titel: str, text: str) -> bool: ...


class BasisDienste:
    """Neutrale Grundimplementierung - tut nichts, schlägt nie fehl."""

    name = "generisch"

    def spiele_ton(self, richtig: bool) -> None:
        return None

    def unterstuetzt_ton(self) -> bool:
        return False

    def beim_start(self) -> None:
        """Einmalige Einrichtung vor dem ersten Fenster. Standard: nichts."""
        return None

    def zeige_meldung(self, titel: str, text: str) -> bool:
        """Meldung ohne Qt anzeigen. Standard: geht nicht, sagt es ehrlich.

        Gedacht als letzter Ausweg für Abstürze, bei denen Qt selbst nicht
        mehr steht — im gebauten Bundle gibt es keine Konsole, auf der eine
        Meldung sonst landen könnte.
        """
        return False

    def datenverzeichnis(self) -> Path:
        from lernapp.storage import paths

        return paths.datenverzeichnis()

    def tastenkuerzel(self) -> dict[str, str]:
        """Aktionsname -> Qt-Tastenfolge.

        Qt bildet "Ctrl" in einer Tastenfolge auf macOS bereits selbst auf die
        Command-Taste ab. Diese Methode existiert trotzdem, damit echte
        Abweichungen (andere Taste, zusätzliches Kürzel) an genau einer
        Stelle liegen und die Oberfläche nie eine Kombination fest verdrahtet.
        """
        return {
            "neuesLernset": "Ctrl+N",
            "lernsetBearbeiten": "Ctrl+E",
            "themeUmschalten": "Ctrl+D",
            "tonUmschalten": "Ctrl+M",
            "neustart": "Ctrl+R",
        }
