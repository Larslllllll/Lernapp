"""ViewModel fuer Einstellungen: Theme, Lernrichtung, Ton.

Haelt nur Zustand und Persistenz - keine Lernregeln.
"""
from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from lernapp.core.learning_engine import GEMISCHT, RUECKWAERTS, VORWAERTS

from .app_state import AppState

RICHTUNGEN = (VORWAERTS, RUECKWAERTS, GEMISCHT)


class SettingsViewModel(QObject):
    themeGeaendert = Signal()
    richtungGeaendert = Signal(str)
    soundGeaendert = Signal()

    def __init__(self, state: AppState) -> None:
        super().__init__()
        self._state = state

    # -- Theme ----------------------------------------------------------------

    @Property(bool, notify=themeGeaendert)
    def dark(self) -> bool:
        return self._state.settings.get("theme", "dark") == "dark"

    @dark.setter
    def dark(self, wert: bool) -> None:
        neu = "dark" if wert else "light"
        if self._state.settings.get("theme") == neu:
            return
        self._state.settings["theme"] = neu
        self._state.save_settings()
        self.themeGeaendert.emit()

    @Slot()
    def themeUmschalten(self) -> None:
        self.dark = not self.dark

    # -- Lernrichtung ---------------------------------------------------------

    @Property("QVariantList", constant=True)
    def richtungen(self) -> list:
        return list(RICHTUNGEN)

    @Property(str, notify=richtungGeaendert)
    def richtung(self) -> str:
        wert = self._state.settings.get("richtung", GEMISCHT)
        return wert if wert in RICHTUNGEN else GEMISCHT

    @richtung.setter
    def richtung(self, wert: str) -> None:
        if wert not in RICHTUNGEN or wert == self.richtung:
            return
        self._state.settings["richtung"] = wert
        self._state.save_settings()
        self.richtungGeaendert.emit(wert)

    @Slot(str)
    def setzeRichtung(self, wert: str) -> None:
        self.richtung = wert

    # -- Ton ------------------------------------------------------------------

    @Property(bool, notify=soundGeaendert)
    def sound(self) -> bool:
        return bool(self._state.settings.get("sound", True))

    @sound.setter
    def sound(self, wert: bool) -> None:
        if bool(self._state.settings.get("sound", True)) == bool(wert):
            return
        self._state.settings["sound"] = bool(wert)
        self._state.save_settings()
        self.soundGeaendert.emit()

    @Slot()
    def soundUmschalten(self) -> None:
        self.sound = not self.sound

    # -- Fenstergroesse merken ------------------------------------------------

    @Property(int, constant=True)
    def fensterBreite(self) -> int:
        return int(self._state.settings.get("fenster", {}).get("breite", 1180))

    @Property(int, constant=True)
    def fensterHoehe(self) -> int:
        return int(self._state.settings.get("fenster", {}).get("hoehe", 760))

    @Slot(int, int)
    def merkeFenster(self, breite: int, hoehe: int) -> None:
        if breite < 400 or hoehe < 300:
            return
        self._state.settings["fenster"] = {"breite": int(breite), "hoehe": int(hoehe)}
        self._state.save_settings()
