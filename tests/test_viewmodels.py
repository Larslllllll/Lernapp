"""Tests der Qt-ViewModels.

Laufen headless. Jeder Test bekommt ein eigenes Datenverzeichnis - die echten
Dateien unter ~/.lernapp werden nie angefasst.

Bewusst NICHT getestet: Lernregeln. Die sind in test_learning_engine.py und
test_progress.py abgedeckt und werden hier nicht dupliziert.
"""
import json

import pytest

pytest.importorskip("PySide6", reason="PySide6 nicht installiert - venv nutzen")

from lernapp.gui.bridge.app_state import AppState                    # noqa: E402
from lernapp.gui.bridge.learning_viewmodel import LearningViewModel  # noqa: E402
from lernapp.gui.bridge.sets_viewmodel import SetsViewModel          # noqa: E402
from lernapp.gui.bridge.settings_viewmodel import SettingsViewModel  # noqa: E402

DATEN = {
    "folders": {
        "Franzoesisch": {"lernsets": [
            {"id": "set-a", "name": "Unite 4", "items": [
                {"q": "la maison", "a": "das haus"},
                {"q": "le chien", "a": "der hund"},
            ]},
        ]},
        "Englisch": {"lernsets": [
            {"id": "set-b", "name": "Verben", "items": [
                {"q": "go ___ ___", "a": "went, gone"},
                {"q": "___ went ___", "a": "go, gone"},
                {"q": "___ ___ gone", "a": "go, went"},
                {"q": "___ had to ___", "a": "must, had to"},
            ]},
        ]},
    }
}


def loesung_fuer(lernen):
    return "das haus" if lernen.frageText == "la maison" else "der hund"


@pytest.fixture
def basis(tmp_path):
    (tmp_path / "data.json").write_text(json.dumps(DATEN), encoding="utf-8")
    return tmp_path


@pytest.fixture
def state(basis):
    return AppState(basis)


@pytest.fixture
def vms(state):
    einst = SettingsViewModel(state)
    lernen = LearningViewModel(state, richtung="→")
    sets = SetsViewModel(state)
    sets.lernsetGewaehlt.connect(lernen.waehleLernset)
    einst.richtungGeaendert.connect(lernen.setzeRichtung)
    lernen.fortschrittGespeichert.connect(lambda _i: sets.aktualisiere())
    return einst, lernen, sets


# -- SettingsViewModel --------------------------------------------------------

def test_theme_umschalten_wird_gespeichert(state):
    vm = SettingsViewModel(state)
    assert vm.dark is True
    vm.themeUmschalten()
    assert vm.dark is False
    assert AppState(state._basis).settings["theme"] == "light"


def test_richtung_wird_gespeichert_und_validiert(state):
    vm = SettingsViewModel(state)
    vm.setzeRichtung("←")
    assert vm.richtung == "←"
    vm.setzeRichtung("unsinn")
    assert vm.richtung == "←", "ungueltige Richtung wird ignoriert"
    assert AppState(state._basis).settings["richtung"] == "←"


def test_fenstergroesse_wird_gemerkt_aber_unsinn_nicht(state):
    vm = SettingsViewModel(state)
    vm.merkeFenster(1400, 900)
    assert AppState(state._basis).settings["fenster"] == {"breite": 1400, "hoehe": 900}
    vm.merkeFenster(10, 10)
    assert AppState(state._basis).settings["fenster"] == {"breite": 1400, "hoehe": 900}


# -- SetsViewModel ------------------------------------------------------------

def test_ordner_und_lernsets_werden_gelistet(vms):
    _e, _l, sets = vms
    ordner = sets.ordner
    assert [o["name"] for o in ordner] == ["Franzoesisch", "Englisch"]
    assert ordner[0]["lernsets"][0]["name"] == "Unite 4"


def test_triple_paket_zaehlt_als_eine_einheit_in_der_seitenleiste(vms):
    _e, _l, sets = vms
    englisch = next(o for o in sets.ordner if o["name"] == "Englisch")
    verben = englisch["lernsets"][0]
    # 4 Karten auf der Platte = 1 vollständiges Paket + 1 Einzelkarte
    assert verben["karten"] == 2, "Pakete zaehlen als eins, nicht als drei"


def test_lernset_anlegen_bearbeiten_loeschen(vms):
    _e, _l, sets = vms
    neu = sets.lernsetAnlegenIn("Franzoesisch", "Neu", [{"q": "frage", "a": "antwort"}])
    assert neu != ""
    assert sets.lernsetSpeichern(neu, "Umbenannt", [{"q": "x", "a": "y"}]) == neu
    geladen = sets.lernsetLaden(neu)
    assert geladen["name"] == "Umbenannt"
    assert geladen["items"] == [{"q": "x", "a": "y"}]
    assert sets.lernsetLoeschen(neu) is True
    assert sets.lernsetLaden(neu) == {}


def test_leere_karten_werden_beim_speichern_verworfen(vms):
    _e, _l, sets = vms
    neu = sets.lernsetAnlegenIn("Franzoesisch", "Gemischt", [
        {"q": "gut", "a": "bon"},
        {"q": "   ", "a": "leer"},
        {"q": "ohne antwort", "a": ""},
    ])
    assert sets.lernsetLaden(neu)["items"] == [{"q": "gut", "a": "bon"}]


def test_lernset_ohne_namen_oder_karten_wird_abgelehnt(vms):
    _e, _l, sets = vms
    fehler = []
    sets.fehler.connect(fehler.append)
    assert sets.lernsetAnlegenIn("Franzoesisch", "", [{"q": "a", "a": "b"}]) == ""
    assert sets.lernsetSpeichern("", "Name", []) == ""
    assert len(fehler) == 2


def test_verschieben_zwischen_ordnern(vms):
    _e, _l, sets = vms
    assert sets.lernsetVerschieben("set-a", "Englisch") is True
    englisch = next(o for o in sets.ordner if o["name"] == "Englisch")
    assert "Unite 4" in [ls["name"] for ls in englisch["lernsets"]]
    assert sets.lernsetVerschieben("set-a", "Gibtsnicht") is False


def test_ordner_anlegen_und_loeschen(vms):
    _e, _l, sets = vms
    fehler = []
    sets.fehler.connect(fehler.append)
    assert sets.ordnerAnlegen("Latein") is True
    assert sets.ordnerAnlegen("Latein") is False, "Duplikat"
    assert sets.ordnerLoeschen("Latein") is True
    assert sets.ordnerLoeschen("Franzoesisch") is False, "nicht leer"
    assert len(fehler) == 2


def test_triple_karten_kommen_aus_dem_core(vms):
    _e, _l, sets = vms
    karten = sets.tripleKarten("must", "had to", "had to")
    assert len(karten) == 3
    assert karten[0] == {"q": "must ___ ___", "a": "had to, had to"}
    assert karten[1] == {"q": "___ had to ___", "a": "must, had to"}
    assert sets.tripleKarten("go", "", "gone") == []


def test_geloeschtes_lernset_behaelt_seinen_fortschritt(vms, state):
    _e, lernen, sets = vms
    sets.waehle("set-a")
    lernen.pruefe([loesung_fuer(lernen)])
    sets.lernsetLoeschen("set-a")
    assert AppState(state._basis).progress["set-a"]["xp"] == 10


# -- LearningViewModel --------------------------------------------------------

def test_lernset_waehlen_startet_eine_frage(vms):
    _e, lernen, sets = vms
    sets.waehle("set-a")
    assert lernen.hatLernset
    assert lernen.lernsetName == "Unite 4"
    assert lernen.frageTyp == "normal"
    assert lernen.frageText in ("la maison", "le chien")


def test_richtige_antwort_gibt_xp_und_sperrt(vms):
    _e, lernen, sets = vms
    sets.waehle("set-a")
    lernen.pruefe([loesung_fuer(lernen)])
    assert lernen.feedbackArt == "richtig"
    assert lernen.xp == 10
    assert lernen.combo == 1
    assert lernen.gesperrt is True


def test_falsche_antwort_meldet_loesung(vms):
    _e, lernen, sets = vms
    sets.waehle("set-a")
    lernen.pruefe(["voellig falsch"])
    assert lernen.feedbackArt == "falsch"
    assert "Richtig" in lernen.feedbackText
    assert lernen.combo == 0


def test_gesperrt_verhindert_doppelte_antwort(vms):
    _e, lernen, sets = vms
    sets.waehle("set-a")
    loesung = loesung_fuer(lernen)
    lernen.pruefe([loesung])
    xp = lernen.xp
    lernen.pruefe([loesung])
    assert lernen.xp == xp, "zweite Antwort ohne weiter() wird ignoriert"


def test_triple_karte_liefert_zwei_eingabefelder(vms):
    _e, lernen, sets = vms
    sets.waehle("set-b")
    for _ in range(40):
        if lernen.frageTyp == "triple":
            break
        lernen.weiter()
    assert lernen.frageTyp == "triple"
    assert len(lernen.slots) == 3
    assert len([s for s in lernen.slots if s["eingabe"]]) == 2


def test_regression_had_to_karte_ist_ueber_das_viewmodel_loesbar(vms):
    """Die Karte, die in der alten App nie lösbar war."""
    _e, lernen, sets = vms
    sets.waehle("set-b")
    for _ in range(80):
        if lernen.frageTyp == "triple" and lernen.slots[1]["text"] == "had to":
            break
        lernen.weiter()
    else:
        pytest.fail("Karte mit sichtbarer Mittelform wurde nie gezogen")
    lernen.pruefe(["must", "had to"])
    assert lernen.feedbackArt == "richtig"


def test_fortschritt_wird_nach_jeder_antwort_gespeichert(vms, state):
    _e, lernen, sets = vms
    sets.waehle("set-a")
    lernen.pruefe([loesung_fuer(lernen)])
    assert AppState(state._basis).progress["set-a"]["xp"] == 10


def test_seitenleiste_zieht_prozent_nach(vms):
    _e, lernen, sets = vms
    sets.waehle("set-a")

    def prozent():
        ordner = next(o for o in sets.ordner if o["name"] == "Franzoesisch")
        return ordner["lernsets"][0]["prozent"]

    vorher = prozent()
    lernen.pruefe([loesung_fuer(lernen)])
    assert prozent() > vorher


def test_fortschritt_loeschen_betrifft_nur_das_aktuelle_lernset(vms, state):
    _e, lernen, sets = vms
    sets.waehle("set-a")
    lernen.pruefe([loesung_fuer(lernen)])

    sets.waehle("set-b")
    for _ in range(40):
        if lernen.frageTyp == "triple":
            break
        lernen.weiter()
    lernen.pruefe(list(s["text"] for s in lernen.slots if not s["eingabe"]) or ["x"])
    xp_b = AppState(state._basis).progress.get("set-b", {}).get("xp", 0)

    sets.waehle("set-a")
    lernen.fortschrittLoeschen()
    assert lernen.xp == 0
    assert AppState(state._basis).progress.get("set-b", {}).get("xp", 0) == xp_b


def test_best_combo_ueberlebt_fortschritt_loeschen(vms):
    _e, lernen, sets = vms
    sets.waehle("set-a")
    lernen.pruefe([loesung_fuer(lernen)])
    assert lernen.bestCombo == 1
    lernen.fortschrittLoeschen()
    assert lernen.xp == 0
    assert lernen.bestCombo == 1, "Rekord bleibt"


def test_richtungswechsel_erreicht_die_session(vms):
    einst, lernen, sets = vms
    sets.waehle("set-a")
    einst.setzeRichtung("←")
    lernen.weiter()
    assert lernen.rueckwaerts is True


def test_lernset_neu_laden_nach_bearbeiten(vms):
    _e, lernen, sets = vms
    sets.waehle("set-a")
    sets.lernsetSpeichern("set-a", "Unite 4", [{"q": "neu", "a": "new"}])
    lernen.lernsetNeuLaden()
    assert lernen.gesamt == 1
    assert lernen.frageText == "neu"


def test_statistik_am_ende_der_sitzung(vms):
    _e, lernen, sets = vms
    sets.waehle("set-a")
    for _ in range(12):
        if lernen.frageTyp == "fertig":
            break
        if lernen.frageTyp == "normal":
            lernen.pruefe([loesung_fuer(lernen)])
        lernen.weiter()
    assert lernen.frageTyp == "fertig"
    assert lernen.statistik["accuracy"] == 100
    assert lernen.statistik["richtig"] == 2


def test_ohne_lernset_passiert_nichts(state):
    lernen = LearningViewModel(state, richtung="→")
    assert lernen.hatLernset is False
    lernen.pruefe(["irgendwas"])
    lernen.weiter()
    lernen.neustart()
    lernen.fortschrittLoeschen()
    assert lernen.frageTyp == "leer"


# -- Ton und Tastenkürzel ----------------------------------------------------

def test_ton_laesst_sich_umschalten_und_wird_gespeichert(state):
    vm = SettingsViewModel(state)
    assert vm.sound is True
    vm.soundUmschalten()
    assert vm.sound is False
    assert AppState(state._basis).settings["sound"] is False
    vm.soundUmschalten()
    assert AppState(state._basis).settings["sound"] is True


def test_ton_verfuegbarkeit_kommt_von_der_plattform(state):
    from lernapp.platform_services import dienste

    vm = SettingsViewModel(state)
    assert vm.tonVerfuegbar == dienste().unterstuetzt_ton()


def test_abgeschalteter_ton_wird_beim_antworten_respektiert(vms, state, monkeypatch):
    einst, lernen, sets = vms
    gespielt = []
    monkeypatch.setattr(
        "lernapp.gui.bridge.learning_viewmodel.dienste",
        lambda: type("D", (), {"spiele_ton": lambda self, ok: gespielt.append(ok)})(),
    )
    sets.waehle("set-a")
    lernen.pruefe([loesung_fuer(lernen)])
    assert gespielt == [True]

    einst.soundUmschalten()
    lernen.weiter()
    lernen.pruefe(["falsch"])
    assert gespielt == [True], "bei abgeschaltetem Ton wird nichts gespielt"


def test_kuerzel_kommen_aus_der_plattformschicht(state):
    from lernapp.platform_services.base import AKTIONEN

    vm = SettingsViewModel(state)
    kuerzel = vm.kuerzel
    assert set(kuerzel) == set(AKTIONEN), "jede Aktion braucht ein Kuerzel"
    assert all(isinstance(v, str) and v for v in kuerzel.values())


def test_kuerzel_sind_eindeutig(state):
    vm = SettingsViewModel(state)
    werte = list(vm.kuerzel.values())
    assert len(werte) == len(set(werte)), "keine Kombination doppelt vergeben"


def test_macos_kuerzel_sind_vollstaendig():
    """macOS-Zuordnung darf keine Aktion vergessen, auch wenn sie erbt."""
    from lernapp.platform_services.base import AKTIONEN
    from lernapp.platform_services.macos import MacDienste

    assert set(MacDienste().tastenkuerzel()) == set(AKTIONEN)


def test_windows_kuerzel_sind_vollstaendig():
    from lernapp.platform_services.base import AKTIONEN
    from lernapp.platform_services.windows import WindowsDienste

    assert set(WindowsDienste().tastenkuerzel()) == set(AKTIONEN)


# -- Import und Export --------------------------------------------------------

def test_export_datei_wird_geschrieben(vms, tmp_path):
    _e, _l, sets = vms
    hinweise = []
    sets.hinweis.connect(hinweise.append)
    ziel = tmp_path / "export.lernset.json"
    assert sets.exportiereLernset("set-a", str(ziel)) is True
    assert ziel.exists()
    assert hinweise and "export.lernset.json" in hinweise[0]


def test_export_von_unbekanntem_lernset_meldet_fehler(vms, tmp_path):
    _e, _l, sets = vms
    fehler = []
    sets.fehler.connect(fehler.append)
    assert sets.exportiereLernset("gibtsnicht", str(tmp_path / "x.json")) is False
    assert fehler


def test_geteiltes_lernset_landet_in_einer_anderen_installation(vms, tmp_path):
    """Der Weg, der beim Teilen mit Klassenkameraden zählt."""
    _e, _l, sets = vms
    datei = tmp_path / "geteilt.lernset.json"
    assert sets.exportiereLernset("set-b", str(datei)) is True

    # Zweite, völlig getrennte Installation
    fremd_basis = tmp_path / "andere_installation"
    fremd_basis.mkdir()
    fremd = SetsViewModel(AppState(fremd_basis))
    ordner_vorher = fremd.ordnerNamen[0]

    neu_id = fremd.importiereLernset(str(datei), ordner_vorher)
    assert neu_id != ""
    geladen = fremd.lernsetLaden(neu_id)
    assert geladen["name"] == "Verben"
    assert len(geladen["items"]) == 4
    assert {"q": "___ had to ___", "a": "must, had to"} in geladen["items"]


def test_import_bringt_keinen_fremden_fortschritt_mit(vms, tmp_path, state):
    _e, lernen, sets = vms
    sets.waehle("set-a")
    lernen.pruefe([loesung_fuer(lernen)])
    datei = tmp_path / "mit_fortschritt.lernset.json"
    sets.exportiereLernset("set-a", str(datei))

    inhalt = datei.read_text(encoding="utf-8")
    assert "xp" not in inhalt
    assert "streaks" not in inhalt

    fremd_basis = tmp_path / "empfaenger"
    fremd_basis.mkdir()
    fremd_state = AppState(fremd_basis)
    fremd = SetsViewModel(fremd_state)
    neu_id = fremd.importiereLernset(str(datei), fremd.ordnerNamen[0])
    assert fremd_state.progress.get(neu_id) is None


def test_import_kaputter_datei_meldet_klaren_fehler(vms, tmp_path):
    _e, _l, sets = vms
    fehler = []
    sets.fehler.connect(fehler.append)

    kaputt = tmp_path / "kaputt.lernset.json"
    kaputt.write_text("{das ist kein json", encoding="utf-8")
    assert sets.importiereLernset(str(kaputt), "Franzoesisch") == ""

    leer = tmp_path / "leer.lernset.json"
    leer.write_text('{"items": []}', encoding="utf-8")
    assert sets.importiereLernset(str(leer), "Franzoesisch") == ""

    assert sets.importiereLernset(str(tmp_path / "fehlt.json"), "Franzoesisch") == ""
    assert len(fehler) == 3


def test_import_akzeptiert_file_url_aus_qml(vms, tmp_path):
    _e, _l, sets = vms
    datei = tmp_path / "via_url.lernset.json"
    sets.exportiereLernset("set-a", str(datei))
    url = datei.as_uri()
    assert url.startswith("file:")
    assert sets.importiereLernset(url, "Franzoesisch") != ""


def test_textvorschau_ohne_zu_speichern(vms):
    _e, _l, sets = vms
    vorher = len(sets.ordner[0]["lernsets"])
    vorschau = sets.textVorschau("go;went;gone\nla maison;das haus\nkaputt")
    assert vorschau["ok"] is True
    assert vorschau["pakete"] == 1
    assert vorschau["normale"] == 1
    assert vorschau["einheiten"] == 2
    assert len(vorschau["probleme"]) == 1
    assert len(sets.ordner[0]["lernsets"]) == vorher, "Vorschau speichert nichts"


def test_textkarten_erzeugen_gueltige_pakete(vms):
    _e, _l, sets = vms
    karten = sets.textKarten("must;had to;had to")
    neu = sets.lernsetAnlegenIn("Franzoesisch", "Aus Text", karten)
    assert neu != ""
    eintrag = next(o for o in sets.ordner if o["name"] == "Franzoesisch")["lernsets"]
    aus_text = next(ls for ls in eintrag if ls["id"] == neu)
    assert aus_text["karten"] == 1, "drei Karten, aber eine Lerneinheit"


def test_standarddateiname_ist_plattformsicher(vms):
    _e, _l, sets = vms
    name = sets.standardDateiname("set-a")
    assert name.endswith(".lernset.json")
    assert not any(z in name for z in r'<>:"/\|?*')


# -- Ordner ein- und ausklappen ----------------------------------------------

def test_ordner_sind_zuerst_alle_offen(vms):
    _einst, _lernen, sets = vms
    assert sets.eingeklappt == []


def test_umklappen_merkt_sich_den_ordner(vms):
    _einst, _lernen, sets = vms
    sets.klappeUm("Englisch")
    assert sets.eingeklappt == ["Englisch"]
    sets.klappeUm("Englisch")
    assert sets.eingeklappt == []


def test_der_zustand_ueberlebt_den_neustart(vms, basis):
    """Wer seine Ordner zuklappt, will sie nicht bei jedem Start wieder
    offen vorfinden."""
    _einst, _lernen, sets = vms
    sets.klappeUm("Englisch")

    frisch = SetsViewModel(AppState(basis))
    assert frisch.eingeklappt == ["Englisch"]


def test_mehrere_ordner_gleichzeitig(vms):
    _einst, _lernen, sets = vms
    sets.klappeUm("Englisch")
    sets.klappeUm("Franzoesisch")
    assert set(sets.eingeklappt) == {"Englisch", "Franzoesisch"}


def test_kaputter_eintrag_in_den_einstellungen_stoert_nicht(state):
    """Alte oder von Hand verbogene settings.json darf nichts umwerfen."""
    state.settings["eingeklappt"] = "kein array"
    assert SetsViewModel(state).eingeklappt == []
