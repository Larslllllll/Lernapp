"""macOS-spezifische Dienste.

Noch nicht auf echter Hardware getestet - siehe Phase-2-Bericht.
Der Ton laeuft ueber afplay, weil das ohne Zusatzpakete verfuegbar ist.
"""
from __future__ import annotations

import subprocess
import threading
from pathlib import Path

from .base import BasisDienste

_RICHTIG = "/System/Library/Sounds/Tink.aiff"
_FALSCH = "/System/Library/Sounds/Basso.aiff"


class MacDienste(BasisDienste):
    name = "macos"

    def tastenkuerzel(self) -> dict[str, str]:
        """Qt uebersetzt "Ctrl" auf macOS selbst zu Command.

        Die Standardzuordnung passt daher bereits. Sobald sich auf echter
        Hardware zeigt, dass eine Kombination mit einem System-Kuerzel
        kollidiert, wird sie hier - und nur hier - ueberschrieben.
        """
        return super().tastenkuerzel()

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
