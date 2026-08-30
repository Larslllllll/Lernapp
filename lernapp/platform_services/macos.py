"""macOS-spezifische Dienste.

Noch nicht auf echter Hardware getestet - siehe Phase-2-Bericht.
Der Ton läuft über afplay, weil das ohne Zusatzpakete verfügbar ist.
"""
from __future__ import annotations

import subprocess
import threading
from pathlib import Path

from .base import BasisDienste

_RICHTIG = "/System/Library/Sounds/Tink.aiff"
_FALSCH = "/System/Library/Sounds/Basso.aiff"


def _as_literal(text: str) -> str:
    """AppleScript-String. Backslash und Anführungszeichen maskieren."""
    maskiert = text.replace(chr(92), chr(92) * 2).replace('"', chr(92) + '"')
    return '"' + maskiert + '"'


class MacDienste(BasisDienste):
    name = "macos"

    def tastenkuerzel(self) -> dict[str, str]:
        """Qt übersetzt "Ctrl" auf macOS selbst zu Command.

        Die Standardzuordnung passt daher bereits. Sobald sich auf echter
        Hardware zeigt, dass eine Kombination mit einem System-Kürzel
        kollidiert, wird sie hier - und nur hier - überschrieben.
        """
        return super().tastenkuerzel()

    def zeige_meldung(self, titel: str, text: str) -> bool:
        """osascript — ohne Zusatzpakete verfügbar. Ungetestet (keine Hardware)."""
        skript = (f'display dialog {_as_literal(text)} '
                  f'with title {_as_literal(titel)} '
                  'buttons {"OK"} default button "OK" with icon caution')
        try:
            subprocess.run(["osascript", "-e", skript], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    def unterstuetzt_ton(self) -> bool:
        return Path(_RICHTIG).exists()

    def spiele_ton(self, richtig: bool) -> None:
        datei = _RICHTIG if richtig else _FALSCH
        if not Path(datei).exists():
            return

        def _spielen() -> None:
            try:
                subprocess.run(["afplay", datei], check=False,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        threading.Thread(target=_spielen, daemon=True).start()
