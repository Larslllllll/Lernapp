"""Gemeinsamer Zustand der Oberflaeche.

Haelt die geladenen Lernsets, den Fortschritt und die Einstellungen an einer
Stelle, damit die ViewModels sich nicht gegenseitig Daten durchreichen muessen.

Enthaelt keine Lernregeln - die liegen ausschliesslich in lernapp.core.
"""
from __future__ import annotations

from pathlib import Path

from lernapp.core.cards import parse_items
from lernapp.core.learning_engine import LearningSession
from lernapp.core.progress import SetProgress
from lernapp.storage import local_storage as store
from lernapp.storage import paths
from lernapp.storage.settings import load_settings, save_settings, settings_file


class AppState:
    """`basis` ueberschreibt das Datenverzeichnis - nur fuer Tests gedacht."""

    def __init__(self, basis: Path | None = None) -> None:
        self._basis = basis
        self.data = store.load_data(self._data_pfad)
        self.progress = store.load_prog(self._prog_pfad)
        self.settings = load_settings(self._settings_pfad)

    # -- Pfade ----------------------------------------------------------------

    @property
    def _data_pfad(self) -> Path:
        return paths.data_file(self._basis)

    @property
    def _prog_pfad(self) -> Path:
        return paths.prog_file(self._basis)

    @property
    def _settings_pfad(self) -> Path:
        return settings_file(self._basis)

    # -- Persistenz -----------------------------------------------------------

    def save_data(self) -> None:
        store.save_data(self.data, self._data_pfad)

    def save_progress(self) -> None:
        store.save_prog(self.progress, self._prog_pfad)

    def save_settings(self) -> None:
        save_settings(self.settings, self._settings_pfad)

    # -- Zugriff --------------------------------------------------------------

    @property
    def folders(self) -> dict:
        return self.data.setdefault("folders", {})

    def alle_lernsets(self):
        """(ordnername, lernset) fuer jedes Lernset."""
        for ordner, fdata in self.folders.items():
            for ls in fdata.get("lernsets", []):
                yield ordner, ls

    def finde_lernset(self, ls_id: str):
        for ordner, ls in self.alle_lernsets():
            if ls["id"] == ls_id:
                return ordner, ls
        return None, None

    def fortschritt_von(self, ls_id: str) -> SetProgress:
        return SetProgress.from_legacy(self.progress.get(ls_id, {}))

    def speichere_fortschritt(self, ls_id: str, fortschritt: SetProgress) -> None:
        self.progress[ls_id] = fortschritt.to_legacy()
        self.save_progress()

    def zaehler_von(self, ls_id: str, items: list[dict]) -> tuple[int, int]:
        """(gelernt, gesamt) in Lerneinheiten - dieselbe Quelle wie im Lernen."""
        sitzung = LearningSession(parse_items(items), fortschritt=self.fortschritt_von(ls_id))
        return sitzung.fortschritt_zaehler()
