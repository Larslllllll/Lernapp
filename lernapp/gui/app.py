"""Start der PySide6/QML-Oberflaeche.

Verdrahtet die ViewModels miteinander und laedt Main.qml. Enthaelt selbst
keine Lernlogik.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine

from lernapp import __version__
from lernapp.platform_services import dienste

from .bridge.app_state import AppState
from .bridge.learning_viewmodel import LearningViewModel
from .bridge.sets_viewmodel import SetsViewModel
from .bridge.settings_viewmodel import SettingsViewModel

def _ressourcen() -> tuple[Path, Path]:
    """(qml-Verzeichnis, Icon-Datei).

    Im PyInstaller-Bundle liegen die Ressourcen unter sys._MEIPASS, nicht
    neben der .py-Datei - die steckt dann im Archiv.
    """
    if getattr(sys, "frozen", False):
        basis = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return basis / "qml", basis / "ico.ico"
    hier = Path(__file__).resolve().parent
    return hier / "qml", hier.parent.parent / "ico.ico"


QML_DIR, ICON = _ressourcen()


def _verdrahten(sets: SetsViewModel, lernen: LearningViewModel,
                einstellungen: SettingsViewModel) -> None:
    """Signale zwischen den ViewModels - kein Polling."""
    sets.lernsetGewaehlt.connect(lernen.waehleLernset)
    einstellungen.richtungGeaendert.connect(lernen.setzeRichtung)
    # Nach jeder Antwort die Prozentzahl in der Seitenleiste nachziehen.
    lernen.fortschrittGespeichert.connect(lambda _id: sets.aktualisiere())


def _entwicklungsposition(engine: QQmlApplicationEngine) -> None:
    """Nur fuer die Entwicklung: Fenster per LERNAPP_FENSTER="x,y" platzieren.

    Ohne die Variable verhaelt sich das Fenster normal.
    """
    import os

    wert = os.environ.get("LERNAPP_FENSTER", "")
    if not wert:
        return
    try:
        x, y = (int(t) for t in wert.split(",", 1))
    except ValueError:
        return
    fenster = engine.rootObjects()[0]
    fenster.setProperty("x", x)
    fenster.setProperty("y", y)


def run() -> int:
    dienste().beim_start()

    app = QGuiApplication(sys.argv)
    app.setApplicationName("LernApp")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("LernApp")
    if ICON.exists():
        app.setWindowIcon(QIcon(str(ICON)))

    state = AppState()
    einstellungen = SettingsViewModel(state)
    lernen = LearningViewModel(state, richtung=einstellungen.richtung)
    sets = SetsViewModel(state)
    _verdrahten(sets, lernen, einstellungen)

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    ctx = engine.rootContext()
    ctx.setContextProperty("lernen", lernen)
    ctx.setContextProperty("sets", sets)
    ctx.setContextProperty("einstellungen", einstellungen)

    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    if not engine.rootObjects():
        print("Main.qml konnte nicht geladen werden.", file=sys.stderr)
        return 1

    _entwicklungsposition(engine)

    # Zuletzt aktives Lernset wieder oeffnen, sonst das erste.
    zuletzt = state.settings.get("letztes_lernset", "")
    kandidat = zuletzt if state.finde_lernset(zuletzt)[1] else ""
    if not kandidat:
        erste = next(state.alle_lernsets(), None)
        kandidat = erste[1]["id"] if erste else ""
    if kandidat:
        sets.waehle(kandidat)

    def _merke_lernset(ls_id: str) -> None:
        state.settings["letztes_lernset"] = ls_id
        state.save_settings()

    sets.lernsetGewaehlt.connect(_merke_lernset)

    return app.exec()
