"""Ein eigenes Lernset im Marktplatz einreichen.

Drei Schritte, in dieser Reihenfolge:

1. **Sperrliste** - sofort und ohne Netz, damit man sie vor dem Anmelden sieht
   und nicht erst nach dem Anmelden erfährt, dass es ohnehin nicht geht.
2. **Anmelden** bei GitHub über den Device Flow, falls noch kein Zugang
   gespeichert ist.
3. **Einreichen** als Pull Request. Veröffentlicht ist es erst nach Lars'
   Freigabe - das steht auch so in der Oberfläche, damit niemand glaubt, sein
   Lernset sei schon für alle sichtbar.
"""
from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from lernapp import __version__
from lernapp.core import wortfilter
from lernapp.netz import github_anmeldung as anmeldung
from lernapp.netz import github_publizieren as publizieren
from lernapp.platform_services import dienste

from . import arbeit
from .app_state import AppState

GEHEIMNIS = "github"


class PublizierenViewModel(QObject):
    zustandGeaendert = Signal()
    codeBereit = Signal()
    fehler = Signal(str)
    hinweis = Signal(str)
    fertig = Signal(str)

    def __init__(self, state: AppState, plattform=None,
                 synchron: bool = False) -> None:
        super().__init__()
        self._state = state
        self._plattform = plattform if plattform is not None else dienste()
        self._synchron = synchron
        self._laeuft = False
        self._lernset_id = ""
        self._nutzercode = ""
        self._adresse = ""
        self._ergebnis = ""
        self._token = self._plattform.lies_geheimnis(GEHEIMNIS) or ""

    # -- Eigenschaften --------------------------------------------------------

    @Property(bool, notify=zustandGeaendert)
    def angemeldet(self) -> bool:
        return bool(self._token)

    @Property(bool, notify=zustandGeaendert)
    def laeuft(self) -> bool:
        return self._laeuft

    @Property(str, notify=zustandGeaendert)
    def nutzercode(self) -> str:
        return self._nutzercode

    @Property(str, notify=zustandGeaendert)
    def adresse(self) -> str:
        return self._adresse

    @Property(str, notify=zustandGeaendert)
    def ergebnis(self) -> str:
        """Adresse des Pull Requests, sobald es einen gibt."""
        return self._ergebnis

    # -- Schritt 1: prüfen ----------------------------------------------------

    @Slot(str, result="QVariantMap")
    def pruefe(self, ls_id: str) -> dict:
        """Sperrliste und Vollständigkeit - ohne Netz, sofort.

        Die Antwort ist so gebaut, dass QML sie direkt anzeigen kann.
        """
        self._lernset_id = ls_id
        self._ergebnis = ""
        self._nutzercode = ""
        self.zustandGeaendert.emit()

        ordner, lernset = self._state.finde_lernset(ls_id)
        if lernset is None:
            return {"ok": False, "grund": "Dieses Lernset gibt es nicht mehr."}

        items = lernset.get("items") or []
        if not items:
            return {"ok": False, "grund": "Ein leeres Lernset kann niemandem helfen."}

        treffer = wortfilter.pruefe_lernset(lernset.get("name", ""), items)
        if treffer:
            return {"ok": False, "grund": wortfilter.meldung(treffer)}

        return {
            "ok": True,
            "grund": "",
            "name": lernset.get("name", ""),
            "fach": ordner,
            "karten": len(items),
        }

    # -- Schritt 2: anmelden --------------------------------------------------

    @Slot()
    def anmelden(self) -> None:
        if self._laeuft:
            return
        self._setze_laeuft(True)
        arbeit.starte(anmeldung.starte_anmeldung, self._code_da,
                      self._fehlgeschlagen, (anmeldung.AnmeldungFehler,),
                      self._synchron)

    @Slot()
    def abmelden(self) -> None:
        """Zugang vergessen. Entzogen wird er bei GitHub selbst."""
        self._token = ""
        self._plattform.loesche_geheimnis(GEHEIMNIS)
        self.zustandGeaendert.emit()
        self.hinweis.emit("Von GitHub abgemeldet. Der Zugang wurde auf diesem "
                          "Rechner gelöscht.")

    def _code_da(self, code) -> None:
        self._nutzercode = code.nutzercode
        self._adresse = code.adresse
        self.zustandGeaendert.emit()
        self.codeBereit.emit()
        # Ab jetzt wird gewartet, bis der Nutzer im Browser bestätigt hat.
        arbeit.starte(lambda: anmeldung.warte_auf_token(code), self._token_da,
                      self._fehlgeschlagen, (anmeldung.AnmeldungFehler,),
                      self._synchron)

    def _token_da(self, token: str) -> None:
        self._token = str(token)
        self._nutzercode = ""
        self._setze_laeuft(False)
        gespeichert = self._plattform.speichere_geheimnis(GEHEIMNIS, self._token)
        self.zustandGeaendert.emit()
        self.hinweis.emit(
            "Bei GitHub angemeldet." if gespeichert else
            "Bei GitHub angemeldet - nur für diese Sitzung, dieser Rechner "
            "kann den Zugang nicht sicher speichern."
        )

    # -- Schritt 3: einreichen ------------------------------------------------

    @Slot(str)
    def reicheEin(self, ls_id: str) -> None:
        if self._laeuft:
            return
        if not self._token:
            self.fehler.emit("Dafür musst du dich zuerst bei GitHub anmelden.")
            return

        ordner, lernset = self._state.finde_lernset(ls_id)
        if lernset is None:
            self.fehler.emit("Dieses Lernset gibt es nicht mehr.")
            return

        name = lernset.get("name", "")
        items = list(lernset.get("items") or [])
        token = self._token
        self._setze_laeuft(True)
        arbeit.starte(
            lambda: publizieren.veroeffentliche(token, name, items, ordner,
                                                app_version=__version__),
            self._eingereicht, self._fehlgeschlagen,
            (publizieren.PublizierenFehler,), self._synchron)

    def _eingereicht(self, ergebnis) -> None:
        self._ergebnis = ergebnis.adresse
        self._setze_laeuft(False)
        self.zustandGeaendert.emit()
        self.fertig.emit(ergebnis.adresse)

    # -- Innereien ------------------------------------------------------------

    def _setze_laeuft(self, wert: bool) -> None:
        if self._laeuft != wert:
            self._laeuft = wert
            self.zustandGeaendert.emit()

    def _fehlgeschlagen(self, text: str) -> None:
        # Eine abgelaufene Anmeldung ist der häufigste Fall. Den gespeicherten
        # Zugang dann wegwerfen, sonst scheitert jeder weitere Versuch gleich.
        if "neu anmelden" in text or "gilt nicht mehr" in text:
            self._token = ""
            self._plattform.loesche_geheimnis(GEHEIMNIS)
        self._nutzercode = ""
        self._setze_laeuft(False)
        self.zustandGeaendert.emit()
        self.fehler.emit(text)
